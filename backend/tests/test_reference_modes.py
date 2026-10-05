"""Versioned feature admission and dynamic reference mapping at the public HTTP boundary."""
import hashlib,json,httpx,pytest
from .test_api import quality_settings,TestClient,image_bytes,wait_for
from .comfy_stub import ComfyService

def feature_settings(tmp_path):
    from dataclasses import replace
    from backend.app.settings import ROOT
    settings=quality_settings(tmp_path,poll_seconds=.01)
    report=tmp_path/'test-only-features.json'
    report.write_text(json.dumps({'baseline_quality_sha256':hashlib.sha256(settings.quality_manifest.read_bytes()).hexdigest(),
      'implementation_sha256':hashlib.sha256((ROOT/'backend/app/references.py').read_bytes()).hexdigest(),
      'modes':{'multi_reference':{'status':'passed','reviewed':8,'preservation_noninferior':True,'fidelity_improved':True,'verified_total_inputs':5,'categories':['shirt']},
               'two_garment':{'status':'passed','reviewed':16,'preservation_noninferior':True,'all_combinations_passed':True,'verified_total_inputs':3,'combinations':['shirt+jacket'],'outfit_implementation_sha256':hashlib.sha256((ROOT/'backend/app/outfits.py').read_bytes()).hexdigest()}}}))
    return replace(settings,feature_manifest=report)

def uploads(*roles):return [(role,(role+'.png',image_bytes(), 'image/png')) for role in roles]

def test_optional_views_map_in_front_back_side_detail_order_and_survive_restart(tmp_path):
    from backend.app.main import create_app
    settings=feature_settings(tmp_path);service=ComfyService();service.finished=True
    with TestClient(create_app(settings,transport=httpx.MockTransport(service))) as client:
        reply=client.post('/api/try-on',data={'category':'shirt','seed':'42'},files=uploads('person','detail','garment','side','back'))
        assert reply.status_code==202
        job=wait_for(client,reply.json()['id'],'complete');graph=service.submissions[0]['prompt']
        assert job['manifest']['image_order']==['person','garment','back','side','detail']
        inputs=graph['459:474']['inputs']
        for index,role in enumerate(job['manifest']['image_order'],1):
            node=inputs['images.image_'+str(index)][0]
            assert graph[node]['inputs']['image']==f"cf_{job['id']}_{role}.png"
        look=client.post('/api/looks',json={'job_id':job['id'],'name':'Five views','consent':True}).json()
    with TestClient(create_app(settings,transport=httpx.MockTransport(service))) as client:
        assert client.get(f"/api/try-on/{job['id']}/inputs/back").status_code==200
        assert client.get(f"/api/looks/{look['id']}/inputs/detail").status_code==200

def test_missing_optional_views_have_no_empty_or_old_image_slots(tmp_path):
    from backend.app.main import create_app
    service=ComfyService();service.finished=True
    with TestClient(create_app(feature_settings(tmp_path),transport=httpx.MockTransport(service))) as client:
        job=client.post('/api/try-on',data={'category':'shirt'},files=uploads('person','garment','detail')).json()
        wait_for(client,job['id'],'complete');inputs=service.submissions[0]['prompt']['459:474']['inputs']
        assert 'images.image_3' in inputs and 'images.image_4' not in inputs
        assert client.get(f"/api/try-on/{job['id']}/inputs/back").status_code==404

def test_two_garment_roles_are_explicit_and_unvalidated_combinations_are_rejected(tmp_path):
    from backend.app.main import create_app
    service=ComfyService();service.finished=True
    with TestClient(create_app(feature_settings(tmp_path),transport=httpx.MockTransport(service))) as client:
        accepted=client.post('/api/try-on',data={'category':'shirt','outer_category':'jacket'},files=uploads('person','garment','outer'))
        assert accepted.status_code==202
        job=wait_for(client,accepted.json()['id'],'complete')
        assert job['manifest']['mode']=='two_garment' and job['manifest']['image_order']==['person','garment','outer']
        assert '<image2>' in job['manifest']['prompt'] and '<image3>' in job['manifest']['prompt']
        denied=client.post('/api/try-on',data={'category':'hoodie','outer_category':'coat'},files=uploads('person','garment','outer'))
        assert denied.status_code==503 and denied.json()['error']['code']=='MODE_NOT_VALIDATED'

def test_extra_reference_does_not_bypass_feature_quality_or_duplicate_role_limits(tmp_path):
    from backend.app.main import create_app
    from .test_api import offline
    with TestClient(create_app(quality_settings(tmp_path),transport=httpx.MockTransport(offline))) as client:
        denied=client.post('/api/try-on',data={'category':'shirt'},files=uploads('person','garment','detail'))
        assert denied.status_code==503 and denied.json()['error']['code']=='MODE_NOT_VALIDATED'
        duplicate=client.post('/api/try-on',data={'category':'shirt'},files=uploads('person','garment','garment'))
        assert duplicate.status_code==422

def test_outfit_prompt_revision_requires_its_own_bound_gate(tmp_path):
    from backend.app.main import create_app
    settings=feature_settings(tmp_path)
    report=json.loads(settings.feature_manifest.read_text())
    report['modes']['two_garment']['outfit_implementation_sha256']='stale-prompt'
    settings.feature_manifest.write_text(json.dumps(report))
    service=ComfyService()
    with TestClient(create_app(settings,transport=httpx.MockTransport(service))) as client:
        denied=client.post('/api/try-on',data={'category':'shirt','outer_category':'jacket'},files=uploads('person','garment','outer'))
        assert denied.status_code==503 and denied.json()['error']['code']=='MODE_NOT_VALIDATED'
        assert not service.submissions


def coat_feature_settings(tmp_path):
    from backend.app.settings import ROOT
    settings=feature_settings(tmp_path)
    report=json.loads(settings.feature_manifest.read_text())
    row=report['modes']['two_garment']
    row.update(experiment='two_garment_v3',reviewed=8,combinations=['shirt+coat'],counts={'shirt+coat':{'expected':8,'passed':7}},
               coat_refinement_sha256=hashlib.sha256((ROOT/'backend/app/coat_outfits.py').read_bytes()).hexdigest())
    settings.feature_manifest.write_text(json.dumps(report))
    return settings


def test_full_coat_only_gate_uses_bound_prompt_and_rejects_other_pairs(tmp_path):
    from backend.app.main import create_app
    from backend.app.settings import ROOT
    service=ComfyService();service.finished=True
    with TestClient(create_app(coat_feature_settings(tmp_path),transport=httpx.MockTransport(service))) as client:
        accepted=client.post('/api/try-on',data={'category':'shirt','outer_category':'coat'},files=uploads('person','garment','outer'))
        assert accepted.status_code==202
        job=wait_for(client,accepted.json()['id'],'complete')
        assert job['manifest']['coat_refinement_sha256']==hashlib.sha256((ROOT/'backend/app/coat_outfits.py').read_bytes()).hexdigest()
        assert 'TUCKED INTO the EXISTING lower-body garment' in job['manifest']['prompt']
        denied=client.post('/api/try-on',data={'category':'shirt','outer_category':'jacket'},files=uploads('person','garment','outer'))
        assert denied.status_code==503 and len(service.submissions)==1


@pytest.mark.parametrize('change',['stale_refinement','incomplete','too_many_failures','changed_denominator','unqualified_pair'])
def test_coat_only_gate_cannot_bypass_revision_or_full_pair_threshold(tmp_path,change):
    from backend.app.main import create_app
    settings=coat_feature_settings(tmp_path)
    report=json.loads(settings.feature_manifest.read_text());row=report['modes']['two_garment']
    if change=='stale_refinement':row['coat_refinement_sha256']='stale'
    elif change=='incomplete':row['reviewed']=7
    elif change=='too_many_failures':row['counts']['shirt+coat']['passed']=6
    elif change=='changed_denominator':row['counts']['shirt+coat']['expected']=7
    else:row['combinations'].append('shirt+jacket')
    settings.feature_manifest.write_text(json.dumps(report));service=ComfyService()
    with TestClient(create_app(settings,transport=httpx.MockTransport(service))) as client:
        denied=client.post('/api/try-on',data={'category':'shirt','outer_category':'coat'},files=uploads('person','garment','outer'))
        assert denied.status_code==503 and not service.submissions


def bag_coat_feature_settings(tmp_path):
    from backend.app.settings import ROOT
    settings=coat_feature_settings(tmp_path)
    report=json.loads(settings.feature_manifest.read_text())
    report['modes']['two_garment'].update(experiment='two_garment_v4',
        bag_refinement_sha256=hashlib.sha256((ROOT/'backend/app/bag_coat_outfits.py').read_bytes()).hexdigest())
    settings.feature_manifest.write_text(json.dumps(report));return settings


def test_bag_refinement_is_a_separately_bound_coat_only_prompt(tmp_path):
    from backend.app.main import create_app
    service=ComfyService();service.finished=True
    with TestClient(create_app(bag_coat_feature_settings(tmp_path),transport=httpx.MockTransport(service))) as client:
        accepted=client.post('/api/try-on',data={'category':'shirt','outer_category':'coat'},files=uploads('person','garment','outer'))
        assert accepted.status_code==202
        job=wait_for(client,accepted.json()['id'],'complete')
        assert 'Preserve existing backpacks, bags and their shoulder straps exactly OVER the new coat.' in job['manifest']['prompt']
        assert job['manifest']['bag_refinement_sha256'] and job['manifest']['coat_refinement_sha256']


@pytest.mark.parametrize('binding',['bag_refinement_sha256','coat_refinement_sha256'])
def test_bag_refinement_cannot_bypass_either_prompt_binding(tmp_path,binding):
    from backend.app.main import create_app
    settings=bag_coat_feature_settings(tmp_path);report=json.loads(settings.feature_manifest.read_text())
    report['modes']['two_garment'][binding]='stale';settings.feature_manifest.write_text(json.dumps(report))
    service=ComfyService()
    with TestClient(create_app(settings,transport=httpx.MockTransport(service))) as client:
        denied=client.post('/api/try-on',data={'category':'shirt','outer_category':'coat'},files=uploads('person','garment','outer'))
        assert denied.status_code==503 and not service.submissions


def conditional_coat_feature_settings(tmp_path):
    from backend.app.settings import ROOT
    settings=bag_coat_feature_settings(tmp_path);report=json.loads(settings.feature_manifest.read_text())
    report['modes']['two_garment'].update(experiment='two_garment_v5',validated_source_bag_options=[False,True],
        conditional_refinement_sha256=hashlib.sha256((ROOT/'backend/app/conditional_coat_outfits.py').read_bytes()).hexdigest())
    settings.feature_manifest.write_text(json.dumps(report));return settings


@pytest.mark.parametrize('has_bag',[False,True])
def test_source_bag_choice_changes_only_qualified_outfit_prompt_and_survives_restart(tmp_path,has_bag):
    from backend.app.main import create_app
    service=ComfyService();service.finished=True;settings=conditional_coat_feature_settings(tmp_path)
    with TestClient(create_app(settings,transport=httpx.MockTransport(service))) as client:
        accepted=client.post('/api/try-on',data={'category':'shirt','outer_category':'coat','source_has_bag':str(has_bag).lower()},files=uploads('person','garment','outer'))
        assert accepted.status_code==202
        job=wait_for(client,accepted.json()['id'],'complete')
        assert job['manifest']['source_has_bag'] is has_bag
        assert ('Preserve existing backpacks' in job['manifest']['prompt']) is has_bag
        assert 'Match the inner shirt front closures' in job['manifest']['prompt']
        assert job['manifest']['conditional_refinement_sha256']
    with TestClient(create_app(settings,transport=httpx.MockTransport(service))) as client:
        assert client.get('/api/try-on/'+job['id']).json()['manifest']['source_has_bag'] is has_bag


@pytest.mark.parametrize('change',['stale_conditional','missing_options','only_bag','integer_options','six_passes'])
def test_conditional_outfit_cannot_bypass_its_full_quality_gate(tmp_path,change):
    from backend.app.main import create_app
    settings=conditional_coat_feature_settings(tmp_path);report=json.loads(settings.feature_manifest.read_text());row=report['modes']['two_garment']
    if change=='stale_conditional':row['conditional_refinement_sha256']='stale'
    elif change=='missing_options':row.pop('validated_source_bag_options')
    elif change=='only_bag':row['validated_source_bag_options']=[True]
    elif change=='integer_options':row['validated_source_bag_options']=[0,1]
    else:row['counts']['shirt+coat']['passed']=6
    settings.feature_manifest.write_text(json.dumps(report));service=ComfyService()
    with TestClient(create_app(settings,transport=httpx.MockTransport(service))) as client:
        denied=client.post('/api/try-on',data={'category':'shirt','outer_category':'coat','source_has_bag':'true'},files=uploads('person','garment','outer'))
        assert denied.status_code==503 and not service.submissions


def test_source_bag_option_cannot_change_single_reference_or_old_outfit_modes(tmp_path):
    from backend.app.main import create_app
    service=ComfyService()
    with TestClient(create_app(bag_coat_feature_settings(tmp_path),transport=httpx.MockTransport(service))) as client:
        for data,roles in [({'category':'shirt'},('person','garment')),({'category':'shirt','outer_category':'coat'},('person','garment','outer'))]:
            denied=client.post('/api/try-on',data={**data,'source_has_bag':'true'},files=uploads(*roles))
            assert denied.status_code==422 and not service.submissions


def test_bag_choice_is_part_of_idempotency_while_same_choice_never_resubmits(tmp_path):
    from backend.app.main import create_app
    service=ComfyService();service.finished=True
    with TestClient(create_app(conditional_coat_feature_settings(tmp_path),transport=httpx.MockTransport(service))) as client:
        data={'category':'shirt','outer_category':'coat','seed':'42','source_has_bag':'true'}
        headers={'Idempotency-Key':'same-outfit-request'}
        first=client.post('/api/try-on',data=data,headers=headers,files=uploads('person','garment','outer'))
        assert first.status_code==202
        wait_for(client,first.json()['id'],'complete')
        same=client.post('/api/try-on',data=data,headers=headers,files=uploads('person','garment','outer'))
        assert same.status_code==202 and same.json()['id']==first.json()['id']
        changed=client.post('/api/try-on',data={**data,'source_has_bag':'false'},headers=headers,files=uploads('person','garment','outer'))
        assert changed.status_code==409 and changed.json()['error']['code']=='IDEMPOTENCY_CONFLICT'
        assert len(service.submissions)==1
