"""Read-only deployment topology validation. Does not build, start or provision anything."""
import json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def validate():
    command=['docker','compose','--env-file',str(ROOT/'deployment/.env.example'),'-f',str(ROOT/'deployment/compose.yaml'),'config','--format','json']
    result=subprocess.run(command,check=True,capture_output=True,text=True)
    config=json.loads(result.stdout);services=config['services']
    assert set(services)=={'app','worker','gateway','tls'}
    assert all(not services[name].get('ports') for name in ('app','worker','gateway'))
    assert services['tls']['ports'][0]['host_ip']=='127.0.0.1'
    assert config['networks']['inference']['internal']
    assert set(services['worker']['networks'])=={'inference'}
    assert 'inference' not in services['gateway']['networks'] and 'inference' not in services['tls']['networks']
    assert services['app']['environment']['COMFYFITTER_DEPLOYMENT_MODE']=='hosted'
    assert services['app']['environment']['COMFYFITTER_QUALITY_MANIFEST']=='/app/evaluation/summary_hosted.json'
    assert services['app']['environment']['COMFYFITTER_FEATURE_MANIFEST']=='/app/evaluation/feature_quality_hosted.json'
    for name in services:
        assert services[name]['read_only'] and services[name]['cap_drop']==['ALL']
        assert 'no-new-privileges:true' in services[name]['security_opt']
        assert services[name]['logging']['options']['max-size']=='10m'
    assert all('healthcheck' in services[name] for name in ('worker','app'))
    assert len(services['gateway']['secrets'])==2
    assert all(mount.get('read_only') for mount in services['worker']['volumes'] if mount['type']=='bind')
    print('Deployment configuration and private topology verified; no resources created.')
if __name__=='__main__':validate()
