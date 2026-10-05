"""Semantic regions protect identity without clipping a legitimately larger garment."""
import unittest

import numpy as np

from semantic_constraints import semantic_mask


class SemanticMaskTests(unittest.TestCase):
    def test_conservative_policy_falls_back_before_ambiguous_hair_pastes_old_blouse(self):
        source=np.zeros((80,80),dtype=np.uint8);generated=source.copy()
        source[20:70,20:60]=4;generated[20:70,20:60]=4;source[20:70,20:27]=2
        semantic_mask(source,generated,policy='occlusion_v2')
        with self.assertRaisesRegex(ValueError,'Hair segmentation'):
            semantic_mask(source,generated,policy='occlusion_v3')

    def test_undeclared_mask_policy_is_rejected(self):
        source=np.zeros((80,80),dtype=np.uint8);source[20:70,20:60]=4
        with self.assertRaisesRegex(ValueError,'Unknown mask policy'):
            semantic_mask(source,source,policy='typo')
    def test_new_sleeves_can_cover_old_arms_but_matching_exposed_hands_stay_protected(self):
        source=np.zeros((80,80),dtype=np.uint8);generated=source.copy()
        source[30:70,30:50]=4;generated[20:70,20:60]=4
        source[35:40,25:30]=14;source[50:55,40:45]=14;generated[50:55,40:45]=14
        mask=np.asarray(semantic_mask(source,generated,policy='occlusion_v2'))
        self.assertGreater(mask[37,27],0)
        self.assertEqual(mask[52,42],0)

    def test_coat_dress_label_accepts_longer_silhouette_and_ambiguous_hair_falls_back(self):
        source=np.zeros((80,80),dtype=np.uint8);generated=source.copy()
        generated[20:70,20:60]=7
        mask=np.asarray(semantic_mask(source,generated,policy='occlusion_v2',category='coat'))
        self.assertGreater(mask[60,30],0)
        source[20:70,20:40]=2
        with self.assertRaisesRegex(ValueError,'Hair segmentation'):
            semantic_mask(source,generated,policy='occlusion_v2',category='coat')
    def test_expanded_garment_is_editable_but_face_and_hand_override_it(self):
        source = np.zeros((80, 80), dtype=np.uint8)
        generated = source.copy()
        source[35:65, 30:50] = 4
        generated[25:70, 20:60] = 4
        source[25:34, 30:50] = 11
        source[45:50, 40:45] = 14
        mask = np.asarray(semantic_mask(source, generated))
        self.assertGreater(mask[60, 22], 0)  # new silhouette beyond original clothing
        self.assertEqual(mask[30, 40], 0)  # source face is protected inside generated clothing
        self.assertEqual(mask[47, 42], 0)  # source exposed hand/arm is protected
        self.assertEqual(mask[0, 0], 0)  # background outside the edit envelope

    def test_missing_clothing_and_geometry_mismatch_require_fallback(self):
        source = np.zeros((40, 40), dtype=np.uint8)
        with self.assertRaisesRegex(ValueError, 'upper garment'):
            semantic_mask(source, source)
        with self.assertRaisesRegex(ValueError, 'same image geometry'):
            semantic_mask(source, np.zeros((41, 40), dtype=np.uint8))


if __name__ == '__main__':
    unittest.main()
