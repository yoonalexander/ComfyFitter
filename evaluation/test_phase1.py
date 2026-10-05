"""Guard the quality gate against missing, duplicate, and partially scored evidence."""
import unittest

from phase1 import CATEGORIES, FLOORS, SEEDS, summarize


class QualityGateTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {'seeds': list(SEEDS), 'cases': [{'id': f'{category}_{index}', 'category': category} for category in CATEGORIES for index in range(5)]}
        self.records = [{
            'case_id': case['id'], 'category': case['category'], 'seed': seed,
            'status': 'complete', 'scores': dict(FLOORS), 'output': 'test-only.png',
            'prompt': 'test-only', 'workflow_sha256': 'test-only',
            'input_hashes': {'person': 'test-only', 'garment': 'test-only'},
            'execution_seconds': 1, 'reviewer': 'test-only', 'notes': 'test-only',
        } for case in self.manifest['cases'] for seed in SEEDS]

    def test_no_results_cannot_pass(self):
        self.assertEqual(summarize(self.manifest, [])['status'], 'incomplete')

    def test_gate_boundary_and_inference_failures(self):
        for index in (0, 1, 10, 11, 20, 21, 30, 31):
            self.records[index] = dict(self.records[index], status='failed', error='test-only')
        summary = summarize(self.manifest, self.records)
        self.assertTrue(summary['quality_gate_passed'])
        self.assertEqual(summary['passed'], 32)
        self.assertEqual(summary['inference_failures'], 8)

    def test_global_pass_rate_cannot_hide_weak_category(self):
        for record in self.records[:3]:
            record['scores']['garment_transfer'] = 0
        self.assertEqual(summarize(self.manifest, self.records)['status'], 'failed')

    def test_missing_review_cannot_pass(self):
        self.records[0]['reviewer'] = None
        self.assertEqual(summarize(self.manifest, self.records)['status'], 'incomplete')

    def test_boolean_is_not_a_visual_score(self):
        self.records[0]['scores']['artifacts'] = True
        self.assertEqual(summarize(self.manifest, self.records)['status'], 'incomplete')

    def test_duplicate_result_is_rejected(self):
        with self.assertRaises(ValueError):
            summarize(self.manifest, self.records + [self.records[0]])


if __name__ == '__main__':
    unittest.main()
