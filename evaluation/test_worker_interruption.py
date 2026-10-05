"""Worker restart failures retain ownership evidence and cannot invent results."""
import copy,json,tempfile,unittest
from pathlib import Path
from publish_references import validate_worker_interruption,sha


class WorkerInterruptionTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.directory=Path(self.temporary.name);self.graph={'node':{'inputs':{'seed':42}}}
        self.record=dict(status='failed',prompt_id='owned-prompt',client_id='owned-client',
                         error={'code':'owned_worker_restart'},execution_seconds=None,wall_seconds=None,
                         vram_sampling_available=False,sampled_device_peak_mib=0)
        self.audit=dict(kind='verified_owned_worker_restart',reason='Stalled worker exited after owned interrupt',
                        prompt_id='owned-prompt',client_id='owned-client',
                        queue_before={'queue_running':[[1,'owned-prompt',self.graph,{'client_id':'owned-client'}]],'queue_pending':[]},
                        history_before={},history_after={},worker_process_exit_verified=True,
                        queue_after={'queue_running':[],'queue_pending':[]},captured_at=1,verified_after=2)

    def check(self,audit=None,record=None):
        path=self.directory/'interruption.json';path.write_text(json.dumps(audit or self.audit))
        row=copy.deepcopy(record or self.record);row['interruption_sha256']=sha(path)
        return validate_worker_interruption(self.directory,row,self.graph)

    def test_verified_restart_is_only_a_failed_submission_with_missing_measurements(self):
        self.check()
        for change in ({'status':'complete'},{'execution_seconds':999},{'output':'invented.png'},{'vram_sampling_available':True}):
            with self.subTest(change=change),self.assertRaises(ValueError):self.check(record={**self.record,**change})

    def test_other_jobs_or_changed_graph_cannot_be_treated_as_owned_interruption(self):
        for change in ('client','graph','other_job','pending','unverified_exit','still_running'):
            audit=copy.deepcopy(self.audit)
            if change=='client':audit['queue_before']['queue_running'][0][3]['client_id']='unrelated'
            elif change=='graph':audit['queue_before']['queue_running'][0][2]['node']['inputs']['seed']=43
            elif change=='other_job':audit['queue_before']['queue_running'].append([2,'other',{},{}])
            elif change=='pending':audit['queue_before']['queue_pending']=[[2,'other',{},{}]]
            elif change=='unverified_exit':audit['worker_process_exit_verified']=False
            else:audit['queue_after']['queue_running']=[[1,'owned-prompt',{},{}]]
            with self.subTest(change=change),self.assertRaises(ValueError):self.check(audit=audit)

    def test_changed_audit_hash_is_rejected(self):
        self.check();row={**self.record,'interruption_sha256':'changed'}
        with self.assertRaisesRegex(ValueError,'evidence changed'):validate_worker_interruption(self.directory,row,self.graph)
