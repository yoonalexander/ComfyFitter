"""Recovery must preserve exact generation evidence without inventing telemetry."""
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, PngImagePlugin

from evidence import verify_png_graph, without_runtime_fields
from phase1 import summarize
import test_phase1


class PngRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'output.png'
        self.graph = {'1': {'class_type': 'LoadImage', 'inputs': {'image': 'person.png'}}}

    def save(self, graph):
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text('prompt', json.dumps(graph))
        Image.new('RGB', (32, 48)).save(self.path, pnginfo=metadata)

    def test_runtime_hashes_do_not_change_the_graph(self):
        graph = json.loads(json.dumps(self.graph))
        graph['1']['is_changed'] = ['runtime-input-hash']
        self.save(graph)
        self.assertEqual(verify_png_graph(self.path, self.graph), [32, 48])
        self.assertEqual(without_runtime_fields(graph), self.graph)
        self.assertIn('is_changed', graph['1'])

    def test_different_image_or_missing_metadata_cannot_be_recovered(self):
        graph = json.loads(json.dumps(self.graph))
        graph['1']['inputs']['image'] = 'different-person.png'
        self.save(graph)
        with self.assertRaisesRegex(ValueError, 'exact job graph'):
            verify_png_graph(self.path, self.graph)
        Image.new('RGB', (32, 48)).save(self.path)
        with self.assertRaises(ValueError):
            verify_png_graph(self.path, self.graph)

    def test_recovery_does_not_require_fabricated_execution_time(self):
        fixture = test_phase1.QualityGateTests()
        fixture.setUp()
        fixture.records[0]['execution_seconds'] = None
        self.assertEqual(summarize(fixture.manifest, fixture.records)['status'], 'incomplete')
        fixture.records[0]['recovery_evidence'] = {'kind': 'png_embedded_graph'}
        self.assertTrue(summarize(fixture.manifest, fixture.records)['quality_gate_passed'])
        # Recovery never excuses missing review evidence.
        fixture.records[0]['notes'] = None
        self.assertEqual(summarize(fixture.manifest, fixture.records)['status'], 'incomplete')


if __name__ == '__main__':
    unittest.main()
