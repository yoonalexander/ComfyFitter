"""Reject changes to a declared full candidate before running or publishing it."""
import hashlib
import json

from phase1 import SEEDS


def verify_protocol(root, experiment, prompt_paths):
    if not experiment:
        return
    path = root / f'evaluation/{experiment}_protocol.json'
    if not path.exists():
        return  # Unregistered experiments cannot claim a predeclared hash lock.
    protocol = json.loads(path.read_text())
    if protocol.get('experiment') != experiment or protocol.get('seeds') != list(SEEDS):
        raise ValueError('Candidate protocol identity or seeds changed')
    expected_gate = {'global_passes': 32, 'outputs': 40,
                     'per_category_passes': 8, 'per_category_outputs': 10}
    if protocol.get('gate') != expected_gate:
        raise ValueError('Candidate acceptance gate changed')
    files = {'cases': root / 'evaluation/cases/phase1.json',
             'workflow': root / 'workflows/qwen_tryon_upper_candidate_gguf.api.json'}
    for name, file in files.items():
        if hashlib.sha256(file.read_bytes()).hexdigest() != protocol[name + '_sha256']:
            raise ValueError('Locked candidate ' + name + ' changed')
    for role in protocol['prompts']:
        file = prompt_paths.get(role)
        if file is None or hashlib.sha256(file.read_bytes()).hexdigest() != protocol['prompts'][role]:
            raise ValueError('Locked candidate prompt missing or changed: ' + role)
