"""Run one admitted Phase 1 pair with both fixed seeds on local ComfyUI."""
import argparse
import copy
import hashlib
import json
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from PIL import Image

from phase1 import SEEDS
from evidence import verify_png_graph

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', required=True)
    parser.add_argument('--model', choices=('gguf', 'int8'), default='gguf')
    parser.add_argument('--base-url', default='http://127.0.0.1:8188')
    parser.add_argument('--experiment', help='Keep a separate named experiment under benchmarks, outside the quality gate.')
    parser.add_argument('--prompt-template', type=Path, help='Experimental prompt file; requires --experiment.')
    parser.add_argument('--resume', action='store_true', help='Reconcile an existing run before continuing its missing seeds.')
    args = parser.parse_args()
    if args.prompt_template and not args.experiment:
        parser.error('A changed prompt requires a separately named experiment.')
    if args.experiment and (not args.experiment or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in args.experiment)):
        parser.error('Use a simple lower-case experiment name.')
    base = args.base_url.rstrip('/')
    if urllib.parse.urlparse(base).hostname not in ('127.0.0.1', 'localhost'):
        parser.error('Evaluation runner sends photos only to loopback ComfyUI.')
    manifest = json.loads((ROOT / 'evaluation/cases/phase1.json').read_text(encoding='utf-8'))
    matches = [case for case in manifest['cases'] if case['id'] == args.case]
    if len(matches) != 1:
        parser.error('Select one existing case ID.')
    case = matches[0]
    if not case.get('garment_features') or not all((case.get('asset_rights') or {}).get(role) for role in ('person', 'garment')):
        parser.error('Record garment features and both asset sources before running.')
    inputs = {role: ROOT / 'evaluation' / case[role + '_image'] for role in ('person', 'garment')}
    for path in inputs.values():
        with Image.open(path) as image:
            image.verify()
    storage = ROOT / ('evaluation/benchmarks/' + args.experiment if args.experiment else 'evaluation/results')
    existing = list(storage.glob(args.case + '_' + args.model + '_*/records.json'))
    if existing and not args.resume:
        parser.error('An existing run must be reconciled with --resume; refusing duplicate generation.')
    if len(existing) > 1:
        parser.error('Multiple existing runs require manual reconciliation.')
    if args.resume and existing:
        directory = existing[0].parent
        run_id = directory.name
        records = json.loads(existing[0].read_text())
    else:
        run_id = args.case + '_' + args.model + '_' + uuid.uuid4().hex[:12]
        directory = storage / run_id
        directory.mkdir(parents=True)
        records = []

    def persist():
        temporary = directory / 'records.tmp'
        temporary.write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')
        temporary.replace(directory / 'records.json')

    def request(route, data=None, content_type='application/json'):
        if isinstance(data, dict):
            data = json.dumps(data).encode()
        req = urllib.request.Request(base + route, data=data, headers={'Content-Type': content_type})
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)

    uploaded = {}
    hashes = {role: digest(path.read_bytes()) for role, path in inputs.items()}
    recovered_any = False
    for record in records:
        if record['input_hashes'] != hashes:
            raise RuntimeError('Input bytes changed; cannot resume this benchmark.')
        if record['status'] not in ('complete', 'failed'):
            seed = record['seed']
            exact_graph = json.loads((directory / f'{seed}.api.json').read_text())
            history = request('/history/' + record['prompt_id']).get(record['prompt_id']) if record.get('prompt_id') else None
            queue = request('/queue')
            queued = queue['queue_running'] + queue['queue_pending']
            if history or any(item[1] == record.get('prompt_id') or item[2] == exact_graph for item in queued):
                raise RuntimeError('Original job is still available: reconcile its live history/queue before resume.')
            # History is in-memory. A server restart may lose it while preserving the output.
            candidates = list((ROOT / '.local/output').glob(exact_graph['461']['inputs']['filename_prefix'] + '_*.png'))
            if len(candidates) != 1:
                raise RuntimeError('No unique saved output: cannot silently resubmit an uncertain generation.')
            raw = candidates[0].read_bytes()
            size = verify_png_graph(candidates[0], exact_graph)
            output = directory / f'{seed}.png'
            output.write_bytes(raw)
            record.update(status='complete', output=str(output.relative_to(ROOT)).replace('\\', '/'), output_size=size,
                          output_sha256=digest(raw), execution_seconds=None, sampled_device_peak_mib=None,
                          recovery_evidence={'kind': 'png_embedded_graph', 'source': str(candidates[0].relative_to(ROOT)).replace('\\', '/'),
                                             'note': 'Server history lost after restart. Embedded graph matches; original timing and VRAM unavailable.'})
            persist()
            recovered_any = True
            print('Recovered verified output for ' + args.case + '/' + str(seed), flush=True)
    for role, path in inputs.items():
        raw = path.read_bytes()
        hashes[role] = digest(raw)
        boundary = uuid.uuid4().hex
        name = run_id + '_' + role + path.suffix
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode() + raw + f'\r\n--{boundary}--\r\n'.encode())
        asset = request('/upload/image', body, 'multipart/form-data; boundary=' + boundary)
        uploaded[role] = str(Path(asset.get('subfolder', '')) / asset['name']).replace('\\', '/')
    graph_bytes = (ROOT / 'workflows/qwen_tryon_upper_candidate_gguf.api.json').read_bytes()
    graph = json.loads(graph_bytes)
    if args.model == 'int8':
        graph['459:477'] = {'class_type': 'UNETLoader', 'inputs': {'unet_name': 'qwen_image_2.1_int8_convrot.safetensors', 'weight_dtype': 'default'}}
    graph['470']['inputs']['image'] = uploaded['person']
    graph['475']['inputs']['image'] = uploaded['garment']
    template = 'outerwear' if case['category'] in ('coat', 'jacket') else 'upper_body'
    prompt_path = args.prompt_template or ROOT / f'evaluation/prompts/{template}.txt'
    prompt = prompt_path.read_text(encoding='utf-8').format(garment_type=case['category'])
    graph['459:474']['inputs']['prompt'] = prompt
    environment = request('/system_stats')
    environment_file = 'environment-resumed.json' if existing else 'environment.json'
    (directory / environment_file).write_text(json.dumps(environment, indent=2) + '\n', encoding='utf-8')

    for ordinal, seed in enumerate(SEEDS):
        previous = [r for r in records if r['seed'] == seed]
        if previous:
            if len(previous) != 1 or previous[0]['status'] not in ('complete', 'failed'):
                raise RuntimeError('Seed not reconciled')
            print('Already terminal: ' + args.case + '/' + str(seed), flush=True)
            continue
        current = copy.deepcopy(graph)
        current['459:458']['inputs']['seed'] = seed
        current['461']['inputs']['filename_prefix'] = run_id + '_' + str(seed)
        current_bytes = json.dumps(current, sort_keys=True).encode()
        (directory / f'{seed}.api.json').write_bytes(current_bytes)
        record = {'case_id': case['id'], 'category': case['category'], 'seed': seed, 'model': args.model, 'prompt': prompt, 'workflow_sha256': digest(current_bytes), 'input_hashes': hashes, 'status': 'submitting', 'scores': None, 'reviewer': None, 'notes': None, 'output': None, 'execution_seconds': None, 'run_ordinal': ordinal + 1}
        record['experiment'] = args.experiment
        record['environment_file'] = environment_file
        if recovered_any:
            record['cache_state'] = 'server_restart_first_new_seed; not_a_matched_warm_run'
        record['prompt_template_sha256'] = digest(prompt_path.read_bytes())
        records.append(record)

        persist()
        started = time.monotonic()
        try:
            queued = request('/prompt', {'prompt': current, 'client_id': run_id})
        except (urllib.error.URLError, TimeoutError):
            record['status'] = 'submission_uncertain'
            persist()
            raise RuntimeError('Submission is uncertain. Reconcile ComfyUI queue/history before another run.')
        record['prompt_id'] = queued['prompt_id']
        record['node_errors'] = queued.get('node_errors')
        record['status'] = 'queued'
        persist()
        peak = 0
        while time.monotonic() - started < 900:
            history = request('/history/' + record['prompt_id']).get(record['prompt_id'])
            try:
                used = subprocess.check_output(['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'], text=True, timeout=5)
                peak = max(peak, int(used.strip().splitlines()[0]))
            except (ValueError, subprocess.SubprocessError):
                pass
            if history and history.get('status', {}).get('completed'):
                (directory / f'{seed}.history.json').write_text(json.dumps(history, indent=2) + '\n', encoding='utf-8')
                record['wall_seconds'] = round(time.monotonic() - started, 3)
                stamps = {kind: data.get('timestamp') for kind, data in history['status'].get('messages', [])}
                last = stamps.get('execution_success') or stamps.get('execution_error')
                record['execution_seconds'] = (last - stamps['execution_start']) / 1000 if last and stamps.get('execution_start') else None
                record['sampled_device_peak_mib'] = peak
                if history['status'].get('status_str') != 'success':
                    record['status'] = 'failed'
                    record['error'] = history['status'].get('messages')
                    persist()
                    break
                outputs = history.get('outputs', {}).get('461', {}).get('images', [])
                if not outputs:
                    raise RuntimeError('Successful history has no expected saved output.')
                image = outputs[0]
                with urllib.request.urlopen(base + '/view?' + urllib.parse.urlencode(image), timeout=30) as response:
                    raw = response.read()
                output = directory / f'{seed}.png'
                output.write_bytes(raw)
                with Image.open(output) as decoded:
                    record['output_size'] = list(decoded.size)
                record.update(status='complete', output=str(output.relative_to(ROOT)), output_sha256=digest(raw))
                persist()
                break
            time.sleep(5)
        else:
            record['status'] = 'timeout_unresolved'
            persist()
            raise TimeoutError('Job remains unresolved; inspect it before resubmitting.')
        print(json.dumps({name: record.get(name) for name in ('case_id', 'seed', 'status', 'execution_seconds', 'sampled_device_peak_mib', 'output')}), flush=True)
    print('Review images and add all five scores, reviewer, and evidence notes to ' + str(directory / 'records.json'), flush=True)


if __name__ == '__main__':
    main()
