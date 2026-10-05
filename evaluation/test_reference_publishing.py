import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from publish_references import reference_decision, outfit_decision, linked_capacity, sha

class ReferenceDecisionTests(unittest.TestCase):
    def test_capacity_does_not_replace_matched_fidelity_or_hide_regression(self):
        baseline=dict(identity=2,body_pose=2,background_lighting=2,garment_transfer=2,artifacts=1,detailed_fidelity=2)
        rows=[dict(category='hoodie',mode='multi_reference',scores={**baseline,'detailed_fidelity':3},matched_review=dict(scores=baseline)) for _ in range(8)]
        capacity=[dict(mode='capacity',status='complete',image_order=['person','garment','back','side','detail']) for _ in range(2)]
        self.assertEqual(reference_decision(rows,capacity)['status'],'passed')
        rows[0]['scores']['identity']=1
        self.assertEqual(reference_decision(rows,capacity)['status'],'rejected')
        rows[0]['scores']['identity']=2;capacity[1]['status']='failed'
        self.assertEqual(reference_decision(rows,capacity)['status'],'rejected')

    def test_outfit_combination_is_counted_in_its_full_fixed_denominator(self):
        scores=dict(identity=2,body_pose=2,inner_transfer=2,outer_transfer=2,background_lighting=1,artifacts=1,layering_occlusion=1)
        rows=[dict(category='shirt',outer_category=outer,status='complete',scores=scores.copy()) for outer in ('jacket','coat') for _ in range(8)]
        rows[0]['scores']['outer_transfer']=0;rows[1]['scores']['inner_transfer']=0
        result=outfit_decision(rows)
        self.assertEqual(result['combinations'],['shirt+coat'])
        self.assertEqual(result['counts']['shirt+jacket'],dict(expected=8,passed=6))
        self.assertEqual(result['reviewed'],16)

    def test_narrowed_coat_study_keeps_all_eight_and_original_seven_pass_floor(self):
        scores=dict(identity=2,body_pose=2,inner_transfer=2,outer_transfer=2,background_lighting=1,artifacts=1,layering_occlusion=1)
        rows=[dict(category='shirt',outer_category='coat',status='complete',scores=scores.copy()) for _ in range(8)]
        rows[0]['scores']['body_pose']=1
        self.assertEqual(outfit_decision(rows,expected=8)['status'],'passed')
        rows[1]['scores']['outer_transfer']=1
        self.assertEqual(outfit_decision(rows,expected=8)['status'],'rejected')
        self.assertEqual(outfit_decision(rows[:-1],expected=8)['status'],'rejected')
        for row in rows:row['outer_category']='jacket';row['scores']=scores.copy()
        self.assertEqual(outfit_decision(rows,expected=8)['status'],'rejected')

    def test_linked_capacity_revalidates_evidence_without_reusing_quality_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'evaluation').mkdir()
            path=root/'evaluation/multiple_reference_v1_protocol.json'
            path.write_text(json.dumps(dict(graph_sha256='graph',implementation_sha256='implementation')))
            protocol=dict(experiment='multiple_reference_v2',graph_sha256='graph',implementation_sha256='implementation',
                          capacity_study=dict(experiment='multiple_reference_v1',protocol_sha256=sha(path),sample_id='capacity'))
            rows=[dict(mode='multi_reference',sample_id='quality'),dict(mode='capacity',sample_id='capacity',seed=1),dict(mode='capacity',sample_id='capacity',seed=2)]
            with patch('publish_references.validate_study',return_value=({},rows)) as validate:
                self.assertEqual(linked_capacity(root,protocol),rows[1:])
                validate.assert_called_once_with(root,path)
            path.write_text('{}')
            with patch('publish_references.validate_study') as validate:
                with self.assertRaisesRegex(ValueError,'protocol changed'):linked_capacity(root,protocol)
                validate.assert_not_called()

    def test_capacity_from_a_different_graph_cannot_qualify_another_study(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'evaluation').mkdir()
            path=root/'evaluation/multiple_reference_v1_protocol.json'
            path.write_text(json.dumps(dict(graph_sha256='different',implementation_sha256='implementation')))
            protocol=dict(experiment='multiple_reference_v2',graph_sha256='graph',implementation_sha256='implementation',
                          capacity_study=dict(experiment='multiple_reference_v1',protocol_sha256=sha(path),sample_id='capacity'))
            with self.assertRaisesRegex(ValueError,'same graph'):linked_capacity(root,protocol)
