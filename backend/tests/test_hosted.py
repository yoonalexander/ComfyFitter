"""Hosted ownership is verified at the HTTP boundary with signed test-only tokens."""
import json,time
import httpx,jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from .test_api import TestClient,quality_settings,submit,wait_for
from .comfy_stub import ComfyService

def identity():
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    jwk=json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()));jwk.update(kid='fixture',alg='RS256',use='sig')
    def token(subject,**claims):
        return jwt.encode({'iss':'https://issuer.example','aud':'fixture-app','sub':subject,'iat':int(time.time()),'exp':int(time.time())+300,**claims},key,algorithm='RS256',headers={'kid':'fixture'})
    return token,httpx.MockTransport(lambda request:httpx.Response(200,json={'keys':[jwk]}))

def test_hosted_authentication_and_job_asset_saved_look_isolation(tmp_path):
    from backend.app.main import create_app
    token,keys=identity();service=ComfyService();service.finished=True
    settings=quality_settings(tmp_path,poll_seconds=.01,deployment_mode='hosted',public_origin='https://app.example',
        oidc_issuer='https://issuer.example',oidc_audience='fixture-app',oidc_jwks_url='https://issuer.example/keys')
    with TestClient(create_app(settings,transport=httpx.MockTransport(service),identity_transport=keys),base_url='https://app.example') as client:
        assert client.get('/api/looks').status_code==401
        client.headers['Authorization']='Bearer '+token('alice')
        job=submit(client,key='same-key').json();wait_for(client,job['id'],'complete')
        look=client.post('/api/looks',json={'job_id':job['id'],'name':'Private','consent':True}).json()
        client.headers['Authorization']='Bearer '+token('bob')
        for path in [f"/api/try-on/{job['id']}",f"/api/try-on/{job['id']}/result",f"/api/try-on/{job['id']}/inputs/person",f"/api/looks/{look['id']}/result"]:
            assert client.get(path).status_code==404
        assert client.delete(f"/api/try-on/{job['id']}").status_code==404
        assert client.delete(f"/api/looks/{look['id']}").status_code==404
        assert client.get('/api/submissions/same-key').status_code==404
        assert client.get('/api/looks').json()['looks']==[]
        bob=submit(client,key='same-key').json();assert bob['id']!=job['id']
        client.headers['Authorization']='Bearer '+token('alice',exp=int(time.time())-1)
        assert client.get(f"/api/try-on/{job['id']}").status_code==401

def test_hosted_daily_limits_and_idempotency_do_not_charge_a_replay_twice(tmp_path):
    from backend.app.main import create_app
    from .test_api import offline
    token,keys=identity()
    settings=quality_settings(tmp_path,deployment_mode='hosted',public_origin='https://app.example',
        oidc_issuer='https://issuer.example',oidc_audience='fixture-app',oidc_jwks_url='https://issuer.example/keys',
        daily_user_generations=1,daily_total_generations=2)
    with TestClient(create_app(settings,transport=httpx.MockTransport(offline),identity_transport=keys),base_url='https://app.example') as client:
        client.headers['Authorization']='Bearer '+token('alice')
        first=submit(client,key='once');assert first.status_code==202
        assert submit(client,key='once').json()['id']==first.json()['id']
        assert submit(client,seed=43).json()['error']['code']=='DAILY_GENERATION_LIMIT'
        client.headers['Authorization']='Bearer '+token('bob');assert submit(client).status_code==202
        client.headers['Authorization']='Bearer '+token('charlie');assert submit(client).status_code==429

def test_hosted_request_rate_is_bounded(tmp_path):
    from backend.app.main import create_app
    from .test_api import offline
    token,keys=identity()
    settings=quality_settings(tmp_path,deployment_mode='hosted',public_origin='https://app.example',
        oidc_issuer='https://issuer.example',oidc_audience='fixture-app',oidc_jwks_url='https://issuer.example/keys',requests_per_minute=2)
    with TestClient(create_app(settings,transport=httpx.MockTransport(offline),identity_transport=keys),base_url='https://app.example') as client:
        client.headers['Authorization']='Bearer '+token('alice')
        assert client.get('/api/looks').status_code==200
        assert client.get('/api/looks').status_code==200
        denied=client.get('/api/looks');assert denied.status_code==429
        assert denied.json()['error']['code']=='REQUEST_RATE_LIMIT'

@pytest.mark.parametrize('claims',[{'iss':'https://attacker.example'},{'aud':'another-app'},
    {'exp':None},{'sub':''},{'iat':int(time.time())+3600}])
def test_hosted_tokens_require_exact_issuer_audience_and_valid_claims(tmp_path,claims):
    from backend.app.main import create_app
    from .test_api import offline
    token,keys=identity()
    settings=quality_settings(tmp_path,deployment_mode='hosted',public_origin='https://app.example',
        oidc_issuer='https://issuer.example',oidc_audience='fixture-app',oidc_jwks_url='https://issuer.example/keys')
    with TestClient(create_app(settings,transport=httpx.MockTransport(offline),identity_transport=keys),base_url='https://app.example') as client:
        client.headers['Authorization']='Bearer '+token('alice',**claims)
        assert client.get('/api/looks').status_code==401

def test_hosted_signed_identity_cannot_bypass_origin_or_host_checks(tmp_path):
    from backend.app.main import create_app
    from .test_api import offline
    token,keys=identity()
    settings=quality_settings(tmp_path,deployment_mode='hosted',public_origin='https://app.example',
        oidc_issuer='https://issuer.example',oidc_audience='fixture-app',oidc_jwks_url='https://issuer.example/keys')
    with TestClient(create_app(settings,transport=httpx.MockTransport(offline),identity_transport=keys),base_url='https://app.example') as client:
        client.headers['Authorization']='Bearer '+token('alice')
        assert client.get('/api/looks',headers={'Origin':'https://another.example'}).status_code==403
        assert client.get('/api/looks',headers={'Host':'another.example','X-Forwarded-Host':'app.example'}).status_code==403
