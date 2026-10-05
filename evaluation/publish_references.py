"""Publish fixed reference/outfit studies after graph, image and visual-review checks."""
import argparse,hashlib,json,statistics,sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app.references import References,multi_prompt,outfit_prompt
from backend.app.outfits import refined_outfit_prompt
from backend.app.coat_outfits import coat_outfit_prompt
from backend.app.bag_coat_outfits import bag_coat_prompt
from evidence import without_runtime_fields,verify_png_graph
from phase1 import FLOORS

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def metric(values):
    values=[v for v in values if v is not None]
    return dict(count=len(values),minimum=min(values) if values else None,median=statistics.median(values) if values else None,maximum=max(values) if values else None)
def reference_decision(rows,capacity):
    changes={};preservation=True;usable=True;roles={}
    for row in rows:
        base=row['matched_review']['scores'];scores=row['scores'];category=row['category']
        changes[category]=changes.get(category,0)+scores['detailed_fidelity']-base['detailed_fidelity']
        preservation &= all(scores[k]>=base[k] for k in ('identity','body_pose','background_lighting'))
        usable &= scores['garment_transfer']>=2 and scores['artifacts']>=1
        roles.setdefault(category,set()).update(role for role in row.get('image_order',[]) if role in ('back','side','detail'))
    capacity_ok=len(capacity)==2 and all(r['status']=='complete' and len(r['image_order'])==5 for r in capacity)
    categories=sorted(c for c,v in changes.items() if v>0) if preservation and usable and capacity_ok else []
    return dict(status='passed' if len(rows)==8 and categories else 'rejected',reviewed=len(rows),
        preservation_noninferior=preservation,fidelity_improved=sum(changes.values())>0,
        detailed_fidelity_change=changes,categories=categories,reference_roles={c:sorted(roles[c],key=('back','side','detail').index) for c in categories},
        verified_total_inputs=5 if capacity_ok else None,capacity_outputs=len(capacity),capacity_succeeded=capacity_ok)
def outfit_decision(rows,expected=16):
    if expected not in (8,16):raise ValueError('Outfit matrix must declare eight or sixteen outputs')
    floors=dict(identity=2,body_pose=2,inner_transfer=2,outer_transfer=2,background_lighting=1,artifacts=1,layering_occlusion=1)
    counts={}
    for row in rows:
        pair=row['category']+'+'+row['outer_category'];count=counts.setdefault(pair,dict(expected=0,passed=0));count['expected']+=1
        count['passed']+=int(row['status']=='complete' and all(row['scores'][k]>=v for k,v in floors.items()))
    combinations=sorted(c for c,v in counts.items() if v['expected']==8 and v['passed']>=7)
    matrix_complete=len(rows)==expected and (expected==16 or set(counts)=={'shirt+coat'})
    return dict(status='passed' if matrix_complete and combinations else 'rejected',reviewed=len(rows),counts=counts,
        combinations=combinations,all_combinations_passed=bool(combinations),preservation_noninferior=bool(combinations),verified_total_inputs=3)
def checked_path(root,value):
    path=root/value
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or not path.is_file():raise ValueError('Evidence path must be an existing private regular file')
    return path
def checked_scores(scores,fields):
    if not isinstance(scores,dict) or set(scores)!=set(fields) or any(type(v)is not int or not 0<=v<=fields[k] for k,v in scores.items()):raise ValueError('Complete independent integer scores required')
def validate_worker_interruption(directory,record,graph):
    """A verified worker exit is a failure, never a fabricated native completion."""
    path=directory/'interruption.json'
    if record.get('interruption_sha256')!=sha(path):raise ValueError('Worker interruption evidence changed')
    audit=json.loads(path.read_text());queue=audit.get('queue_before',{})
    active=queue.get('queue_running',[])
    if (record.get('status')!='failed' or record.get('error',{}).get('code')!='owned_worker_restart'
            or audit.get('kind')!='verified_owned_worker_restart' or not audit.get('reason')
            or audit.get('prompt_id')!=record['prompt_id'] or audit.get('client_id')!=record['client_id']
            or len(active)!=1 or queue.get('queue_pending') or active[0][1]!=record['prompt_id']
            or active[0][3].get('client_id')!=record['client_id']
            or without_runtime_fields(active[0][2])!=without_runtime_fields(graph)
            or audit.get('worker_process_exit_verified') is not True
            or audit.get('queue_after')!={'queue_running':[],'queue_pending':[]}
            or record['prompt_id'] in audit.get('history_before',{})
            or record['prompt_id'] in audit.get('history_after',{})
            or not isinstance(audit.get('verified_after'),(int,float))
            or audit['verified_after']<audit.get('captured_at',float('inf'))
            or record.get('execution_seconds') is not None or record.get('wall_seconds') is not None
            or record.get('vram_sampling_available') is not False
            or record.get('sampled_device_peak_mib')!=0 or record.get('output')):
        raise ValueError('Worker failure must retain sole owned submission and verified exit, without invented output or timing')
def validate_study(root,protocol_path):
    protocol=json.loads(protocol_path.read_text());config=json.loads((root/'backend/workflow.json').read_text())
    template=checked_path(root,config['graph']);implementation=root/'backend/app/references.py'
    if sha(template)!=protocol['graph_sha256'] or sha(implementation)!=protocol['implementation_sha256']:raise ValueError('Declared graph or implementation changed')
    if protocol.get('outfit_implementation_sha256') and sha(root/'backend/app/outfits.py')!=protocol['outfit_implementation_sha256']:raise ValueError('Declared outfit implementation changed')
    if protocol.get('coat_refinement_sha256') and sha(root/'backend/app/coat_outfits.py')!=protocol['coat_refinement_sha256']:raise ValueError('Declared coat refinement changed')
    if protocol.get('bag_refinement_sha256') and sha(root/'backend/app/bag_coat_outfits.py')!=protocol['bag_refinement_sha256']:raise ValueError('Declared bag refinement changed')
    if protocol.get('conditional_refinement_sha256') and sha(root/'backend/app/conditional_coat_outfits.py')!=protocol['conditional_refinement_sha256']:raise ValueError('Declared conditional refinement changed')
    if protocol['status']!='defined_before_execution':raise ValueError('Study must be declared before execution')
    baseline=json.loads((root/f"evaluation/reviewed_results_{protocol['baseline_experiment']}.json").read_text())
    baseline={(r['case_id'],r['seed']):r for r in baseline};records=[]
    for sample in protocol['samples']:
        for seed in protocol['seeds']:
            directory=root/'evaluation/benchmarks'/protocol['experiment']/sample['id']/str(seed)
            record=json.loads((directory/'record.json').read_text())
            if record['sample_id']!=sample['id'] or record['seed']!=seed or record['experiment']!=protocol['experiment'] or record['protocol_sha256']!=sha(protocol_path):raise ValueError('Study identity or protocol drift')
            if record['inputs']!=sample['images'] or record['image_order']!=list(sample['images']) or list(record['uploaded'])!=list(sample['images']):raise ValueError('Reference order differs from declared roles')
            for role,value in sample['images'].items():
                source=checked_path(root,value['path']);uploaded=checked_path(root/'.local/input',record['uploaded'][role])
                if sha(source)!=value['sha256'] or sha(uploaded)!=value['sha256']:raise ValueError('Source/uploaded bytes differ')
            graph_path=directory/'graph.api.json';graph=json.loads(graph_path.read_text())
            if sha(graph_path)!=record['graph_sha256']:raise ValueError('Submitted graph changed')
            expected=References.graph(json.loads(template.read_text()),config,record['uploaded'])
            outfit_function=bag_coat_prompt if protocol.get('bag_refinement_sha256') else coat_outfit_prompt if protocol.get('coat_refinement_sha256') else refined_outfit_prompt if protocol.get('outfit_implementation_sha256') else outfit_prompt
            prompt=sample['prompt'] if sample['mode']=='capacity' else outfit_function(sample['category'],sample['outer_category']) if sample['mode']=='two_garment' else multi_prompt((root/sample['base_prompt']).read_text().format(garment_type=sample['category']),[role for role in sample['images'] if role not in ('person','garment')])
            if protocol.get('conditional_refinement_sha256'):
                from backend.app.conditional_coat_outfits import conditional_coat_prompt
                if type(sample.get('source_has_bag')) is not bool or record.get('source_has_bag') is not sample['source_has_bag']:raise ValueError('Source bag option differs from declared photo')
                prompt=conditional_coat_prompt(sample['category'],sample['outer_category'],sample['source_has_bag'])
            if sample['mode']=='multi_reference' and (root/sample['base_prompt']).read_text().format(garment_type=sample['category'])!=baseline[sample['baseline_case'],seed]['prompt']:raise ValueError('Matched study changed its baseline prompt')
            expected[config['prompt_node']]['inputs']['prompt']=prompt;expected[config['sampler_node']]['inputs']['seed']=seed;expected[config['output_node']]['inputs']['filename_prefix']=record['client_id']
            if record['prompt']!=prompt or without_runtime_fields(graph)!=without_runtime_fields(expected):raise ValueError('Graph differs beyond declared job inputs')
            interrupted=record.get('error',{}).get('code')=='owned_worker_restart' if isinstance(record.get('error'),dict) else False
            if interrupted:
                validate_worker_interruption(directory,record,graph)
                history=None
            else:
                history=json.loads((directory/'history.json').read_text())
                if history['prompt'][1]!=record['prompt_id'] or history['prompt'][3].get('client_id')!=record['client_id'] or without_runtime_fields(history['prompt'][2])!=without_runtime_fields(graph) or not history['status']['completed']:raise ValueError('Native history mismatch')
            if record['status']=='complete':
                if history['status']['status_str']!='success':raise ValueError('Successful output has failed history')
                output=checked_path(root,record['output'])
                if sha(output)!=record['output_sha256'] or verify_png_graph(output,graph)!=record['output_size']:raise ValueError('Retained output evidence changed')
                image_rows=history['outputs'][config['output_node']]['images']
                if len(image_rows)!=1 or not image_rows[0]['filename'].startswith(record['client_id']):raise ValueError('History output is not owned by this study submission')
                descriptor=image_rows[0]
                if descriptor.get('type')!='output' or Path(descriptor['filename']).name!=descriptor['filename']:raise ValueError('Output descriptor is not a private output image')
                native=checked_path(root/'.local/output',str(Path(descriptor.get('subfolder',''))/descriptor['filename']))
                if sha(native)!=record['output_sha256']:raise ValueError('Native output differs from retained PNG')
                fields={k:2 for k in (('identity','body_pose','inner_transfer','outer_transfer','background_lighting','artifacts','layering_occlusion') if sample['mode']=='two_garment' else FLOORS)}
                if sample['mode']=='multi_reference':fields['detailed_fidelity']=4
                checked_scores(record['scores'],fields)
                if not record.get('reviewer') or not record.get('notes'):raise ValueError('Independent visual review and observations required')
            elif record['status']=='failed':
                if not record.get('error') or (not interrupted and history['status']['status_str']=='success'):raise ValueError('Failure has no native error evidence')
                # Failures remain in the denominator and cannot receive invented visual scores.
                record['scores']={k:0 for k in ('identity','body_pose','inner_transfer','outer_transfer','background_lighting','artifacts','layering_occlusion','garment_transfer','detailed_fidelity')}
            else:raise ValueError('Nonterminal submission cannot be published')
            if sample['mode']=='multi_reference':
                raw=baseline[sample['baseline_case'],seed];review=record.get('matched_review')
                if sha(checked_path(root,raw['output']))!=raw['output_sha256'] or not review or review.get('output_sha256')!=raw['output_sha256'] or not review.get('notes'):raise ValueError('Matched raw review or output missing')
                checked_scores(review['scores'],{**{k:2 for k in FLOORS},'detailed_fidelity':4})
                if {k:v for k,v in review['scores'].items() if k in FLOORS}!=raw['scores']:raise ValueError('Matched review changed published baseline scores')
            record.update(category=sample.get('category'),outer_category=sample.get('outer_category'),mode=sample['mode'])
            records.append(record)
    return protocol,records
def linked_capacity(root,protocol):
    link=protocol.get('capacity_study')
    if not link:return []
    experiment=link.get('experiment')
    if experiment not in ('multiple_reference_v1','multiple_reference_v2') or experiment==protocol['experiment']:
        raise ValueError('Capacity must identify a separate declared reference study')
    path=checked_path(root,f'evaluation/{experiment}_protocol.json')
    if sha(path)!=link.get('protocol_sha256'):raise ValueError('Linked capacity protocol changed')
    linked=json.loads(path.read_text())
    if any(linked.get(k)!=protocol.get(k) for k in ('graph_sha256','implementation_sha256')):
        raise ValueError('Capacity must use the same graph and reference implementation')
    _,rows=validate_study(root,path)
    capacity=[r for r in rows if r['mode']=='capacity' and r['sample_id']==link.get('sample_id')]
    if len(capacity)!=2:raise ValueError('Both declared capacity seeds must be retained')
    return capacity

def publish(root=ROOT,reference_experiment='multiple_reference_v1',outfit_experiment='two_garment_v1'):
    if reference_experiment not in ('multiple_reference_v1','multiple_reference_v2'):raise ValueError('Unknown reference experiment')
    if outfit_experiment not in ('two_garment_v1','two_garment_v2','two_garment_v3','two_garment_v4','two_garment_v5'):raise ValueError('Unknown outfit experiment')
    quality_path=root/'evaluation/summary_category_reference_v4.json';quality=json.loads(quality_path.read_text())
    if quality.get('quality_gate_passed') is not True:raise ValueError('Passing complete baseline required before feature publication')
    results={};report_rows=[];history={}
    experiments=[('multiple_reference_v1','multi_reference')]
    if reference_experiment!='multiple_reference_v1':experiments.append((reference_experiment,'multi_reference'))
    experiments.append(('two_garment_v1','two_garment'))
    if outfit_experiment!='two_garment_v1':experiments.append(('two_garment_v2','two_garment'))
    if outfit_experiment in ('two_garment_v3','two_garment_v4','two_garment_v5'):experiments.append(('two_garment_v3','two_garment'))
    if outfit_experiment in ('two_garment_v4','two_garment_v5'):experiments.append(('two_garment_v4','two_garment'))
    if outfit_experiment=='two_garment_v5':experiments.append((outfit_experiment,'two_garment'))
    for experiment,name in experiments:
        protocol,rows=validate_study(root,root/f'evaluation/{experiment}_protocol.json')
        capacity=[r for r in rows if r['mode']=='capacity']
        if protocol.get('capacity_study'):capacity=linked_capacity(root,protocol)
        if name=='multi_reference':result=reference_decision([r for r in rows if r['mode']!='capacity'],capacity)
        else:result=outfit_decision(rows,expected=protocol['expected'])
        result.update(experiment=experiment,protocol_sha256=sha(root/f'evaluation/{experiment}_protocol.json'),execution_seconds=metric([r.get('execution_seconds') for r in rows]),sampled_device_peak_mib=max(r.get('sampled_device_peak_mib',0) for r in rows))
        if any(r.get('vram_sampling_available') is False for r in rows):
            result['vram_sampling_unavailable_outputs']=sum(r.get('vram_sampling_available') is False for r in rows)
            result['measurement_note']='Reported device peak is from available sampled records. Recovered successes retain exact native execution time; verified worker interruptions remain failures with no invented output or timing. These records lack complete VRAM or wall-time measurements. No resubmission.'
        if protocol.get('outfit_implementation_sha256'):result['outfit_implementation_sha256']=protocol['outfit_implementation_sha256']
        if protocol.get('coat_refinement_sha256'):result['coat_refinement_sha256']=protocol['coat_refinement_sha256']
        if protocol.get('bag_refinement_sha256'):result['bag_refinement_sha256']=protocol['bag_refinement_sha256']
        if protocol.get('conditional_refinement_sha256'):
            result['conditional_refinement_sha256']=protocol['conditional_refinement_sha256']
            result['validated_source_bag_options']=sorted({r['source_has_bag'] for r in rows})
        if protocol.get('capacity_study'):
            result.update(capacity_study=protocol['capacity_study'],capacity_execution_seconds=metric([r.get('execution_seconds') for r in capacity]),capacity_sampled_device_peak_mib=max(r.get('sampled_device_peak_mib',0) for r in capacity))
        history[experiment]=result
        if (name=='multi_reference' and experiment==reference_experiment) or (name=='two_garment' and experiment==outfit_experiment):results[name]=result
        (root/f'evaluation/reference_quality_{experiment}.json').write_text(json.dumps(result,indent=2)+'\n')
        (root/f'evaluation/reviewed_results_{experiment}.json').write_text(json.dumps(rows,indent=2)+'\n')
        report_rows.extend(f"| {experiment} | {r['sample_id']} | {r['seed']} | {r['status']} | {json.dumps(r['scores'])} | {r.get('notes') or 'Native execution failure retained'} |" for r in rows)
    report=dict(baseline_quality_sha256=sha(quality_path),implementation_sha256=sha(root/'backend/app/references.py'),modes=results)
    (root/'evaluation/feature_quality.json').write_text(json.dumps(report,indent=2)+'\n')
    (root/'docs/REFERENCE_STUDIES.md').write_text('# Ordered references and two garments\n\nAll declared outputs, failures and fixed seeds are retained. Source/upload and exact graph checks passed before this report. Completed outputs additionally pass native history and embedded PNG checks. A verified owned worker restart remains a failed case with its queue/ownership/exit audit; it is never represented as native success or a visual result. One AI visual reviewer; small licensed matrix coverage is not a production accuracy estimate. Five-input capacity is separate from genuine view quality; the capacity-only side slot repeats the front and does not validate side-view fidelity. Only documented passing categories/roles and combinations are offered. The narrowed hoodie study contains eight fresh quality outputs. Its separately linked capacity protocol is hash-bound and fully revalidated against the same graph and implementation; no earlier quality row substitutes for a fresh output. Rejected study decisions remain visible below.\n\nAll decisions and measured local runtime:\n\n```json\n'+json.dumps(history,indent=2)+'\n```\n\nActive feature selection:\n\n```json\n'+json.dumps(results,indent=2)+'\n```\n\n| Study | Sample | Seed | State | Independent scores | Observation |\n|---|---|---|---|---|---|\n'+'\n'.join(report_rows)+'\n')
    print(json.dumps(results,indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-experiment',choices=('multiple_reference_v1','multiple_reference_v2'),default='multiple_reference_v1')
    parser.add_argument('--outfit-experiment',choices=('two_garment_v1','two_garment_v2','two_garment_v3','two_garment_v4','two_garment_v5'),default='two_garment_v1')
    args=parser.parse_args();publish(reference_experiment=args.reference_experiment,outfit_experiment=args.outfit_experiment)
