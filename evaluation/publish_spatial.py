"""Validate and report a complete matched constraint study without replacing raw scores."""
import argparse,hashlib,json,statistics
from pathlib import Path
import numpy as np
from PIL import Image
from semantic_constraints import semantic_mask
from boundary_guard import safe_mask
from protected_regions import constrain
from phase1 import FLOORS
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def metric(values):
    values=[v for v in values if v is not None]
    return dict(count=len(values),minimum=min(values) if values else None,median=statistics.median(values) if values else None,maximum=max(values) if values else None)
def spatial_decision(summary):
    noninferior=all(summary['matched_score_changes'][k]['regressed']==0 for k in FLOORS)
    return ('passed' if noninferior and summary['passing']>=32 and min(summary['categories'].values())>=8
            and summary.get('raw_protected_pixels_changed',0)>0 and summary.get('protected_pixels_changed',1)==0 else 'rejected')
def publish(experiment,source_experiment='reference_v2'):
    if not experiment or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in experiment):raise ValueError('Invalid experiment')
    cases=json.loads((ROOT/'evaluation/cases/phase1.json').read_text())
    if not source_experiment or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in source_experiment):raise ValueError('Invalid baseline experiment')
    raw=json.loads((ROOT/f'evaluation/reviewed_results_{source_experiment}.json').read_text())
    raw_summary=ROOT/f'evaluation/summary_{source_experiment}.json'
    protocol_path=ROOT/f'evaluation/{experiment}_protocol.json'
    protocol=json.loads(protocol_path.read_text()) if protocol_path.exists() else None
    if protocol and (protocol['baseline_experiment']!=source_experiment or protocol['implementation_sha256']!=sha(ROOT/'evaluation/semantic_constraints.py') or protocol['parser_manifest_sha256']!=sha(ROOT/'evaluation/segmentation_environment.json')):raise ValueError('Declared protection study changed')
    if protocol and protocol.get('guard_sha256') and (protocol['guard_sha256']!=sha(ROOT/'evaluation/boundary_guard.py') or protocol['cached_source_protocol_sha256']!=sha(ROOT/f"evaluation/{protocol['cached_source_experiment']}_protocol.json")):raise ValueError('Declared boundary fallback changed')
    original={(r['case_id'],r['seed']):r for r in raw}
    records=[]; categories={c:0 for c in ('shirt','hoodie','jacket','coat')}; differences={k:[] for k in FLOORS};raw_protected=0;final_protected=0
    for case in cases['cases']:
        directory=ROOT/'evaluation/benchmarks'/experiment/case['id']
        rows=json.loads((directory/'records.json').read_text())
        if sorted(r['seed'] for r in rows)!=sorted(cases['seeds']):raise ValueError('Missing or duplicate seed')
        for r in rows:
            if protocol and (r.get('protocol_sha256')!=sha(protocol_path) or r['mask_policy']!=protocol['mask_policy'] or not r.get('cached_label_hashes')):raise ValueError('Incomplete declared mask evidence')
            baseline=original[case['id'],r['seed']]
            source_path=ROOT/'evaluation'/case['person_image']; raw_path=ROOT/r['original_output']
            if r['source_sha256']!=sha(source_path) or r['original_output_sha256']!=sha(raw_path) or r['original_output_sha256']!=baseline['output_sha256']:raise ValueError('Changed source or raw output')
            mask_path=directory/f"{r['seed']}.mask.png"; output_path=ROOT/r['output']
            if r['output_sha256']!=sha(output_path) or r['mask_sha256']!=sha(mask_path):raise ValueError('Changed spatial evidence')
            paths=r.get('cached_label_paths') or {name:str((directory/f"{r['seed']}.{name}-labels.png").relative_to(ROOT)) for name in ('source','generated')}
            if r.get('cached_label_hashes') and any(sha(ROOT/paths[name])!=r['cached_label_hashes'][name] for name in paths):raise ValueError('Changed cached parser evidence')
            source_labels=np.asarray(Image.open(ROOT/paths['source'])); generated_labels=np.asarray(Image.open(ROOT/paths['generated']))
            generated=Image.open(raw_path).convert('RGB');source=Image.open(source_path).convert('RGB').resize(generated.size,Image.Resampling.LANCZOS)
            fallback=None
            try:expected_mask=semantic_mask(source_labels,generated_labels,policy=r.get('mask_policy','legacy'),category=case['category'])
            except ValueError as error:fallback=str(error);expected_mask=Image.new('L',generated.size,255)
            if fallback is None and protocol and protocol.get('guard_sha256'):
                expected_mask,fallback,metrics=safe_mask(source,generated,expected_mask,source_labels)
                if metrics!=r.get('boundary_guard'):raise ValueError('Boundary metrics cannot be reconstructed')
            if fallback!=r['fallback_reason'] or (fallback is None)!=r['constraint_applied']:raise ValueError('Incorrect fallback evidence')
            if not np.array_equal(np.asarray(expected_mask),np.asarray(Image.open(mask_path))):raise ValueError('Mask cannot be reproduced')
            expected=constrain(source,generated,expected_mask) if fallback is None else generated
            if not np.array_equal(np.asarray(expected),np.asarray(Image.open(output_path).convert('RGB'))):raise ValueError('Output cannot be reproduced')
            protected=np.asarray(expected_mask)==0
            raw_count=int(np.count_nonzero(np.any(np.asarray(source)!=np.asarray(generated),axis=2)&protected))
            final_count=int(np.count_nonzero(np.any(np.asarray(source)!=np.asarray(expected),axis=2)&protected))
            if r.get('raw_protected_pixels_changed',raw_count)!=raw_count or r.get('protected_pixels_changed',final_count)!=final_count:raise ValueError('Protection pixel metric cannot be reproduced')
            raw_protected+=raw_count;final_protected+=final_count
            scores=r['scores']
            if not isinstance(scores,dict) or set(scores)!=set(FLOORS) or any(type(v)is not int or v not in (0,1,2) for v in scores.values()) or not r['reviewer'] or not r['notes']:raise ValueError('Complete visual review required')
            passed=all(scores[k]>=floor for k,floor in FLOORS.items());categories[case['category']]+=int(passed)
            for k in FLOORS:differences[k].append(scores[k]-baseline['scores'][k])
            records.append(r)
    summary=dict(experiment=experiment,expected=40,reviewed=len(records),passing=sum(categories.values()),categories=categories,
        source_experiment=source_experiment,raw_passing=sum(all(r['scores'][k]>=v for k,v in FLOORS.items()) for r in raw),fallback_outputs=sum(not r['constraint_applied'] for r in records),
        raw_protected_pixels_changed=raw_protected,protected_pixels_changed=final_protected,
        exact_source_pixel_protection_verified=True,decision='rejected',
        matched_score_changes={k:dict(improved=sum(v>0 for v in values),unchanged=sum(v==0 for v in values),regressed=sum(v<0 for v in values),total=sum(values)) for k,values in differences.items()},
        cpu_parser_and_compositing_seconds=metric([r['constraint_wall_seconds'] for r in records]),
        revised_compositing_seconds=metric([r.get('revised_compositing_seconds') for r in records]),
        cold_parser_load_seconds=metric([r['cold_model_load_seconds'] for r in records]),
        cpu_process_peak_mib=max(r['cpu_process_peak_mib'] for r in records),
        parser_manifest_sha256=sha(ROOT/'evaluation/segmentation_environment.json'),
        model_revision=records[0]['model_revision'],gpu_regeneration_required=False,
        baseline_quality_sha256=sha(raw_summary),implementation_sha256=sha(ROOT/'evaluation/semantic_constraints.py'),
        protocol_sha256=sha(protocol_path) if protocol else None)
    if protocol and protocol.get('guard_sha256'):summary['guard_sha256']=protocol['guard_sha256']
    parity_path=ROOT/'.local/protection-runtime-parity.json'
    if experiment=='semantic_guarded_v5' and parity_path.exists():
        parity=json.loads(parity_path.read_text());keys={(r['case_id'],r['seed']) for r in records};observed={(r['case_id'],r['seed']) for r in parity['records']}
        expected_hashes={(r['case_id'],r['seed']):r['output_sha256'] for r in records}
        if (parity['exact_outputs']!=40 or len(parity['records'])!=40 or keys!=observed or parity['helper_outputs']!=4 or parity['protocol_sha256']!=sha(protocol_path)
            or parity['engine_sha256']!=sha(ROOT/'evaluation/protection_engine.py') or parity['helper_sha256']!=sha(ROOT/'evaluation/apply_protection.py')
            or any(r['expected_sha256']!=expected_hashes[r['case_id'],r['seed']] or r['exact_pixels'] is not True or r['exact_mask'] is not True for r in parity['records'])):raise ValueError('Incomplete/changed application CPU runtime parity')
        summary['runtime_parity']={k:parity[k] for k in ('expected','exact_outputs','helper_outputs','engine_sha256','helper_sha256')}
    # Phase 5 requires fewer unintended edits and noninferior transfer/edges;
    # detailed garment-fidelity improvement is the separate Phase 4 requirement.
    summary['decision']=spatial_decision(summary)
    if summary['decision']=='passed' and not json.loads(raw_summary.read_text()).get('quality_gate_passed'):summary['decision']='baseline_not_validated'
    (ROOT/f'evaluation/summary_{experiment}.json').write_text(json.dumps(summary,indent=2)+'\n')
    rows='\n'.join(f"| {r['case_id']} | {r['seed']} | {' / '.join(str(r['scores'][k]) for k in FLOORS)} | {'Raw fallback' if not r['constraint_applied'] else 'Applied'} | {r['notes']} |" for r in records)
    report=f"# Matched spatial study: {experiment}\n\nDecision: **{summary['decision']}**. Reviewed all 40 fixed outputs, including {summary['fallback_outputs']} raw fallbacks. Passing previews: {summary['passing']}/40 versus raw 31/40. Category counts: {categories}.\n\nEvery source, raw output, mask and constrained output hash was checked. Masks and final pixels were reconstructed from retained parser labels; exact source pixels outside the editable mask were verified. This pixel guarantee does not establish garment fidelity or good boundaries.\n\nMatched score changes: `{json.dumps(summary['matched_score_changes'])}`. The visible original blouse remains incorrectly restored in several outputs. No spatial mode is enabled by this study.\n\nCPU parser plus original compositing: `{summary['cpu_parser_and_compositing_seconds']}` seconds. Revised cached compositing: `{summary['revised_compositing_seconds']}` seconds, where present. Cold model loading: `{summary['cold_parser_load_seconds']}` seconds, measured separately. CPU process peak: {summary['cpu_process_peak_mib']} MiB. Revised runs reuse parser labels; their compositing timing is not a new full parser measurement. Python import startup is excluded. Original GPU generation telemetry remains in the raw reference_v2 report; no GPU work was resubmitted.\n\nSingle AI visual reviewer; see ASSETS.md for source rights. Scores: identity / body-pose / garment / background / artifacts.\n\n| Case | Seed | Scores | Mode | Observation |\n|---|---|---|---|\n{rows}\n"
    report=report.replace('versus raw 31/40',f"versus raw {summary['raw_passing']}/40").replace('raw reference_v2 report',f'raw {source_experiment} report')
    report=report.replace('The visible original blouse remains incorrectly restored in several outputs. No spatial mode is enabled by this study.',f'Changed pixels in accepted protected regions: raw {raw_protected}; constrained {final_protected}. Visual reviews determine garment and boundary quality. Adoption additionally requires the exact passing baseline, parser and implementation manifests.')
    report += f"\nDeclared study: [protocol](../evaluation/{experiment}_protocol.json). Machine-readable evidence: [summary](../evaluation/summary_{experiment}.json).\n"
    if summary.get('runtime_parity'):
        report += f"\nApplication runtime parity: {summary['runtime_parity']['exact_outputs']}/40 actual CPU-engine outputs and masks matched the study; {summary['runtime_parity']['helper_outputs']} real helper-process checks cover all four categories. This is CPU postprocessing after native generation, with raw fallback for uncertain boundaries. It does not establish native latent/inpainting support.\n"
    (ROOT/f'docs/SPATIAL_{experiment}.md').write_text(report)
    print(json.dumps(summary,indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--experiment',required=True);parser.add_argument('--source-experiment',default='reference_v2');args=parser.parse_args();publish(args.experiment,args.source_experiment)
