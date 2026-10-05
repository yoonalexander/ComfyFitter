"""Optional source protection, admitted only by its matched gate and exact runtime parity."""
import asyncio,hashlib,json,os,time,uuid,subprocess
from pathlib import Path
from io import BytesIO
from PIL import Image
from .settings import ROOT
from .workflow import sha
class Protection:
    def __init__(self,settings,workflow):
        self.settings=settings;self.available=False;self.report_hash=None;self.code_hashes={}
        try:
            report=json.loads(settings.protection_manifest.read_text())
            valid=(bool(workflow.supported) and report['decision']=='passed' and report['expected']==report['reviewed']==40
                and report['baseline_quality_sha256']==workflow.quality_sha256
                and report['implementation_sha256']==sha(ROOT/'evaluation/semantic_constraints.py')
                and report['guard_sha256']==sha(ROOT/'evaluation/boundary_guard.py')
                and report['parser_manifest_sha256']==sha(ROOT/'evaluation/segmentation_environment.json')
                and report.get('runtime_parity',{}).get('exact_outputs')==40
                and report['runtime_parity']['engine_sha256']==sha(ROOT/'evaluation/protection_engine.py')
                and report['runtime_parity']['helper_sha256']==sha(ROOT/'evaluation/apply_protection.py'))
            python=Path(settings.protection_python)
            if not valid or not python.is_absolute() or not python.is_file():return
            parser=json.loads((ROOT/'evaluation/segmentation_environment.json').read_text())
            names=list(parser['packages'])
            code='import importlib.metadata,json; names='+repr(names)+'; print(json.dumps({name:importlib.metadata.version(name) for name in names}))'
            runtime=subprocess.run([str(python),'-c',code],capture_output=True,text=True,timeout=5,check=True)
            if json.loads(runtime.stdout)!=parser['packages']:return
            for row in parser['files']:
                path=settings.protection_model_dir/row['file']
                if path.is_symlink() or not path.is_file() or sha(path)!=row['sha256']:return
            self.available=True;self.report_hash=sha(settings.protection_manifest)
            self.code_hashes={name:sha(ROOT/'evaluation'/name) for name in ('semantic_constraints.py','boundary_guard.py','protection_engine.py','apply_protection.py')}
        except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError):pass
    async def apply(self,job,directory,data):
        raw_sha=hashlib.sha256(data).hexdigest();fallback=dict(applied=False,fallback_reason='Source protection was unavailable; the validated raw preview was retained.',raw_sha256=raw_sha,report_sha256=self.report_hash)
        if not self.available or job['manifest'].get('protection_manifest_sha256')!=self.report_hash:return data,fallback
        try:
            if sha(self.settings.protection_manifest)!=self.report_hash or any(sha(ROOT/'evaluation'/name)!=value for name,value in self.code_hashes.items()):return data,fallback
        except OSError:return data,fallback
        started=time.monotonic();nonce='protection-'+uuid.uuid4().hex;raw=directory/(nonce+'-raw.png');output=directory/(nonce+'.png');metadata=directory/(nonce+'.json')
        raw.write_bytes(data);process=None
        try:
            environment={**os.environ,'HF_HUB_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','TOKENIZERS_PARALLELISM':'false'}
            process=await asyncio.create_subprocess_exec(self.settings.protection_python,str(ROOT/'evaluation/apply_protection.py'),
                '--source',str(directory/'person.png'),'--raw',str(raw),'--output',str(output),'--metadata',str(metadata),'--model-directory',str(self.settings.protection_model_dir),
                '--category',job['category'],stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL,env=environment)
            await asyncio.wait_for(process.wait(),90)
            if process.returncode:raise ValueError('CPU helper failed')
            if output.is_symlink() or metadata.is_symlink() or not output.is_file() or output.stat().st_size>40*1024*1024:raise ValueError('Invalid CPU helper result')
            result=output.read_bytes();metrics=json.loads(metadata.read_text())
            if metrics['source_sha256']!=sha(directory/'person.png') or metrics['raw_sha256']!=raw_sha or metrics['result_sha256']!=hashlib.sha256(result).hexdigest() or metrics['protected_pixels_changed']!=0:raise ValueError('CPU helper evidence mismatch')
            with Image.open(BytesIO(result)) as final,Image.open(BytesIO(data)) as original:
                if final.format!='PNG' or final.size!=original.size or getattr(final,'n_frames',1)!=1:raise ValueError('CPU helper geometry mismatch')
                final.load()
            return result,{**metrics,'report_sha256':self.report_hash}
        except (OSError,ValueError,KeyError,TypeError,asyncio.TimeoutError):
            fallback['wall_seconds']=time.monotonic()-started;return data,fallback
        finally:
            if process and process.returncode is None:
                process.kill();await process.wait()
