"""Saved looks use explicit consent and survive temporary-job cleanup/restart."""
import httpx
import pytest
from .test_api import TestClient, quality_settings, submit, wait_for
from .comfy_stub import ComfyService

def test_saved_look_requires_opt_in_and_survives_job_deletion_and_restart(tmp_path):
    from backend.app.main import create_app
    service = ComfyService(); service.finished = True
    settings = quality_settings(tmp_path,poll_seconds=.01)
    with TestClient(create_app(settings,transport=httpx.MockTransport(service))) as client:
        job = submit(client).json(); wait_for(client,job['id'],'complete')
        assert client.post('/api/looks',json={'job_id':job['id'],'name':'Denim day','consent':False}).status_code == 422
        response = client.post('/api/looks',json={'job_id':job['id'],'name':'Denim day','consent':True})
        assert response.status_code == 201
        look = response.json()
        result = client.get(f"/api/looks/{look['id']}/result")
        assert result.status_code == 200 and result.headers['cache-control'] == 'no-store'
        assert client.delete(f"/api/try-on/{job['id']}").status_code == 200
        assert client.get(f"/api/looks/{look['id']}/inputs/person").status_code == 200
    with TestClient(create_app(settings,transport=httpx.MockTransport(service))) as client:
        assert [r['name'] for r in client.get('/api/looks').json()['looks']] == ['Denim day']
        assert client.get(f"/api/looks/{look['id']}/result").content == result.content
        assert client.delete(f"/api/looks/{look['id']}").status_code == 204
        assert client.get(f"/api/looks/{look['id']}/result").status_code == 404
        assert client.get('/api/looks').json()['used_bytes'] == 0

@pytest.mark.parametrize('limits',[{'saved_look_capacity':1},{'saved_look_bytes':1}])
def test_saved_storage_limits_are_enforced_before_copying_more_photos(tmp_path,limits):
    from backend.app.main import create_app
    service=ComfyService();service.finished=True
    with TestClient(create_app(quality_settings(tmp_path,poll_seconds=.01,**limits),transport=httpx.MockTransport(service))) as client:
        job=submit(client).json();wait_for(client,job['id'],'complete')
        request={'job_id':job['id'],'name':'One','consent':True}
        first=client.post('/api/looks',json=request)
        assert first.status_code == (201 if 'saved_look_capacity' in limits else 429)
        denied=client.post('/api/looks',json=request)
        assert denied.status_code==429 and denied.json()['error']['code']=='LOOK_STORAGE_FULL'
