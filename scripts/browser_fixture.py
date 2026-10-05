"""Controlled local UI verification service. Never contacts a GPU or enables real quality.

Run with .venv/Scripts/python -m scripts.browser_fixture; listen only on 127.0.0.1:8801.
All test routes and synthetic acceptance data exist only in this separate process.
"""
import hashlib
import json
from io import BytesIO

import httpx
from PIL import Image
from backend.app.main import create_app
from backend.app.settings import ROOT, Settings

fixture = ROOT / '.local/browser-fixture'
fixture.mkdir(parents=True, exist_ok=True)
config = json.loads((ROOT / 'backend/workflow.json').read_text())
report = fixture / 'test-only-quality.json'
categories = ['shirt', 'hoodie', 'jacket', 'coat']
report.write_text(json.dumps({'status': 'passed', 'quality_gate_passed': True,
    'expected': 40, 'recorded': 40, 'scored': 40, 'inference_failures': 0, 'passed': 40,
    'validated_categories': categories, 'categories': {c: {'passed': 10} for c in categories},
    'workflow_template_sha256': config['graph_sha256'],
    'prompt_hashes': {r: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for r,p in config['prompts'].items()},
    'environment_sha256': hashlib.sha256((ROOT / 'evaluation/environment.json').read_bytes()).hexdigest()}))
for name, color in [('person', '#335C77'), ('garment', '#D9E67A')]:
    Image.new('RGB', (360, 480), color).save(fixture / (name + '.png'))
(fixture / 'invalid.png').write_bytes(b'not an image')

class Service:
    ready = True
    finished = False
    submissions = []
    def __call__(self, request):
        path = request.url.path
        if not self.ready:
            raise httpx.ConnectError('Controlled offline service', request=request)
        if path == '/system_stats': return httpx.Response(200, json={'system': {}, 'devices': []})
        if path == '/object_info':
            graph = json.loads((ROOT / config['graph']).read_text())
            catalog = {n['class_type']: {'input': {'required': {}}} for n in graph.values()}
            for node in graph.values():
                for key in ('unet_name','clip_name','vae_name'):
                    if key in node['inputs']: catalog[node['class_type']]['input']['required'][key] = [[node['inputs'][key]]]
            return httpx.Response(200, json=catalog)
        if path == '/upload/image':
            from email.parser import BytesParser
            message = BytesParser().parsebytes(('Content-Type: '+request.headers['content-type']+'\r\n\r\n').encode()+request.read())
            part = next(p for p in message.walk() if p.get_filename())
            return httpx.Response(200,json={'name':part.get_filename(),'subfolder':'','type':'input'})
        if path == '/prompt':
            data = json.loads(request.read()); data['id'] = 'fixture-'+str(len(self.submissions)); self.submissions.append(data)
            self.finished = False
            return httpx.Response(200,json={'prompt_id':data['id'],'node_errors':{}})
        if path == '/queue':
            return httpx.Response(200,json={'queue_running':[] if self.finished or not self.submissions else [self.prompt(self.submissions[-1])], 'queue_pending':[]})
        if path.startswith('/history'):
            rows = {} if not self.finished else {d['id']:{'prompt':self.prompt(d),'status':{'completed':True,'status_str':'success'},
                'outputs':{config['output_node']:{'images':[{'filename':f"cf_{d['client_id']}_result.png",'type':'output','subfolder':''}]}}} for d in self.submissions}
            return httpx.Response(200,json=rows)
        if path == '/view':
            data = BytesIO(); Image.new('RGB',(360,480),'#9A6A82').save(data,format='PNG')
            return httpx.Response(200,content=data.getvalue())
        raise AssertionError(path)
    def prompt(self,d): return [0,d['id'],d['prompt'],{'client_id':d['client_id']},[config['output_node']]]

service = Service()
class FixtureProtection:
    available=True
    report_hash='test-only-protection'
    async def apply(self,job,directory,data):
        return data,dict(applied=False,fallback_reason='Controlled uncertain boundary; standard fixture preview retained',raw_sha256=hashlib.sha256(data).hexdigest(),report_sha256=self.report_hash)
features=fixture/'test-only-features.json'
features.write_text(json.dumps({'baseline_quality_sha256':hashlib.sha256(report.read_bytes()).hexdigest(),
    'implementation_sha256':hashlib.sha256((ROOT/'backend/app/references.py').read_bytes()).hexdigest(),
    'modes':{'multi_reference':{'status':'passed','reviewed':8,'preservation_noninferior':True,'fidelity_improved':True,'verified_total_inputs':5,'categories':['hoodie','jacket'],'reference_roles':{'hoodie':['detail'],'jacket':['back','side','detail']}},
             'two_garment':{'status':'passed','reviewed':16,'preservation_noninferior':True,'all_combinations_passed':True,'verified_total_inputs':3,'combinations':['shirt+jacket','shirt+coat'],'outfit_implementation_sha256':hashlib.sha256((ROOT/'backend/app/outfits.py').read_bytes()).hexdigest()}}}))
app = create_app(Settings(data_dir=fixture/'app',quality_manifest=report,feature_manifest=features,poll_seconds=.1),transport=httpx.MockTransport(service),protection_adapter=FixtureProtection())

@app.post('/__test/control')
def control(finished: bool | None = None, ready: bool | None = None):
    if finished is not None: service.finished = finished
    if ready is not None: service.ready = ready
    return {'submissions':len(service.submissions)}

@app.get('/__test/observations')
def observations():
    return {'submissions':len(service.submissions),'seeds':[d['prompt'][config['sampler_node']]['inputs']['seed'] for d in service.submissions]}

# create_app mounts the production static UI last; insert only these test routes before it.
app.router.routes[-3:] = app.router.routes[-2:] + app.router.routes[-3:-2]

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8801,access_log=False)
