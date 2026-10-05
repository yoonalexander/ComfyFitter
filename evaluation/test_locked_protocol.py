import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from locked_protocol import verify_protocol
from phase1 import SEEDS


class ProtocolTests(unittest.TestCase):
    def test_declared_candidate_rejects_prompt_drift_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = {'cases': root / 'evaluation/cases/phase1.json',
                     'workflow': root / 'workflows/qwen_tryon_upper_candidate_gguf.api.json',
                     'upper_body': root / 'upper.txt', 'outerwear': root / 'outer.txt'}
            for key, file in paths.items():
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text(key)
            hashes = {key: hashlib.sha256(file.read_bytes()).hexdigest() for key, file in paths.items()}
            protocol = {'experiment': 'test', 'seeds': list(SEEDS),
                        'cases_sha256': hashes['cases'], 'workflow_sha256': hashes['workflow'],
                        'prompts': {key: hashes[key] for key in ('upper_body', 'outerwear')},
                        'gate': {'global_passes': 32, 'outputs': 40,
                                 'per_category_passes': 8, 'per_category_outputs': 10}}
            (root / 'evaluation/test_protocol.json').write_text(json.dumps(protocol))
            prompts = {key: paths[key] for key in ('upper_body', 'outerwear')}
            verify_protocol(root, 'test', prompts)
            paths['upper_body'].write_text('different wording')
            with self.assertRaisesRegex(ValueError, 'prompt missing or changed'):
                verify_protocol(root, 'test', prompts)
