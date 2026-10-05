"""Execute a declared ordered-reference/outfit study against dedicated loopback inference."""
import argparse,hashlib,json,sys,time,uuid,urllib.request,urllib.parse,subprocess
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app.references import References,multi_prompt,outfit_prompt
from backend.app.outfits import refined_outfit_prompt
from backend.app.coat_outfits import coat_outfit_prompt
from backend.app.bag_coat_outfits import bag_coat_prompt
from backend.app.conditional_coat_outfits import conditional_coat_prompt
from evidence import without_runtime_fields
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def request(route,data=None,content_type='application/json'):
    if isinstance(data,dict):data=json.dumps(data).encode()
    req=urllib.request.Request('http://127.0.0.1:8188'+route,data=data,headers={'Content-Type':content_type})
    with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)
def save(path,record):
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(record,indent=2)+'\n');temporary.replace(path)
def run(protocol_path,wait_for_baseline=False):
    protocol=json.loads(protocol_path.read_text());experiment=protocol['experiment']
    execution_limit=protocol.get('execution_wait_seconds',900)
    if type(execution_limit) is not int or not 900<=execution_limit<=3600:raise ValueError('Declared execution wait must be 900-3600 seconds')
    if any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in experiment):raise ValueError('Invalid experiment')
    config=json.loads((ROOT/'backend/workflow.json').read_text())
    graph_path=ROOT/config['graph'];implementation=ROOT/'backend/app/references.py'
    if sha(graph_path)!=protocol['graph_sha256'] or sha(implementation)!=protocol['implementation_sha256']:raise ValueError('Declared implementation changed')
    if protocol.get('outfit_implementation_sha256') and sha(ROOT/'backend/app/outfits.py')!=protocol['outfit_implementation_sha256']:raise ValueError('Declared outfit implementation changed')
    if protocol.get('coat_refinement_sha256') and sha(ROOT/'backend/app/coat_outfits.py')!=protocol['coat_refinement_sha256']:raise ValueError('Declared coat refinement changed')
    if protocol.get('bag_refinement_sha256') and sha(ROOT/'backend/app/bag_coat_outfits.py')!=protocol['bag_refinement_sha256']:raise ValueError('Declared bag refinement changed')
    if protocol.get('conditional_refinement_sha256') and sha(ROOT/'backend/app/conditional_coat_outfits.py')!=protocol['conditional_refinement_sha256']:raise ValueError('Declared conditional refinement changed')
    if wait_for_baseline:
        while True:
            terminal=[]
            for path in (ROOT/'evaluation/benchmarks'/protocol['baseline_experiment']).glob('*/records.json'):
                terminal.extend(json.loads(path.read_text()))
            if len(terminal)==40 and all(r['status'] in ('complete','failed') for r in terminal):break
            time.sleep(15)
    for sample in protocol['samples']:
        for seed in protocol['seeds']:
            directory=ROOT/'evaluation/benchmarks'/experiment/sample['id']/str(seed);directory.mkdir(parents=True,exist_ok=True)
            record_path=directory/'record.json'
            if record_path.exists():
                existing=json.loads(record_path.read_text())
                if existing['status'] in ('complete','failed'):
                    if existing['status']=='complete' and sha(ROOT/existing['output'])!=existing['output_sha256']:raise ValueError('Retained output changed')
                    print('Already terminal: '+sample['id']+'/'+str(seed),flush=True);continue
                raise RuntimeError('Unresolved existing submission: reconcile history/queue before any retry: '+str(record_path))
            for value in sample['images'].values():
                path=ROOT/value['path']
                if sha(path)!=value['sha256']:raise ValueError('Declared study input changed')
                with Image.open(path) as image:image.verify()
            if sample['mode']=='multi_reference':
                baseline_protocol=json.loads((ROOT/f"evaluation/{protocol['baseline_experiment']}_protocol.json").read_text())
                role='jacket' if sample['category']=='jacket' else 'outerwear' if sample['category']=='coat' else 'upper_body'
                if sha(ROOT/sample['base_prompt'])!=baseline_protocol['prompts'][role]:raise ValueError('Declared baseline prompt changed before matched execution')
            while True:
                queue=request('/queue')
                if not queue['queue_running'] and not queue['queue_pending']:break
                time.sleep(5)
            run_id='cf_study_'+uuid.uuid4().hex;uploaded={}
            for role,value in sample['images'].items():
                path=ROOT/value['path'];boundary=uuid.uuid4().hex;filename=run_id+'_'+role+path.suffix
                body=(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()+path.read_bytes()+f'\r\n--{boundary}--\r\n'.encode())
                item=request('/upload/image',body,'multipart/form-data; boundary='+boundary)
                if item.get('name')!=filename or item.get('subfolder',''):raise ValueError('Unexpected uploaded location')
                uploaded[role]=filename
            graph=References.graph(json.loads(graph_path.read_text()),config,uploaded)
            if sample['mode']=='capacity':prompt=sample['prompt']
            elif sample['mode']=='two_garment':
                if protocol.get('conditional_refinement_sha256'):
                    prompt=conditional_coat_prompt(sample['category'],sample['outer_category'],sample['source_has_bag'])
                else:prompt=(bag_coat_prompt if protocol.get('bag_refinement_sha256') else coat_outfit_prompt if protocol.get('coat_refinement_sha256') else refined_outfit_prompt if protocol.get('outfit_implementation_sha256') else outfit_prompt)(sample['category'],sample['outer_category'])
            else:
                base=(ROOT/sample['base_prompt']).read_text().format(garment_type=sample['category'])
                prompt=multi_prompt(base,[role for role in sample['images'] if role not in ('person','garment')])
            graph[config['prompt_node']]['inputs']['prompt']=prompt
            graph[config['sampler_node']]['inputs']['seed']=seed
            graph[config['output_node']]['inputs']['filename_prefix']=run_id
            graph_file=directory/'graph.api.json';graph_file.write_text(json.dumps(graph,indent=2)+'\n')
            record=dict(experiment=experiment,sample_id=sample['id'],seed=seed,status='submission_intent',
                graph_sha256=sha(graph_file),protocol_sha256=sha(protocol_path),inputs=sample['images'],uploaded=uploaded,
                image_order=list(sample['images']),prompt=prompt,client_id=run_id,scores=None,reviewer=None,notes=None)
            if protocol.get('conditional_refinement_sha256'):record['source_has_bag']=sample['source_has_bag']
            save(record_path,record);started=time.monotonic()
            acknowledgement=request('/prompt',{'prompt':graph,'client_id':run_id})
            record.update(status='queued',prompt_id=acknowledgement['prompt_id']);save(record_path,record)
            peak=0
            while time.monotonic()-started<execution_limit:
                history=request('/history/'+record['prompt_id']).get(record['prompt_id'])
                try:peak=max(peak,int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True,timeout=5).splitlines()[0]))
                except (ValueError,subprocess.SubprocessError):pass
                if history and history.get('status',{}).get('completed'):
                    save(directory/'history.json',history)
                    if without_runtime_fields(history['prompt'][2])!=without_runtime_fields(graph):raise ValueError('History graph mismatch')
                    stamps={kind:value.get('timestamp') for kind,value in history['status'].get('messages',[])}
                    last=stamps.get('execution_success') or stamps.get('execution_error')
                    record.update(execution_seconds=(last-stamps['execution_start'])/1000 if last and stamps.get('execution_start') else None,
                                  wall_seconds=round(time.monotonic()-started,3),sampled_device_peak_mib=peak)
                    if history['status']['status_str']!='success':record.update(status='failed',error=history['status']['messages']);save(record_path,record);break
                    images=history['outputs'][config['output_node']]['images']
                    if len(images)!=1 or not images[0]['filename'].startswith(run_id):raise ValueError('Unexpected output')
                    url='http://127.0.0.1:8188/view?'+urllib.parse.urlencode(images[0])
                    with urllib.request.urlopen(url,timeout=30) as response:data=response.read()
                    output=directory/'output.png';output.write_bytes(data)
                    with Image.open(output) as image:
                        image.load()
                        if without_runtime_fields(json.loads(image.info['prompt']))!=without_runtime_fields(graph):raise ValueError('PNG graph mismatch')
                        size=list(image.size)
                    record.update(status='complete',output=output.relative_to(ROOT).as_posix(),output_sha256=sha(output),output_size=size)
                    save(record_path,record);break
                time.sleep(5)
            else:raise TimeoutError('Study submission unresolved; do not resubmit')
            print(json.dumps({k:record.get(k) for k in ('sample_id','seed','status','execution_seconds','sampled_device_peak_mib')}),flush=True)
    print('All declared study outputs terminal. Independent matched visual scoring remains required.',flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--protocol',type=Path,required=True);parser.add_argument('--wait-for-baseline',action='store_true');args=parser.parse_args();run(args.protocol,args.wait_for_baseline)
