"""Run a declared CPU protection study as each fresh baseline pair becomes terminal."""
import argparse,hashlib,json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(protocol_path):
    protocol=json.loads(protocol_path.read_text())
    if protocol['status']!='defined_before_execution':raise ValueError('Unregistered study')
    for key,file in {'implementation_sha256':'evaluation/semantic_constraints.py','baseline_protocol_sha256':f"evaluation/{protocol['baseline_experiment']}_protocol.json",'cases_sha256':'evaluation/cases/phase1.json'}.items():
        if sha(ROOT/file)!=protocol[key]:raise ValueError('Declared study component changed')
    cases=json.loads((ROOT/'evaluation/cases/phase1.json').read_text())
    for case in cases['cases']:
        destination=ROOT/'evaluation/benchmarks'/protocol['experiment']/case['id']
        if destination.exists():
            saved=json.loads((destination/'records.json').read_text())
            if len(saved)!=2 or any(sha(ROOT/r['output'])!=r['output_sha256'] for r in saved):raise ValueError('Incomplete/changed retained CPU study; reconcile before resuming')
            print('Retained spatial pair: '+case['id'],flush=True);continue
        while True:
            paths=list((ROOT/'evaluation/benchmarks'/protocol['baseline_experiment']).glob(case['id']+'_gguf_*/records.json'))
            rows=json.loads(paths[0].read_text()) if len(paths)==1 else []
            if len(rows)==2 and all(r['status']=='complete' for r in rows):break
            if any(r['status']=='failed' for r in rows):raise ValueError('Raw inference failed; retain and declare raw fallback without fabricated segmentation')
            time.sleep(15)
        subprocess.run([sys.executable,str(ROOT/'evaluation/semantic_constraints.py'),'--case',case['id'],'--experiment',protocol['experiment'],'--source-experiment',protocol['baseline_experiment'],'--policy',protocol['mask_policy']],check=True)
        path=destination/'records.json';rows=json.loads(path.read_text())
        for row in rows:row['protocol_sha256']=sha(protocol_path)
        path.write_text(json.dumps(rows,indent=2)+'\n')
    print('All 40 spatial outputs retained; full visual review remains required.',flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--protocol',type=Path,required=True);run(parser.parse_args().protocol)
