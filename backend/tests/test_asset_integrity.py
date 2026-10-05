import httpx
from .test_api import TestClient,quality_settings,submit,wait_for
from .comfy_stub import ComfyService

def test_completed_result_is_not_served_or_saved_after_file_changes(tmp_path):
    from backend.app.main import create_app
    settings=quality_settings(tmp_path,poll_seconds=.01);service=ComfyService();service.finished=True
    with TestClient(create_app(settings,transport=httpx.MockTransport(service))) as client:
        job=submit(client).json();wait_for(client,job['id'],'complete')
        (settings.data_dir/'jobs'/job['id']/'result.png').write_bytes(b'changed')
        assert client.get(f"/api/try-on/{job['id']}/result").status_code==409
        assert client.post('/api/looks',json={'job_id':job['id'],'name':'Changed','consent':True}).status_code==409
