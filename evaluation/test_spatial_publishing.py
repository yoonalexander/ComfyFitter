import unittest
from publish_spatial import spatial_decision
from phase1 import FLOORS
class SpatialDecisionTests(unittest.TestCase):
    def test_protection_improves_without_garment_rescoring_but_edges_cannot_regress(self):
        summary=dict(passing=36,categories=dict(shirt=9,hoodie=9,jacket=9,coat=9),raw_protected_pixels_changed=250,protected_pixels_changed=0,
                     matched_score_changes={k:dict(regressed=0,total=0) for k in FLOORS})
        self.assertEqual(spatial_decision(summary),'passed')
        summary['matched_score_changes']['artifacts']['regressed']=1
        self.assertEqual(spatial_decision(summary),'rejected')
        summary['matched_score_changes']['artifacts']['regressed']=0;summary['raw_protected_pixels_changed']=0
        self.assertEqual(spatial_decision(summary),'rejected')
