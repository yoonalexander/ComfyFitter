"""Sequential Phase 1 evaluation; resume only reconciled terminal case runs."""
import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from phase1 import SEEDS, admission
from locked_protocol import verify_protocol

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cold-first', action='store_true', help='Unload models before the first new case; requires an idle dedicated server.')
    parser.add_argument('--experiment', help='Separate full 40-output experiment; never replaces the locked baseline.')
    parser.add_argument('--upper-body-prompt', type=Path)
    parser.add_argument('--outerwear-prompt', type=Path)
    parser.add_argument('--jacket-prompt', type=Path, help='Explicit jacket template; outerwear then applies to coats.')
    args = parser.parse_args()
    if (args.upper_body_prompt or args.outerwear_prompt or args.jacket_prompt) and not args.experiment:
        parser.error('Changed prompts require a separate --experiment.')
    if args.experiment and any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in args.experiment):
        parser.error('Use a simple lower-case experiment name.')
    storage = ROOT / ('evaluation/benchmarks/' + args.experiment if args.experiment else 'evaluation/results')
    prompt_paths={'upper_body':args.upper_body_prompt,'outerwear':args.outerwear_prompt}
    if args.jacket_prompt:prompt_paths['jacket']=args.jacket_prompt
    verify_protocol(ROOT, args.experiment, prompt_paths)
    manifest = json.loads((ROOT / 'evaluation/cases/phase1.json').read_text())
    errors = admission(manifest, ROOT / 'evaluation')
    if errors:
        raise RuntimeError('\n'.join(errors))
    cold_pending = args.cold_first
    for case in manifest['cases']:
        candidates = list(storage.glob(case['id'] + '_gguf_*/records.json'))
        command = [sys.executable, str(ROOT / 'evaluation/run_case.py'), '--case', case['id']]
        if args.experiment:
            command += ['--experiment', args.experiment]
        prompt = args.outerwear_prompt if case['category'] in ('jacket', 'coat') else args.upper_body_prompt
        if case['category']=='jacket' and args.jacket_prompt:prompt=args.jacket_prompt
        if prompt:
            command += ['--prompt-template', str(prompt)]
        if len(candidates) > 1:
            raise RuntimeError('Multiple runs need manual reconciliation: ' + case['id'])
        if candidates:
            records = json.loads(candidates[0].read_text())
            if len(records) == 2 and {r['seed'] for r in records} == set(SEEDS) and all(r['status'] in ('complete', 'failed') for r in records):
                for record in records:
                    if record['input_hashes'] != {role: hashlib.sha256((ROOT / 'evaluation' / case[role + '_image']).read_bytes()).hexdigest() for role in ('person', 'garment')}:
                        raise RuntimeError('Inputs changed after generation: ' + case['id'])
                print('Already terminal: ' + case['id'], flush=True)
                continue
            print('Reconciling unfinished case: ' + case['id'], flush=True)
            subprocess.run(command + ['--resume'], check=True)
            continue
        cache_state = 'session_warm'
        if cold_pending:
            with urllib.request.urlopen('http://127.0.0.1:8188/queue') as response:
                queue = json.load(response)
            if queue['queue_running'] or queue['queue_pending']:
                raise RuntimeError('Dedicated ComfyUI must be idle before model unloading.')
            request = urllib.request.Request('http://127.0.0.1:8188/free', data=json.dumps({'unload_models': True, 'free_memory': True}).encode(), headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(request).close()
            # /free schedules work on the worker thread; allow it to process flags
            # before submission. This does not clear the OS filesystem cache.
            time.sleep(2)
            cold_pending = False
            cache_state = 'models_unloaded_first_seed; OS_disk_cache_not_cleared'
        print('Starting ' + case['id'] + ' (' + cache_state + ')', flush=True)
        subprocess.run(command, check=True)
        path, = storage.glob(case['id'] + '_gguf_*/records.json')
        records = json.loads(path.read_text())
        records[0]['cache_state'] = cache_state
        records[1]['cache_state'] = 'same_case_second_seed_warm'
        path.write_text(json.dumps(records, indent=2) + '\n')
    print('All 40 executions terminal; visual scoring still required.', flush=True)


if __name__ == '__main__':
    main()
