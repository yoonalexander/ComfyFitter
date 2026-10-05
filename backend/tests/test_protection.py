import hashlib,httpx
from backend.app.main import create_app
from .test_api import TestClient,quality_settings,image_bytes,wait_for,offline
from .comfy_stub import ComfyService
def submit(client,key='protection-key',protected='true'):
    return client.post('/api/try-on',headers={'Idempotency-Key':key},data={'category':'shirt','protect_regions':protected},files={'person':('person.png',image_bytes(),'image/png'),'garment':('garment.png',image_bytes(),'image/png')})
def test_protection_cannot_be_requested_before_its_own_quality_and_runtime_gate(tmp_path):
    with TestClient(create_app(quality_settings(tmp_path),transport=httpx.MockTransport(offline))) as client:
        assert client.get('/api/health').json()['spatial_protection_available'] is False
        denied=submit(client)
        assert denied.status_code==503 and denied.json()['error']['code']=='PROTECTION_NOT_VALIDATED'

class ControlledProtection:
    available=True
    report_hash='test-only-report'
    async def apply(self,job,directory,data):
        return data,dict(applied=False,fallback_reason='Controlled conservative raw fallback',raw_sha256=hashlib.sha256(data).hexdigest(),report_sha256=self.report_hash)

def test_opt_in_protection_is_a_durable_request_choice_and_preserves_raw_fallback(tmp_path):
    service=ComfyService();service.finished=True
    with TestClient(create_app(quality_settings(tmp_path,poll_seconds=.01),transport=httpx.MockTransport(service),protection_adapter=ControlledProtection())) as client:
        accepted=submit(client);assert accepted.status_code==202
        job=wait_for(client,accepted.json()['id'],'complete')
        assert job['manifest']['protect_regions'] is True
        assert job['manifest']['protection']['fallback_reason']=='Controlled conservative raw fallback'
        assert hashlib.sha256(client.get(f"/api/try-on/{job['id']}/result").content).hexdigest()==job['manifest']['protection']['raw_sha256']
        assert submit(client,protected='false').status_code==409
        assert len(service.submissions)==1
