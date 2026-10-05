"""Validate local execution evidence and publish the reviewed Phase 1 summary."""
import argparse
import hashlib
import html
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from phase1 import FLOORS, admission, summarize
from evidence import validate_record
from locked_protocol import verify_protocol

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / 'evaluation'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def timing_summary(values):
    return {'count': len(values), 'min': min(values) if values else None,
            'median': statistics.median(values) if values else None,
            'max': max(values) if values else None}


def write_report(summary, suffix):
    rows = [f"| {name} | {row['passed']}/{row['expected']} | {'Meets' if row['passed'] >= 8 else 'Below'} 8/10 |"
            for name, row in summary['categories'].items()]
    result = 'PASSED' if summary['quality_gate_passed'] else 'FAILED'
    measured = summary['execution_seconds']
    warm = summary['warm_execution_seconds']
    recovered = summary['recovered_outputs']
    report = f'''# Phase 1 evaluation{suffix}

Published {summary['published_at']}. Protocol: {'phase1_v1' if not suffix else summary['experiment']}.
Complete evaluation and passing the quality gate are separate outcomes.

## Quality decision

**{result}: {summary['passed']}/40 outputs pass.** The gate requires at least
32/40 overall and at least 8/10 in every category. Scores use the same fixed
rubric for identity, body/pose, garment transfer, background/lighting and artifacts.
Failed executions remain in the denominator: {summary['inference_failures']}.

| Category | Passing outputs | Category threshold |
|---|---|---|
{chr(10).join(rows)}

Categories meeting their individual threshold:
{', '.join(summary['categories_meeting_threshold']) or 'none'}.
Validated categories for this full workflow:
{', '.join(summary['validated_categories']) or 'none; the full gate has not passed'}.
Do not replace poor outputs, select different seeds, or merge experiment results
into the original benchmark. A changed workflow requires its own complete gate.

## Runtime on the evaluated GPU

RTX 5060, 8,151 MiB reported device VRAM; exact environment and pinned hashes
are in [environment.json](../evaluation/environment.json). Model: GGUF Q4_K_M;
25 steps, CFG 1, Euler/simple, denoise 1, aspect-preserving 1024 pixel budget.

| Measurement | Count | Minimum seconds | Median seconds | Maximum seconds |
|---|---|---|---|---|
| Completed outputs with timing | {measured['count']} | {measured['min']} | {measured['median']} | {measured['max']} |
| Matched warm second seeds | {warm['count']} | {warm['min']} | {warm['median']} | {warm['max']} |

Sampled total-device peak VRAM: {summary['sampled_device_peak_mib']} MiB.
Five-second sampling can miss short peaks and includes other desktop GPU usage.
Model-unloaded cold runs have warm operating-system file caches; they are not
machine cold boots. Exact cold-run records and delivered image dimensions are
in the [summary](../evaluation/summary{suffix}.json). Restarted second seeds are
excluded from the matched warm set.
Some runs overlapped local CPU segmentation and container-build verification; these timings describe
the observed machine envelope, rather than an exclusive-machine speed comparison.

Recovered outputs with missing original history/timing/VRAM: {len(recovered)}.
Recovery verifies the PNG's embedded exact graph, source/uploaded bytes and output
hash; missing telemetry is never reconstructed and is excluded from metrics.

## Evidence and limits

- [Scores and per-output observations](../evaluation/SCORES{suffix}.md).
- [Reviewed record manifest](../evaluation/reviewed_results{suffix}.json).
- [Protocol and score anchors](../evaluation/PROTOCOL.md).
- [Inputs, rights and coverage](../evaluation/ASSETS.md).
- Local comparison gallery: `.local/evaluation_gallery{suffix}.html`.

Only one AI reviewer compared source/reference/output images. This is an
engineering benchmark, not independent human approval, representative customer
accuracy, or physical sizing evidence. Five subjects and five reference garments
limit coverage; four subjects originate from upstream example imagery whose
synthetic status is unknown. Only visible garment details are graded.
Protected-region and multi-reference modes have no quality claim from this run.
The Qwen Image 2.1 model has separate research/evaluation terms; the application's
MIT license does not remove those restrictions.
'''
    (ROOT / f'docs/EVALUATION{suffix}.md').write_text(report, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment')
    parser.add_argument('--upper-body-prompt', type=Path)
    parser.add_argument('--outerwear-prompt', type=Path)
    parser.add_argument('--jacket-prompt', type=Path)
    args = parser.parse_args()
    if (args.upper_body_prompt or args.outerwear_prompt or args.jacket_prompt) and not args.experiment:
        parser.error('Changed prompts require a separate experiment.')
    if args.experiment and any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in args.experiment):
        parser.error('Use a simple lower-case experiment name.')
    storage = EVAL / ('benchmarks/' + args.experiment if args.experiment else 'results')
    prompt_paths = {'upper_body': args.upper_body_prompt, 'outerwear': args.outerwear_prompt}
    if args.jacket_prompt:prompt_paths['jacket']=args.jacket_prompt
    verify_protocol(ROOT, args.experiment,prompt_paths)
    suffix = '_' + args.experiment if args.experiment else ''
    manifest = json.loads((EVAL / 'cases/phase1.json').read_text())
    errors = admission(manifest, EVAL)
    if errors:
        raise RuntimeError('\n'.join(errors))
    records = []
    for case in manifest['cases']:
        candidates = list(storage.glob(case['id'] + '_gguf_*/records.json'))
        if len(candidates) != 1:
            raise RuntimeError('Expected exactly one canonical run: ' + case['id'])
        for record in json.loads(candidates[0].read_text()):
            validate_record(ROOT, candidates[0].parent, case, record, experiment=args.experiment, prompt_paths=prompt_paths)
            record['output'] = record.get('output', '').replace('\\', '/') if record.get('output') else None
            records.append(record)
    summary = summarize(manifest, records)
    if summary['status'] == 'incomplete':
        raise RuntimeError(json.dumps(summary, indent=2))
    completed = [r for r in records if r['status'] == 'complete']
    times = [r['execution_seconds'] for r in completed if r.get('execution_seconds') is not None]
    cold = [r for r in completed if r.get('cache_state', '').startswith('models_unloaded')]
    # Second seeds are matched warm runs with the same pair/prompt. First seeds
    # of new pairs also perform fresh encoding and can reload evicted models.
    warm = [r['execution_seconds'] for r in completed if r['run_ordinal'] == 2 and not r.get('cache_state', '').startswith('server_restart') and r.get('execution_seconds') is not None]
    categories_meeting_threshold = [name for name, row in summary['categories'].items() if row['passed'] >= 8]
    peak_samples = [r['sampled_device_peak_mib'] for r in completed if r.get('sampled_device_peak_mib') is not None]
    summary.update(
        published_at=datetime.now(timezone.utc).isoformat(),
        reviewer='Codex visual review (single AI reviewer)',
        categories_meeting_threshold=categories_meeting_threshold,
        validated_categories=categories_meeting_threshold if summary['quality_gate_passed'] else [],
        execution_seconds=timing_summary(times), warm_execution_seconds=timing_summary(warm),
        cold_model_residency_runs=[{k: r.get(k) for k in ('case_id', 'seed', 'cache_state', 'execution_seconds', 'wall_seconds')} for r in cold],
        sampled_device_peak_mib=max(peak_samples) if peak_samples else None,
        recovered_outputs=[{'case_id': r['case_id'], 'seed': r['seed'], 'evidence': r['recovery_evidence']} for r in completed if r.get('recovery_evidence')],
        output_sizes=sorted({tuple(r['output_size']) for r in completed}),
        failed_dimensions={name: sum(r['scores'][name] < floor for r in completed) for name, floor in FLOORS.items()},
        environment_sha256=sha(EVAL / 'environment.json'), cases_sha256=sha(EVAL / 'cases/phase1.json'))
    summary['workflow_template_sha256'] = sha(ROOT / 'workflows/qwen_tryon_upper_candidate_gguf.api.json')
    summary['experiment'] = args.experiment
    summary['prompt_hashes'] = {name: sha(path or EVAL / f'prompts/{name}.txt') for name, path in prompt_paths.items()}
    (EVAL / f'reviewed_results{suffix}.json').write_text(json.dumps(records, indent=2) + '\n')
    (EVAL / f'summary{suffix}.json').write_text(json.dumps(summary, indent=2) + '\n')
    rows = []
    gallery = ['<!doctype html><meta charset="utf-8"><title>ComfyFitter Phase 1</title><style>body{font:16px system-ui;margin:32px;max-width:1500px;background:#f5f5f5;color:#222}section{background:white;padding:20px;margin:24px 0}figure{margin:0}img{width:100%;height:480px;object-fit:contain}a{color:#164d8f}.images{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}pre{white-space:pre-wrap}@media(max-width:800px){.images{grid-template-columns:1fr}}</style><h1>Phase 1 garment evaluation</h1><p>Single AI reviewer; see evaluation/ASSETS.md for source attribution. Clothing in outputs was modified using generative AI; no endorsement implied.</p><p>Photo source for cases ending in 05: <a href="https://www.flickr.com/photos/161894595@N03/51610395715/">Reba Spike, Plus Size Model 1</a>, <a href="https://creativecommons.org/licenses/by/2.0/">CC BY 2.0</a>, modified using local AI.</p>']
    for record in records:
        scores = record.get('scores') or {}
        passed = record['status'] == 'complete' and all(scores[name] >= floor for name, floor in FLOORS.items())
        values = ' / '.join(str(scores.get(name, '-')) for name in FLOORS)
        rows.append(f"| {record['case_id']} | {record['seed']} | {values} | {'Pass' if passed else 'Fail'} | {record.get('notes') or 'Execution failure'} |")
        case = next(c for c in manifest['cases'] if c['id'] == record['case_id'])
        gallery.append('<section><h2>' + html.escape(record['case_id'] + ' / ' + str(record['seed'])) + '</h2><p>' + html.escape(('PASS' if passed else 'FAIL') + ' — ' + values) + '</p><div class="images">')
        for name, path in [('Person', 'evaluation/' + case['person_image']), ('Reference', 'evaluation/' + case['garment_image']), ('Output', record['output'])]:
            if path:
                gallery.append('<figure><figcaption>' + name + '</figcaption><a href="../' + html.escape(path, quote=True) + '"><img loading="lazy" src="../' + html.escape(path, quote=True) + '"></a></figure>')
        gallery.append('</div><p>' + html.escape(record.get('notes') or 'Execution failure') + '</p></section>')
    (EVAL / f'SCORES{suffix}.md').write_text('# Phase 1 visual scores' + suffix + '\n\nScore order: identity / body-pose / garment transfer / background-lighting / artifacts. 0 = unacceptable; 1 = noticeable defects; 2 = intended preview quality. Reviewer: Codex (single AI visual review). See ASSETS.md for attribution and local gallery for comparisons.\n\n| Case | Seed | Scores | Result | Evidence |\n|---|---|---|---|---|\n' + '\n'.join(rows) + '\n')
    (ROOT / f'.local/evaluation_gallery{suffix}.html').write_text('\n'.join(gallery), encoding='utf-8')
    write_report(summary, suffix)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
