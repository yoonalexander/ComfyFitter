"""Verify saved graph/input/output evidence, including outputs from a lost server history."""
import copy
import hashlib
import json
from pathlib import Path

from PIL import Image


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def without_runtime_fields(graph):
    graph = copy.deepcopy(graph)
    for node in graph.values():
        node.pop('is_changed', None)
    return graph


def verify_png_graph(path, graph):
    with Image.open(path) as image:
        image.load()
        embedded = json.loads(image.info.get('prompt', '{}'))
        size = list(image.size)
    if without_runtime_fields(embedded) != without_runtime_fields(graph):
        raise ValueError('Saved PNG does not match the exact job graph')
    return size


def validate_record(root, directory, case, record, *, experiment=None, prompt_paths=None):
    seed = record['seed']
    graph_path = directory / f'{seed}.api.json'
    if sha(graph_path) != record['workflow_sha256']:
        raise ValueError('Workflow hash mismatch: ' + case['id'])
    graph = json.loads(graph_path.read_text())
    baseline = json.loads((root / 'workflows/qwen_tryon_upper_candidate_gguf.api.json').read_text())
    template = 'outerwear' if case['category'] in ('coat', 'jacket') else 'upper_body'
    if case['category']=='jacket' and (prompt_paths or {}).get('jacket'):template='jacket'
    prompt_path = (prompt_paths or {}).get(template) or root / f'evaluation/prompts/{template}.txt'
    locked_prompt = prompt_path.read_text().format(garment_type=case['category'])
    if record['prompt'] != locked_prompt or record.get('experiment') != experiment:
        raise ValueError('Prompt or experiment does not match the selected evaluation protocol')
    for node, field in (('470', 'image'), ('475', 'image'), ('461', 'filename_prefix')):
        baseline[node]['inputs'][field] = graph[node]['inputs'][field]
    baseline['459:458']['inputs']['seed'] = seed
    baseline['459:474']['inputs']['prompt'] = locked_prompt
    if without_runtime_fields(graph) != without_runtime_fields(baseline):
        raise ValueError('Graph differs from locked workflow beyond allowed job inputs')
    if graph['459:458']['inputs']['seed'] != seed or graph['459:474']['inputs']['prompt'] != record['prompt']:
        raise ValueError('Prompt/seed evidence mismatch')
    sampler = {'steps': 25, 'cfg': 1.0, 'sampler_name': 'euler', 'scheduler': 'simple', 'denoise': 1.0}
    if any(graph['459:458']['inputs'][k] != v for k, v in sampler.items()):
        raise ValueError('Locked sampler settings changed')
    if graph['459:477']['inputs']['unet_name'] != 'qwen_image_2.1_Q4_K_M.gguf' or graph['459:474']['inputs']['resolution'] != 1024:
        raise ValueError('Locked model/resolution changed')
    if record['input_hashes'] != {role: sha(root / 'evaluation' / case[role + '_image']) for role in ('person', 'garment')}:
        raise ValueError('Input hash mismatch: ' + case['id'])
    input_root = (root / '.local/input').resolve()
    for node, role in (('470', 'person'), ('475', 'garment')):
        uploaded = (input_root / graph[node]['inputs']['image']).resolve()
        if not uploaded.is_relative_to(input_root) or sha(uploaded) != record['input_hashes'][role]:
            raise ValueError('Uploaded graph input does not match source bytes: ' + role)
    history_path = directory / f'{seed}.history.json'
    if history_path.exists():
        history = json.loads(history_path.read_text())
        if history['prompt'][1] != record['prompt_id'] or without_runtime_fields(history['prompt'][2]) != without_runtime_fields(graph):
            raise ValueError('History prompt/graph mismatch')
        if record['status'] == 'complete' and history['status']['status_str'] != 'success':
            raise ValueError('History did not succeed')
        record['history'] = str(history_path.relative_to(root)).replace('\\', '/')
    elif record.get('recovery_evidence', {}).get('kind') == 'png_embedded_graph':
        # A recovered output proves generation, but cannot supply missing timings/history.
        if record['status'] != 'complete' or record.get('execution_seconds') is not None:
            raise ValueError('Recovered PNG must explicitly retain missing timing')
        record['history'] = None
    else:
        raise ValueError('Missing ComfyUI history or verifiable PNG recovery evidence')
    if record['status'] == 'complete':
        output = (root / record['output']).resolve()
        if not output.is_relative_to((root / 'evaluation').resolve()):
            raise ValueError('Output outside evaluation storage')
        if sha(output) != record['output_sha256']:
            raise ValueError('Output hash mismatch')
        if verify_png_graph(output, graph) != record['output_size']:
            raise ValueError('Output size mismatch')
    record['graph'] = str(graph_path.relative_to(root)).replace('\\', '/')
    return record
