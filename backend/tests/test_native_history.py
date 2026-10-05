import copy,httpx,pytest
from backend.app.main import create_app
from .test_api import TestClient,quality_settings,submit,wait_for
from .comfy_stub import ComfyService

@pytest.mark.parametrize('outputs',[None,[],{'461':None},{'461':{'images':[None]}}])
def test_malformed_completed_output_does_not_kill_durable_worker(tmp_path,outputs):
    service=ComfyService();service.finished=True
    def boundary(request):
        reply=service(request)
        if request.url.path.startswith('/history'):
            body=reply.json();body['controlled-prompt']['outputs']=outputs
            return httpx.Response(200,json=body)
        return reply
    with TestClient(create_app(quality_settings(tmp_path,poll_seconds=.01),transport=httpx.MockTransport(boundary))) as client:
        row=wait_for(client,submit(client).json()['id'],'failed')
        assert row['error']['code']=='RESULT_MISSING' and row['upstream_active'] is False
        assert client.get(f"/api/try-on/{row['id']}/result").status_code==409

def test_native_runtime_cache_annotations_do_not_change_exact_submitted_graph(tmp_path):
    service=ComfyService();service.finished=True
    def boundary(request):
        reply=service(request)
        if request.url.path.startswith('/history'):
            body=copy.deepcopy(reply.json())
            for node in body['controlled-prompt']['prompt'][2].values():node['is_changed']=['native-runtime-annotation']
            return httpx.Response(200,json=body)
        return reply
    with TestClient(create_app(quality_settings(tmp_path,poll_seconds=.01),transport=httpx.MockTransport(boundary))) as client:
        row=wait_for(client,submit(client).json()['id'],'complete')
        assert row['error'] is None and len(service.submissions)==1
