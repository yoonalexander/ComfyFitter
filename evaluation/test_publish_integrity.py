"""Publication rejects altered workflows, input mappings and edited output bytes."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, PngImagePlugin

from evidence import sha, validate_record

SOURCE = Path(__file__).resolve().parents[1]


class PublicationIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for directory in ('workflows', 'evaluation/prompts', 'evaluation/assets', '.local/input', 'evaluation/results/test'):
            (self.root / directory).mkdir(parents=True)
        self.case = {'id': 'shirt_01', 'category': 'shirt', 'person_image': 'assets/person.png', 'garment_image': 'assets/garment.png'}
        for role, color in (('person', 'red'), ('garment', 'blue')):
            Image.new('RGB', (32, 48), color).save(self.root / f'evaluation/assets/{role}.png')
            (self.root / f'.local/input/{role}.png').write_bytes((self.root / f'evaluation/assets/{role}.png').read_bytes())
        baseline_path = SOURCE / 'workflows/qwen_tryon_upper_candidate_gguf.api.json'
        (self.root / 'workflows/qwen_tryon_upper_candidate_gguf.api.json').write_bytes(baseline_path.read_bytes())
        prompt = 'Locked {garment_type} prompt'
        (self.root / 'evaluation/prompts/upper_body.txt').write_text(prompt)
        self.graph = json.loads(baseline_path.read_text())
        self.graph['470']['inputs']['image'] = 'person.png'
        self.graph['475']['inputs']['image'] = 'garment.png'
        self.graph['459:474']['inputs']['prompt'] = 'Locked shirt prompt'
        self.directory = self.root / 'evaluation/results/test'
        self.record = {'case_id': 'shirt_01', 'seed': 2026093001, 'status': 'complete',
                       'prompt': 'Locked shirt prompt', 'input_hashes': {role: sha(self.root / f'evaluation/assets/{role}.png') for role in ('person', 'garment')},
                       'experiment': None, 'execution_seconds': None, 'output': 'evaluation/results/test/output.png',
                       'output_size': [32, 48], 'recovery_evidence': {'kind': 'png_embedded_graph'}}
        self.write_graph_and_output()

    def write_graph_and_output(self):
        graph_path = self.directory / '2026093001.api.json'
        graph_path.write_text(json.dumps(self.graph))
        self.record['workflow_sha256'] = sha(graph_path)
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text('prompt', json.dumps(self.graph))
        Image.new('RGB', (32, 48), 'green').save(self.root / self.record['output'], pnginfo=metadata)
        self.record['output_sha256'] = sha(self.root / self.record['output'])

    def validate(self):
        return validate_record(self.root, self.directory, self.case, copy.deepcopy(self.record))

    def test_complete_recovery_can_publish_with_explicitly_missing_history(self):
        self.assertIsNone(self.validate()['history'])

    def test_encoder_change_fails_even_with_consistent_png_and_hashes(self):
        self.graph['459:453']['inputs']['clip_name'] = 'different-encoder.safetensors'
        self.write_graph_and_output()
        with self.assertRaisesRegex(ValueError, 'locked workflow'):
            self.validate()

    def test_uploaded_file_must_be_the_hashed_source(self):
        (self.root / '.local/input/person.png').write_bytes((self.root / 'evaluation/assets/garment.png').read_bytes())
        with self.assertRaisesRegex(ValueError, 'Uploaded graph input'):
            self.validate()

    def test_output_modification_cannot_publish(self):
        with (self.root / self.record['output']).open('ab') as output:
            output.write(b'altered')
        with self.assertRaisesRegex(ValueError, 'Output hash'):
            self.validate()

    def test_recovery_cannot_invent_execution_time(self):
        self.record['execution_seconds'] = 123
        with self.assertRaisesRegex(ValueError, 'missing timing'):
            self.validate()


if __name__ == '__main__':
    unittest.main()
