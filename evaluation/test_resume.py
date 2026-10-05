"""Exercise crash recovery end-to-end without sending images to a real server."""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlparse

from PIL import Image, PngImagePlugin

import run_case
from evidence import sha


class ResumeTests(unittest.TestCase):
    def test_saved_seed_is_not_resubmitted_or_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ('evaluation/cases', 'evaluation/prompts', 'evaluation/assets', 'workflows', '.local/output'):
                (root / directory).mkdir(parents=True)
            case = {'id': 'shirt_01', 'category': 'shirt', 'person_image': 'assets/person.png',
                    'garment_image': 'assets/garment.png', 'garment_features': ['collar'],
                    'asset_rights': {'person': 'test', 'garment': 'test'}}
            (root / 'evaluation/cases/phase1.json').write_text(json.dumps({'cases': [case]}))
            (root / 'evaluation/prompts/upper_body.txt').write_text('Transfer {garment_type}')
            for role in ('person', 'garment'):
                Image.new('RGB', (32, 48)).save(root / f'evaluation/assets/{role}.png')
            graph = {'470': {'class_type': 'LoadImage', 'inputs': {'image': 'original-person.png'}},
                     '475': {'class_type': 'LoadImage', 'inputs': {'image': 'original-garment.png'}},
                     '461': {'class_type': 'SaveImageAdvanced', 'inputs': {'filename_prefix': 'old-output'}},
                     '459:458': {'inputs': {'seed': run_case.SEEDS[0]}},
                     '459:474': {'inputs': {'prompt': 'Transfer shirt'}}}
            (root / 'workflows/qwen_tryon_upper_candidate_gguf.api.json').write_text(json.dumps(graph))
            directory = root / 'evaluation/results/shirt_01_gguf_original'
            directory.mkdir(parents=True)
            graph_path = directory / f'{run_case.SEEDS[0]}.api.json'
            original_bytes = json.dumps(graph).encode()
            graph_path.write_bytes(original_bytes)
            (directory / 'environment.json').write_text('{"original": true}')
            metadata = PngImagePlugin.PngInfo()
            metadata.add_text('prompt', json.dumps(graph))
            Image.new('RGB', (32, 48)).save(root / '.local/output/old-output_00001.png', pnginfo=metadata)
            record = {'case_id': case['id'], 'category': 'shirt', 'seed': run_case.SEEDS[0],
                      'prompt_id': 'old-prompt', 'status': 'queued', 'prompt': 'Transfer shirt',
                      'workflow_sha256': sha(graph_path), 'input_hashes': {role: sha(root / f'evaluation/assets/{role}.png') for role in ('person', 'garment')}}
            (directory / 'records.json').write_text(json.dumps([record]))
            submissions = []

            def open_request(request, **kwargs):
                url = request if isinstance(request, str) else request.full_url
                route = urlparse(url).path
                if route == '/history/old-prompt':
                    data = {}
                elif route == '/queue':
                    data = {'queue_running': [], 'queue_pending': []}
                elif route == '/upload/image':
                    data = {'name': 'new-upload.png'}
                elif route == '/system_stats':
                    data = {'new_environment': True}
                elif route == '/prompt':
                    submissions.append(json.loads(request.data)['prompt'])
                    data = {'prompt_id': 'new-prompt'}
                elif route == '/history/new-prompt':
                    data = {'new-prompt': {'status': {'completed': True, 'status_str': 'success',
                            'messages': [['execution_start', {'timestamp': 1000}], ['execution_success', {'timestamp': 3000}]]},
                            'outputs': {'461': {'images': [{'filename': 'new.png', 'type': 'output', 'subfolder': ''}]}}}}
                elif route == '/view':
                    output = io.BytesIO()
                    Image.new('RGB', (32, 48)).save(output, format='PNG')
                    return io.BytesIO(output.getvalue())
                else:
                    raise AssertionError('Unexpected request: ' + route)
                return io.BytesIO(json.dumps(data).encode())

            with patch.object(run_case, 'ROOT', root), patch.object(sys, 'argv', ['run_case.py', '--case', 'shirt_01', '--resume']), \
                 patch('urllib.request.urlopen', side_effect=open_request), patch('subprocess.check_output', return_value='1234'):
                run_case.main()
            final = json.loads((directory / 'records.json').read_text())
            self.assertEqual(len(submissions), 1)
            self.assertEqual(submissions[0]['459:458']['inputs']['seed'], run_case.SEEDS[1])
            self.assertEqual(graph_path.read_bytes(), original_bytes)
            self.assertEqual((directory / 'environment.json').read_text(), '{"original": true}')
            self.assertEqual(final[0]['status'], 'complete')
            self.assertIsNone(final[0]['execution_seconds'])
            self.assertEqual(final[0]['recovery_evidence']['kind'], 'png_embedded_graph')
            self.assertEqual(final[1]['execution_seconds'], 2)
            self.assertTrue(final[1]['cache_state'].startswith('server_restart'))


if __name__ == '__main__':
    unittest.main()
