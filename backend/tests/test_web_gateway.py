import json
import httpx
import pytest
from starlette.testclient import TestClient
from scripts.web_gateway import create_gateway

HOST='a'*64+'.localhost'
ORIGIN='https://private-room.trycloudflare.com'

def config(tmp_path, **changes):
    path=tmp_path/'config.json'
    path.write_text(json.dumps({'private_host':HOST,'public_origin':ORIGIN,**changes}))
    return path

def upstream(request):
    assert request.url.host=='127.0.0.1' and request.url.port==8000
    assert request.headers['host']=='127.0.0.1:8000'
    assert request.headers['origin']=='http://127.0.0.1:8000'
    assert 'authorization' not in request.headers and 'cookie' not in request.headers
    if request.url.path=='/api/health':
        return httpx.Response(200,json={'process_id':123,'deployment_mode':'local','supported_categories':['shirt']})
    return httpx.Response(202 if request.method=='POST' else 200,content=b'upstream bytes')

def test_gateway_requires_private_connector_host_and_locked_https_origin(tmp_path):
    path=config(tmp_path,public_origin='')
    with TestClient(create_gateway(path,httpx.MockTransport(upstream))) as client:
        assert client.get('/api/health').status_code==403
        assert client.get('/api/health',headers={'host':HOST}).status_code==503
        path.write_text(json.dumps({'private_host':HOST,'public_origin':ORIGIN}))
        health=client.get('/api/health',headers={'host':HOST}).json()
        assert health['deployment_mode']=='hosted' and 'process_id' not in health

@pytest.mark.parametrize('path',['/system_stats','/prompt','/history','/api/unknown','/docs','/openapi.json','/.env','/assets/../../.local/config.json','/api/health?origin=evil'])
def test_gateway_never_exposes_native_worker_or_arbitrary_paths(tmp_path,path):
    with TestClient(create_gateway(config(tmp_path),httpx.MockTransport(upstream)),headers={'host':HOST}) as client:
        assert client.get(path).status_code==404

def test_gateway_rejects_cross_origin_mutations_and_strips_upstream_credentials(tmp_path):
    with TestClient(create_gateway(config(tmp_path),httpx.MockTransport(upstream)),headers={'host':HOST}) as client:
        assert client.post('/api/try-on').status_code==403
        assert client.post('/api/try-on',headers={'Origin':'https://evil.example'}).status_code==403
        assert client.get('/api/health',headers={'Origin':'null'}).status_code==403
        response=client.post('/api/try-on',headers={'Origin':ORIGIN,'Idempotency-Key':'safe-key','Authorization':'secret','Cookie':'private'},content=b'photo')
        assert response.status_code==202 and response.headers['cache-control']=='no-store'
        assert client.put('/api/looks',headers={'Origin':ORIGIN}).status_code==404

def test_gateway_daily_limit_survives_restart_and_same_key_replays(tmp_path):
    path=config(tmp_path)
    for restart in range(2):
        with TestClient(create_gateway(path,httpx.MockTransport(upstream)),headers={'host':HOST,'Origin':ORIGIN}) as client:
            if restart==0:
                for i in range(10): assert client.post('/api/try-on',headers={'Idempotency-Key':f'key-{i}'}).status_code==202
            assert client.post('/api/try-on',headers={'Idempotency-Key':'key-0'}).status_code==202
            assert client.post('/api/try-on',headers={'Idempotency-Key':'new'}).status_code==429

def test_gateway_cannot_select_another_upstream_service(tmp_path):
    with pytest.raises(ValueError): create_gateway(config(tmp_path,upstream='http://127.0.0.1:8188'))

def test_gateway_request_limit_and_failed_upstream_are_closed(tmp_path):
    def offline(request):raise httpx.ConnectError('offline',request=request)
    with TestClient(create_gateway(config(tmp_path),httpx.MockTransport(offline)),headers={'host':HOST}) as client:
        assert client.get('/api/health').status_code==503
        for i in range(119): assert client.get('/api/health').status_code==503
        assert client.get('/api/health').status_code==429
