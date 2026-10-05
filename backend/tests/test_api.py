"""Verify the roadmap's API behavior against the external ComfyUI HTTP boundary."""
import httpx
import pytest
import json
import time
from io import BytesIO
from PIL import Image
from fastapi.testclient import TestClient as FastAPIClient
from functools import partial

TestClient = partial(FastAPIClient, base_url='http://127.0.0.1')


@pytest.mark.parametrize('headers', [{'Origin': 'https://another-site.example'},
                                    {'Origin': 'null'},
                                    {'Host': 'another-site.example'}])
def test_local_api_rejects_foreign_browser_origins_and_nonlocal_hosts(tmp_path, headers):
    from backend.app.main import create_app
    from backend.app.settings import Settings
    with TestClient(create_app(Settings(data_dir=tmp_path), transport=httpx.MockTransport(offline))) as client:
        response = client.post('/api/try-on', data={'category': 'shirt'}, headers=headers,
                               files={'person': ('fake.png', b'bad', 'image/png'),
                                      'garment': ('fake.png', b'bad', 'image/png')})
    assert response.status_code == 403
    assert response.json()['error']['code'] == 'LOCAL_ACCESS_DENIED'


@pytest.mark.parametrize('missing', ['node', 'model'])
def test_health_distinguishes_reachable_service_from_missing_workflow_dependencies(tmp_path, missing):
    from backend.app.main import create_app
    from backend.app.settings import Settings, ROOT
    graph = json.loads((ROOT / 'workflows/qwen_tryon_upper_candidate_gguf.api.json').read_text())

    def service(request):
        if request.url.path == '/system_stats':
            return httpx.Response(200, json={'system': {}, 'devices': []})
        if request.url.path == '/object_info':
            catalog = {n['class_type']: {'input': {'required': {}}} for n in graph.values()}
            if missing == 'node':
                del catalog['UnetLoaderGGUF']
            return httpx.Response(200, json=catalog)
        raise AssertionError(request.url.path)

    with TestClient(create_app(Settings(data_dir=tmp_path), transport=httpx.MockTransport(service))) as client:
        health = client.get('/api/health')
    assert health.status_code == 200
    assert health.json()['app'] == 'ok'
    assert health.json()['comfyui']['ready'] is False
    assert health.json()['comfyui']['reachable'] is True
    assert health.json()['comfyui']['error']['code'] == 'COMFYUI_NOT_CONFIGURED'


def image_bytes(size=(64, 64), format='PNG'):
    output = BytesIO()
    Image.new('RGB', size, '#557766').save(output, format=format)
    return output.getvalue()


def test_invalid_completed_output_fails_cleanly_and_does_not_stall_the_worker(tmp_path):
    from backend.app.main import create_app
    from .comfy_stub import ComfyService
    service = ComfyService()
    service.finished = True
    def boundary(request):
        if request.url.path == '/view':
            return httpx.Response(200, content=b'broken PNG from completed inference')
        return service(request)
    with TestClient(create_app(quality_settings(tmp_path, poll_seconds=.01), transport=httpx.MockTransport(boundary))) as client:
        job = submit(client).json()
        failed = wait_for(client, job['id'], 'failed')
        assert failed['error']['code'] == 'RESULT_INVALID'
        assert failed['upstream_active'] is False
        assert client.get(f"/api/try-on/{job['id']}/result").status_code == 409
        assert client.delete(f"/api/try-on/{job['id']}").status_code == 200


def offline(request):
    raise httpx.ConnectError('offline test service', request=request)


def quality_settings(tmp_path, **overrides):
    """Synthetic acceptance data for API tests, not a publishable evaluation."""
    import hashlib
    import json
    from backend.app.settings import ROOT, Settings
    report = tmp_path / 'test_only_quality.json'
    config = json.loads((ROOT / 'backend/workflow.json').read_text())
    report.write_text(json.dumps({'status': 'passed', 'expected': 40, 'recorded': 40,
        'scored': 40, 'passed': 40, 'inference_failures': 0, 'quality_gate_passed': True,
        'validated_categories': ['shirt', 'hoodie', 'jacket', 'coat'],
        'categories': {c: {'expected': 10, 'passed': 10} for c in ('shirt','hoodie','jacket','coat')},
        'workflow_template_sha256': config['graph_sha256'],
        'prompt_hashes': {role: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                          for role,path in config['prompts'].items()},
        'environment_sha256': hashlib.sha256((ROOT / 'evaluation/environment.json').read_bytes()).hexdigest()}))
    return Settings(data_dir=tmp_path / 'app', quality_manifest=report, **overrides)


def submit(client, seed=42, key=None, person=None):
    return client.post('/api/try-on', data={'category': 'shirt', 'seed': str(seed)},
                       files={'person': ('portrait.png', person or image_bytes(), 'image/png'),
                              'garment': ('shirt.png', image_bytes(), 'image/png')},
                       headers={'Idempotency-Key': key} if key else {})


def wait_for(client, job_id, state, seconds=3):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        status = client.get(f'/api/try-on/{job_id}').json()
        if status['state'] == state:
            return status
        time.sleep(0.01)
    raise AssertionError(status)


def test_deadline_keeps_tracking_gpu_and_prevents_cleanup_or_concurrent_submission(tmp_path):
    from backend.app.main import create_app
    from .comfy_stub import ComfyService
    comfy = ComfyService()
    settings = quality_settings(tmp_path, poll_seconds=0.01, deadline_seconds=0.05)
    with TestClient(create_app(settings, transport=httpx.MockTransport(comfy))) as client:
        job_id = submit(client).json()['id']
        timed_out = wait_for(client, job_id, 'failed')
        assert timed_out['error']['code'] == 'GENERATION_DEADLINE'
        assert timed_out['upstream_active'] is True
        assert timed_out['expires_at'] is None
        assert client.delete(f'/api/try-on/{job_id}').status_code == 409
        assert client.get(f'/api/try-on/{job_id}/result').status_code == 409
        assert submit(client, seed=43).status_code == 202
        time.sleep(0.05)
        assert len(comfy.submissions) == 1
        comfy.finished = True
        complete = wait_for(client, job_id, 'complete')
        assert complete['upstream_active'] is False
        assert complete['manifest']['deadline_exceeded'] is True


def test_delete_removes_job_owned_assets_in_both_services_and_preserves_unrelated_files(tmp_path):
    from backend.app.main import create_app
    from .comfy_stub import ComfyService
    comfy = ComfyService()
    comfy.finished = True
    comfy.input_dir = tmp_path / 'comfy-input'
    comfy.output_dir = tmp_path / 'comfy-output'
    for directory in (comfy.input_dir, comfy.output_dir):
        directory.mkdir()
        (directory / 'unrelated.png').write_bytes(b'unrelated bytes')
    settings = quality_settings(tmp_path, poll_seconds=0.01,
                                comfy_input_dir=comfy.input_dir, comfy_output_dir=comfy.output_dir)
    with TestClient(create_app(settings, transport=httpx.MockTransport(comfy))) as client:
        job_id = submit(client).json()['id']
        wait_for(client, job_id, 'complete')
        deleted = client.delete(f'/api/try-on/{job_id}')
        assert deleted.status_code == 200
        assert deleted.json()['assets_expired'] is True
        assert client.get(f'/api/try-on/{job_id}/result').status_code == 410
        assert client.get(f'/api/try-on/{job_id}').json()['manifest'] == {}
        assert client.delete(f'/api/try-on/{job_id}').status_code == 200
    assert sorted(p.name for p in comfy.input_dir.iterdir()) == ['unrelated.png']
    assert sorted(p.name for p in comfy.output_dir.iterdir()) == ['unrelated.png']
    assert (comfy.input_dir / 'unrelated.png').read_bytes() == b'unrelated bytes'
    with TestClient(create_app(settings, transport=httpx.MockTransport(comfy))) as restarted:
        assert restarted.get(f'/api/try-on/{job_id}/result').status_code == 410


def test_expired_images_are_removed_on_restart_without_expiring_an_active_job(tmp_path):
    from backend.app.main import create_app
    from .comfy_stub import ComfyService
    comfy = ComfyService()
    comfy.finished = True
    settings = quality_settings(tmp_path, poll_seconds=0.01, retention_seconds=0.05)
    with TestClient(create_app(settings, transport=httpx.MockTransport(comfy))) as client:
        complete_id = submit(client).json()['id']
        wait_for(client, complete_id, 'complete')
    with TestClient(create_app(settings, transport=httpx.MockTransport(offline))) as client:
        queued_id = submit(client, seed=43).json()['id']
    time.sleep(0.08)
    with TestClient(create_app(settings, transport=httpx.MockTransport(offline))) as client:
        expired = client.get(f'/api/try-on/{complete_id}').json()
        assert expired['assets_expired'] is True
        assert expired['manifest'] == {}
        assert client.get(f'/api/try-on/{complete_id}/result').status_code == 410
        queued = client.get(f'/api/try-on/{queued_id}').json()
        assert queued['state'] == 'queued'
        assert queued['assets_expired'] is False
        assert client.delete(f'/api/try-on/{queued_id}').status_code == 409


def test_streamed_multipart_body_is_bounded_even_without_content_length(tmp_path):
    from backend.app.main import create_app
    from backend.app.settings import Settings
    settings = Settings(data_dir=tmp_path, max_image_bytes=128)
    with TestClient(create_app(settings, transport=httpx.MockTransport(offline))) as client:
        response = client.post('/api/try-on', content=(b'x'*1000 for _ in range(70)),
                               headers={'Content-Type': 'multipart/form-data; boundary=test'})
    assert response.status_code == 413
    assert response.json()['error']['code'] == 'REQUEST_TOO_LARGE'


def test_only_one_backend_worker_can_use_the_same_durable_job_storage(tmp_path):
    from backend.app.main import create_app
    from backend.app.settings import Settings
    settings = Settings(data_dir=tmp_path)
    transport = httpx.MockTransport(offline)
    with TestClient(create_app(settings, transport=transport)):
        with pytest.raises(RuntimeError, match='already using this storage'):
            with TestClient(create_app(settings, transport=transport)):
                pass
    with TestClient(create_app(settings, transport=transport)) as restarted:
        assert restarted.get('/api/health').status_code == 200


@pytest.mark.parametrize('failure,code', [('graph', 'INVALID_WORKFLOW'),
                                         ('execution', 'INFERENCE_FAILED'),
                                         ('output', 'RESULT_MISMATCH')])
def test_inference_failures_are_typed_and_do_not_serve_unrelated_outputs(tmp_path, failure, code):
    from backend.app.main import create_app
    from .comfy_stub import ComfyService
    service = ComfyService()
    service.finished = True

    def failing(request):
        if failure == 'graph' and request.url.path == '/prompt':
            return httpx.Response(400, json={'error': 'invalid graph', 'node_errors': {'unknown': {}}})
        response = service(request)
        if request.url.path.startswith('/history'):
            data = response.json()
            if failure == 'execution':
                data['controlled-prompt']['status']['status_str'] = 'error'
            elif failure == 'output':
                data['controlled-prompt']['outputs']['461']['images'][0]['filename'] = '../unrelated.png'
            return httpx.Response(200, json=data)
        return response

    with TestClient(create_app(quality_settings(tmp_path, poll_seconds=0.01), transport=httpx.MockTransport(failing))) as client:
        job_id = submit(client).json()['id']
        failed = wait_for(client, job_id, 'failed')
        assert failed['error']['code'] == code
        assert failed['upstream_active'] is False
        assert client.get(f'/api/try-on/{job_id}/result').status_code == 409
        assert client.delete(f'/api/try-on/{job_id}').status_code == 200


def test_completed_png_is_recovered_when_the_image_service_loses_its_history(tmp_path):
    from backend.app.main import create_app
    from PIL.PngImagePlugin import PngInfo
    from .comfy_stub import ComfyService
    service = ComfyService()
    service.input_dir = tmp_path / 'input'
    output_dir = tmp_path / 'output'
    service.input_dir.mkdir()
    output_dir.mkdir()

    def lost_history(request):
        if request.url.path == '/prompt':
            data = json.loads(request.read())
            service.submissions.append(data)
            metadata = PngInfo()
            metadata.add_text('prompt', json.dumps(data['prompt']))
            Image.new('RGB', (64, 64), 'blue').save(
                output_dir / ('cf_' + data['client_id'] + '_result_00001.png'), pnginfo=metadata)
            raise httpx.ReadTimeout('server finished but acknowledgement/history lost', request=request)
        if request.url.path == '/queue':
            return httpx.Response(200, json={'queue_running': [], 'queue_pending': []})
        if request.url.path.startswith('/history'):
            return httpx.Response(200, json={})
        return service(request)

    settings = quality_settings(tmp_path, poll_seconds=0.01,
                                comfy_input_dir=service.input_dir, comfy_output_dir=output_dir)
    with TestClient(create_app(settings, transport=httpx.MockTransport(lost_history))) as client:
        job_id = submit(client).json()['id']
        complete = wait_for(client, job_id, 'complete')
        assert complete['manifest']['recovery']['kind'] == 'png_embedded_graph'
        assert complete['manifest']['gpu_execution_seconds'] is None
        assert client.get(f'/api/try-on/{job_id}/result').status_code == 200
        assert len(service.submissions) == 1
        assert client.delete(f'/api/try-on/{job_id}').status_code == 200
    assert list(output_dir.iterdir()) == []


def test_malformed_acknowledgement_does_not_crash_worker_or_resubmit(tmp_path):
    from backend.app.main import create_app
    from .comfy_stub import ComfyService
    service = ComfyService()
    count = 0

    def malformed(request):
        nonlocal count
        if request.url.path == '/prompt':
            count += 1
            return httpx.Response(200, json=[])
        return service(request)

    with TestClient(create_app(quality_settings(tmp_path, poll_seconds=0.01, deadline_seconds=0.05),
                              transport=httpx.MockTransport(malformed))) as client:
        job_id = submit(client).json()['id']
        failed = wait_for(client, job_id, 'failed')
        assert failed['error']['code'] == 'GENERATION_DEADLINE'
        assert failed['upstream_active'] is True
        assert client.delete(f'/api/try-on/{job_id}').status_code == 409
    assert count == 1


def test_single_reference_api_rejects_duplicate_garments_instead_of_silently_choosing_one(tmp_path):
    from backend.app.main import create_app
    from backend.app.settings import Settings
    with TestClient(create_app(Settings(data_dir=tmp_path), transport=httpx.MockTransport(offline))) as client:
        response = client.post('/api/try-on', data={'category': 'shirt'}, files=[
            ('person', ('person.png', image_bytes(), 'image/png')),
            ('garment', ('front.png', image_bytes(), 'image/png')),
            ('garment', ('back.png', image_bytes(), 'image/png'))])
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'INVALID_REFERENCE_COUNT'


def test_queue_runs_one_job_at_a_time_and_keeps_seeds_prompts_and_results_isolated(tmp_path):
    from backend.app.main import create_app
    from .comfy_stub import ComfyService
    uploads = ComfyService()
    submissions, completed = [], set()

    def service(request):
        path = request.url.path
        if path == '/upload/image':
            return uploads(request)
        if path == '/queue':
            active = [[i, str(i), row['prompt'], {'client_id': row['client_id']}, ['461']]
                      for i, row in enumerate(submissions) if str(i) not in completed]
            return httpx.Response(200, json={'queue_running': active, 'queue_pending': []})
        if path == '/prompt':
            submissions.append(json.loads(request.read()))
            return httpx.Response(200, json={'prompt_id': str(len(submissions)-1), 'node_errors': {}})
        if path.startswith('/history/'):
            prompt_id = path.rsplit('/', 1)[1]
            if prompt_id not in completed:
                return httpx.Response(200, json={})
            row = submissions[int(prompt_id)]
            return httpx.Response(200, json={prompt_id: {
                'prompt': [0, prompt_id, row['prompt'], {'client_id': row['client_id']}, ['461']],
                'status': {'completed': True, 'status_str': 'success'},
                'outputs': {'461': {'images': [{'filename': f"cf_{row['client_id']}_result.png", 'subfolder': '', 'type': 'output'}]}}}})
        if path == '/view':
            row = next(r for r in submissions if r['client_id'] in request.url.params['filename'])
            seed = row['prompt']['459:458']['inputs']['seed']
            stream = BytesIO(); Image.new('RGB', (64,64), 'red' if seed == 10 else 'blue').save(stream,format='PNG')
            return httpx.Response(200, content=stream.getvalue())
        raise AssertionError(path)

    with TestClient(create_app(quality_settings(tmp_path, poll_seconds=0.01), transport=httpx.MockTransport(service))) as client:
        first_id = submit(client, seed=10).json()['id']
        second = client.post('/api/try-on', data={'category': 'coat', 'seed': '20'},
                             files={'person': ('person.png', image_bytes(), 'image/png'),
                                    'garment': ('coat.png', image_bytes(), 'image/png')})
        assert second.status_code == 202
        second_id = second.json()['id']
        wait_for(client, first_id, 'processing')
        time.sleep(0.05)
        assert len(submissions) == 1
        assert client.get(f'/api/try-on/{second_id}').json()['state'] == 'queued'
        completed.add('0')
        wait_for(client, first_id, 'complete')
        wait_for(client, second_id, 'processing')
        completed.add('1')
        wait_for(client, second_id, 'complete')
        assert len(submissions) == 2
        assert [r['prompt']['459:458']['inputs']['seed'] for r in submissions] == [10, 20]
        assert 'actual shirt' in submissions[0]['prompt']['459:474']['inputs']['prompt']
        assert 'coat' in submissions[1]['prompt']['459:474']['inputs']['prompt']
        assert submissions[0]['prompt']['470']['inputs']['image'] != submissions[1]['prompt']['470']['inputs']['image']
        first = client.get(f'/api/try-on/{first_id}/result')
        second = client.get(f'/api/try-on/{second_id}/result')
        with Image.open(BytesIO(first.content)) as image:
            assert image.getpixel((0,0)) == (255,0,0)
        with Image.open(BytesIO(second.content)) as image:
            assert image.getpixel((0,0)) == (0,0,255)


def test_restart_fails_a_queued_job_with_missing_input_without_submitting_gpu_work(tmp_path):
    from backend.app.main import create_app
    settings = quality_settings(tmp_path)
    transport = httpx.MockTransport(offline)
    with TestClient(create_app(settings, transport=transport)) as client:
        job_id = submit(client).json()['id']
    (settings.data_dir / 'jobs' / job_id / 'person.png').unlink()
    with TestClient(create_app(settings, transport=transport)) as restarted:
        status = restarted.get(f'/api/try-on/{job_id}').json()
        assert status['state'] == 'failed'
        assert status['error']['code'] == 'INPUT_UNAVAILABLE'
        assert status['upstream_active'] is False
        assert restarted.delete(f'/api/try-on/{job_id}').status_code == 200


def test_startup_cleans_aged_untracked_upload_folders_but_preserves_recent_or_unmanaged_files(tmp_path):
    import os
    import uuid
    from backend.app.main import create_app
    from backend.app.settings import Settings
    settings = Settings(data_dir=tmp_path / 'app')
    orphan = settings.data_dir / 'jobs' / str(uuid.uuid4())
    recent = settings.data_dir / 'jobs' / str(uuid.uuid4())
    unmanaged = settings.data_dir / 'jobs' / 'manual-notes'
    for directory in (orphan, recent, unmanaged):
        directory.mkdir(parents=True)
        (directory / 'file.png').write_bytes(image_bytes())
    old = time.time() - 90000
    os.utime(orphan / 'file.png', (old,old))
    os.utime(orphan, (old,old))
    with TestClient(create_app(settings, transport=httpx.MockTransport(offline))) as client:
        assert client.get('/api/health').status_code == 200
    assert not orphan.exists()
    assert (recent / 'file.png').exists()
    assert (unmanaged / 'file.png').exists()


def test_retained_inputs_can_be_restored_for_comparison_and_retry_until_deletion(tmp_path):
    from backend.app.main import create_app
    from .comfy_stub import ComfyService
    service = ComfyService(); service.finished = True
    with TestClient(create_app(quality_settings(tmp_path,poll_seconds=0.01), transport=httpx.MockTransport(service))) as client:
        job_id = submit(client).json()['id']
        wait_for(client,job_id,'complete')
        for role in ('person','garment'):
            response = client.get(f'/api/try-on/{job_id}/inputs/{role}')
            assert response.status_code == 200
            assert response.headers['cache-control'] == 'no-store'
            with Image.open(BytesIO(response.content)) as image:
                assert image.size == (64,64)
                assert image.format == 'PNG'
                assert not image.getexif()
        assert client.get(f'/api/try-on/{job_id}/inputs/other').status_code == 422
        assert client.delete(f'/api/try-on/{job_id}').status_code == 200
        assert client.get(f'/api/try-on/{job_id}/inputs/person').status_code == 410


def test_browser_can_recover_accepted_job_by_request_key_after_losing_the_response(tmp_path):
    from backend.app.main import create_app
    settings = quality_settings(tmp_path)
    transport = httpx.MockTransport(offline)
    with TestClient(create_app(settings,transport=transport)) as client:
        assert client.get('/api/submissions/not-yet-accepted').status_code == 404
        job_id = submit(client,key='recover-browser-request').json()['id']
    with TestClient(create_app(settings,transport=transport)) as restarted:
        response = restarted.get('/api/submissions/recover-browser-request')
        assert response.status_code == 200
        assert response.json()['id'] == job_id
        assert response.json()['state'] == 'queued'


def test_queue_rejects_more_work_at_capacity_but_replays_existing_request(tmp_path):
    from backend.app.main import create_app
    settings = quality_settings(tmp_path, queue_capacity=1)
    with TestClient(create_app(settings, transport=httpx.MockTransport(offline))) as client:
        first = submit(client, key='one')
        assert first.status_code == 202
        assert submit(client, seed=43).status_code == 429
        replay = submit(client, key='one')
        assert replay.status_code == 202
        assert replay.json()['id'] == first.json()['id']


def test_generation_uploads_normalized_images_and_serves_a_reproducible_result(tmp_path):
    from backend.app.main import create_app
    from email.parser import BytesParser
    from email.policy import default
    uploads, submitted = [], []
    result_bytes = image_bytes((96, 64))

    def comfy(request):
        path = request.url.path
        if path == '/queue':
            return httpx.Response(200, json={'queue_running': [], 'queue_pending': []})
        if path == '/upload/image':
            message = BytesParser(policy=default).parsebytes(
                ('Content-Type: ' + request.headers['content-type'] + '\r\n\r\n').encode() + request.read())
            part = next(p for p in message.iter_parts() if p.get_param('name', header='content-disposition') == 'image')
            with Image.open(BytesIO(part.get_payload(decode=True))) as image:
                uploads.append((image.size, dict(image.getexif()), image.format))
            return httpx.Response(200, json={'name': part.get_filename(), 'subfolder': '', 'type': 'input'})
        if path == '/prompt':
            data = json.loads(request.read())
            submitted.append(data)
            return httpx.Response(200, json={'prompt_id': 'test-prompt', 'node_errors': {}})
        if path == '/history/test-prompt':
            data = submitted[0]
            return httpx.Response(200, json={'test-prompt': {
                'prompt': [0, 'test-prompt', data['prompt'], {'client_id': data['client_id']}, ['461']],
                'status': {'completed': True, 'status_str': 'success'},
                'outputs': {'461': {'images': [{'filename': 'cf_' + data['client_id'] + '_result.png',
                                               'subfolder': '', 'type': 'output'}]}}}})
        if path == '/view':
            return httpx.Response(200, content=result_bytes)
        raise AssertionError('Unexpected inference call: ' + path)

    portrait = BytesIO()
    exif = Image.Exif()
    exif[274] = 6
    exif[315] = 'private metadata'
    Image.new('RGB', (64, 96), 'orange').save(portrait, format='JPEG', exif=exif)
    app = create_app(quality_settings(tmp_path, poll_seconds=0.01), transport=httpx.MockTransport(comfy))
    with TestClient(app) as client:
        accepted = submit(client, person=portrait.getvalue())
        assert accepted.status_code == 202
        job_id = accepted.json()['id']
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            status = client.get(f'/api/try-on/{job_id}').json()
            if status['state'] in ('complete', 'failed'):
                break
            time.sleep(0.01)
        assert status['state'] == 'complete', status
        output = client.get(f'/api/try-on/{job_id}/result')
        assert output.status_code == 200
        assert output.content == result_bytes
        assert uploads == [((96, 64), {}, 'PNG'), ((64, 64), {}, 'PNG')]
        assert len(submitted) == 1
        graph = submitted[0]['prompt']
        assert graph['459:458']['inputs']['seed'] == 42
        assert 'shirt' in graph['459:474']['inputs']['prompt']
        assert status['manifest']['images']['person']['size'] == [96, 64]
        assert status['manifest']['api_graph_sha256']
        assert status['manifest']['result_sha256']


def test_lost_submission_acknowledgement_reconciles_after_restart_without_duplicate_gpu_work(tmp_path):
    from backend.app.main import create_app
    submitted = []
    finished = False

    def comfy(request):
        path = request.url.path
        if path == '/upload/image':
            from email.parser import BytesParser
            message = BytesParser().parsebytes(('Content-Type: ' + request.headers['content-type'] + '\r\n\r\n').encode() + request.read())
            part = next(p for p in message.walk() if p.get_filename())
            return httpx.Response(200, json={'name': part.get_filename(), 'subfolder': '', 'type': 'input'})
        if path == '/prompt':
            submitted.append(json.loads(request.read()))
            raise httpx.ReadTimeout('ack lost after upstream accepted', request=request)
        if path == '/queue':
            running = [] if not submitted or finished else [[0, 'accepted-once', submitted[0]['prompt'],
                        {'client_id': submitted[0]['client_id']}, ['461']]]
            return httpx.Response(200, json={'queue_running': running, 'queue_pending': []})
        if path.startswith('/history'):
            data = submitted[0]
            history = {'prompt': [0, 'accepted-once', data['prompt'], {'client_id': data['client_id']}, ['461']],
                'status': {'completed': finished, 'status_str': 'success' if finished else 'running'},
                'outputs': {'461': {'images': [{'filename': 'cf_' + data['client_id'] + '_result.png', 'subfolder': '', 'type': 'output'}]}}}
            return httpx.Response(200, json={'accepted-once': history} if finished or path != '/history' else {})
        if path == '/view':
            return httpx.Response(200, content=image_bytes())
        raise AssertionError(path)

    settings = quality_settings(tmp_path, poll_seconds=0.01)
    transport = httpx.MockTransport(comfy)
    with TestClient(create_app(settings, transport=transport)) as client:
        job_id = submit(client, key='lost-ack').json()['id']
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and not submitted:
            time.sleep(0.01)
        assert len(submitted) == 1
    finished = True
    with TestClient(create_app(settings, transport=transport)) as restarted:
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            status = restarted.get(f'/api/try-on/{job_id}').json()
            if status['state'] == 'complete':
                break
            time.sleep(0.01)
        assert status['state'] == 'complete', status
        assert submit(restarted, key='lost-ack').json()['id'] == job_id
    assert len(submitted) == 1


def test_job_is_durable_and_idempotency_reuses_only_identical_submissions(tmp_path):
    """The test-only report enables HTTP contract testing, never a real quality claim."""
    import hashlib
    import json
    from pathlib import Path
    from backend.app.main import create_app
    from backend.app.settings import Settings, ROOT

    report = tmp_path / 'test_only_quality.json'
    config = json.loads((ROOT / 'backend/workflow.json').read_text())
    report.write_text(json.dumps({'status': 'passed', 'expected': 40, 'recorded': 40,
        'scored': 40, 'passed': 40, 'inference_failures': 0, 'quality_gate_passed': True,
        'validated_categories': ['shirt', 'hoodie', 'jacket', 'coat'],
        'categories': {c: {'expected': 10, 'passed': 10} for c in ('shirt','hoodie','jacket','coat')},
        'workflow_template_sha256': config['graph_sha256'],
        'prompt_hashes': {role: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                          for role,path in config['prompts'].items()},
        'environment_sha256': hashlib.sha256((ROOT / 'evaluation/environment.json').read_bytes()).hexdigest()}))
    settings = Settings(data_dir=tmp_path / 'app', quality_manifest=report)
    files = {'person': ('portrait.png', image_bytes(), 'image/png'),
             'garment': ('shirt.png', image_bytes(), 'image/png')}
    with TestClient(create_app(settings, transport=httpx.MockTransport(offline))) as client:
        response = client.post('/api/try-on', data={'category': 'shirt', 'seed': '42'},
                               files=files, headers={'Idempotency-Key': 'example-request'})
        assert response.status_code == 202
        job_id = response.json()['id']
        duplicate = client.post('/api/try-on', data={'category': 'shirt', 'seed': '42'},
                               files=files, headers={'Idempotency-Key': 'example-request'})
        assert duplicate.json()['id'] == job_id
        changed = client.post('/api/try-on', data={'category': 'shirt', 'seed': '43'},
                             files=files, headers={'Idempotency-Key': 'example-request'})
        assert changed.status_code == 409
    with TestClient(create_app(settings, transport=httpx.MockTransport(offline))) as restarted:
        status = restarted.get(f'/api/try-on/{job_id}')
        assert status.status_code == 200
        assert status.json()['id'] == job_id
        assert status.json()['state'] == 'queued'
        assert status.json()['seed'] == 42


@pytest.mark.parametrize('data,expected_status,code', [
    (image_bytes(format='BMP'), 422, 'UNSUPPORTED_IMAGE'),
    (image_bytes((70, 70)), 422, 'IMAGE_PIXELS_EXCEEDED'),
    (b'x' * 16385, 413, 'IMAGE_TOO_LARGE')], ids=['format', 'pixels', 'bytes'])
def test_try_on_bounds_decoded_format_pixels_and_bytes(tmp_path, data, expected_status, code):
    from backend.app.main import create_app
    from backend.app.settings import Settings
    app = create_app(Settings(data_dir=tmp_path, max_image_bytes=16384, max_image_pixels=4096))
    with TestClient(app) as client:
        response = client.post('/api/try-on', data={'category': 'shirt'}, files={
            'person': ('pretends.png', data, 'image/png'),
            'garment': ('shirt.png', image_bytes(), 'image/png')})
    assert response.status_code == expected_status
    assert response.json()['error']['code'] == code


def test_try_on_rejects_fake_image_bytes_before_any_inference(tmp_path):
    from backend.app.main import create_app
    from backend.app.settings import Settings

    def unexpected_call(request):
        raise AssertionError('Invalid photos must not reach ComfyUI')

    with TestClient(create_app(Settings(data_dir=tmp_path), transport=httpx.MockTransport(unexpected_call))) as client:
        response = client.post('/api/try-on', data={'category': 'shirt'}, files={
            'person': ('portrait.png', b'not an image', 'image/png'),
            'garment': ('shirt.png', b'not an image', 'image/png')})
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'INVALID_IMAGE'


def test_app_health_remains_available_when_comfyui_is_offline(tmp_path):
    from backend.app.main import create_app

    def offline(request):
        raise httpx.ConnectError('offline service', request=request)

    app = create_app(quality_settings(tmp_path), transport=httpx.MockTransport(offline))
    with TestClient(app) as client:
        response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json()['app'] == 'ok'
    assert response.json()['comfyui']['ready'] is False
    # Qualification is independent of current service availability.
    assert response.json()['supported_categories'] == ['shirt', 'hoodie', 'jacket', 'coat']
