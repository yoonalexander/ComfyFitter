"""A failed benchmark remains publishable even without successful timing samples."""
import unittest

from publish_results import timing_summary


class PublishingTests(unittest.TestCase):
    def test_all_failures_report_unavailable_timing(self):
        self.assertEqual(timing_summary([]), {'count': 0, 'min': None, 'median': None, 'max': None})

    def test_metrics_use_only_the_supplied_measured_samples(self):
        self.assertEqual(timing_summary([220, 180, 200]), {'count': 3, 'min': 180, 'median': 200, 'max': 220})


if __name__ == '__main__':
    unittest.main()
