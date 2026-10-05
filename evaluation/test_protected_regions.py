"""Spatial protection remains exact at boundaries, after feathering and overlap."""
import unittest

from PIL import Image

from protected_regions import build_mask, constrain


class ProtectionTests(unittest.TestCase):
    def test_feather_never_leaks_outside_editable_region(self):
        definition = {'editable_polygons': [[[.25, .25], [.75, .25], [.75, .75], [.25, .75]]],
                      'protected_polygons': [[[.4, .4], [.6, .4], [.6, .6], [.4, .6]]], 'feather_pixels': 8}
        mask = build_mask((101, 101), definition)
        result = constrain(Image.new('RGB', mask.size, 'red'), Image.new('RGB', mask.size, 'blue'), mask)
        # Protection wins even inside the feathered editable polygon.
        self.assertEqual(result.getpixel((50, 50)), (255, 0, 0))
        self.assertEqual(result.getpixel((24, 50)), (255, 0, 0))
        self.assertNotEqual(result.getpixel((30, 30)), (255, 0, 0))

    def test_unprotected_canvas_and_nonfinite_coordinates_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'protected pixels'):
            build_mask((20, 20), {'editable_polygons': [[[0, 0], [1, 0], [1, 1], [0, 1]]]})
        with self.assertRaisesRegex(ValueError, 'finite fractions'):
            build_mask((20, 20), {'editable_polygons': [[[0, 0], [1, 0], [float('nan'), 1]]]})

    def test_mismatched_geometry_is_rejected_instead_of_silent_paste(self):
        with self.assertRaisesRegex(ValueError, 'same canvas'):
            constrain(Image.new('RGB', (20, 20)), Image.new('RGB', (21, 20)), Image.new('L', (20, 20)))


if __name__ == '__main__':
    unittest.main()
