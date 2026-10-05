import json,httpx,pytest
from .test_api import quality_settings,TestClient,offline,submit

@pytest.mark.parametrize('field',['workflow_template_sha256','environment_sha256','prompt_hashes'])
def test_quality_acceptance_must_match_exact_deployed_workflow_and_environment(tmp_path,field):
    from backend.app.main import create_app
    settings=quality_settings(tmp_path)
    report=json.loads(settings.quality_manifest.read_text());report[field]='different-version'
    settings.quality_manifest.write_text(json.dumps(report))
    with TestClient(create_app(settings,transport=httpx.MockTransport(offline))) as client:
        assert client.get('/api/health').json()['supported_categories']==[]
        rejected=submit(client)
        assert rejected.status_code==503
        assert rejected.json()['error']['code']=='QUALITY_NOT_VALIDATED'
