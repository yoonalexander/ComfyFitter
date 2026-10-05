import unittest
import numpy as np
from PIL import Image
from boundary_guard import safe_mask
class BoundaryGuardTests(unittest.TestCase):
    def inputs(self):
        labels=np.zeros((80,80),dtype=np.uint8);labels[10:30,20:60]=11
        mask=np.zeros((80,80),dtype=np.uint8);mask[30:70,20:60]=255
        source=np.full((80,80,3),120,dtype=np.uint8);generated=source.copy();generated[30:70,20:60]=(0,70,180)
        return labels,Image.fromarray(mask),Image.fromarray(source),generated
    def test_legitimate_garment_color_is_kept_when_protected_skin_boundary_is_continuous(self):
        labels,mask,source,generated=self.inputs()
        self.assertIsNone(safe_mask(source,Image.fromarray(generated),mask,labels)[1])
    def test_ambiguous_face_boundary_keeps_raw_instead_of_clipping_new_collar(self):
        labels,mask,source,generated=self.inputs();generated[27:30,20:60]=(0,70,180)
        fallback_mask,reason,metrics=safe_mask(source,Image.fromarray(generated),mask,labels)
        self.assertIn('boundary',reason)
        self.assertTrue(np.all(np.asarray(fallback_mask)==255))
        self.assertGreater(metrics['discontinuous_fraction'],.15)
