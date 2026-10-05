"""Apply a predeclared boundary fallback to pinned cached parser evidence, CPU only."""
import argparse,hashlib,json,time
from pathlib import Path
import numpy as np
from PIL import Image
from boundary_guard import safe_mask
from semantic_constraints import semantic_mask
from protected_regions import constrain
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(protocol_path):
    protocol=json.loads(protocol_path.read_text());cases=json.loads((ROOT/'evaluation/cases/phase1.json').read_text())
    if sha(ROOT/'evaluation/boundary_guard.py')!=protocol['guard_sha256'] or sha(ROOT/'evaluation/semantic_constraints.py')!=protocol['implementation_sha256'] or sha(ROOT/f"evaluation/{protocol['cached_source_experiment']}_protocol.json")!=protocol['cached_source_protocol_sha256']:raise ValueError('Declared cached study changed')
    for case in cases['cases']:
        before=ROOT/'evaluation/benchmarks'/protocol['cached_source_experiment']/case['id']/'records.json'
        destination=ROOT/'evaluation/benchmarks'/protocol['experiment']/case['id']
        if destination.exists():
            retained=json.loads((destination/'records.json').read_text())
            if len(retained)!=2 or any(sha(ROOT/r['output'])!=r['output_sha256'] for r in retained):raise ValueError('Incomplete/changed guarded outputs; reconcile before resume')
            print('Retained guarded pair: '+case['id'],flush=True);continue
        while True:
            rows=json.loads(before.read_text()) if before.exists() else []
            if len(rows)==2 and all(r.get('protocol_sha256') for r in rows):break
            time.sleep(15)
        destination.mkdir(parents=True);results=[]
        for prior in rows:
            started=time.perf_counter();seed=prior['seed']
            paths={name:(before.parent/f'{seed}.{name}-labels.png').relative_to(ROOT).as_posix() for name in ('source','generated')}
            if any(sha(ROOT/path)!=prior['cached_label_hashes'][name] for name,path in paths.items()):raise ValueError('Cached parser label changed')
            raw_path=ROOT/prior['original_output'];source_path=ROOT/'evaluation'/case['person_image']
            if sha(raw_path)!=prior['original_output_sha256'] or sha(source_path)!=prior['source_sha256']:raise ValueError('Matched source/raw changed')
            raw=Image.open(raw_path).convert('RGB');source=Image.open(source_path).convert('RGB').resize(raw.size,Image.Resampling.LANCZOS)
            source_labels=np.asarray(Image.open(ROOT/paths['source']));generated_labels=np.asarray(Image.open(ROOT/paths['generated']))
            fallback=None;metrics=None
            try:mask=semantic_mask(source_labels,generated_labels,policy=protocol['mask_policy'],category=case['category'])
            except ValueError as error:mask=Image.new('L',raw.size,255);fallback=str(error)
            if fallback is None:mask,fallback,metrics=safe_mask(source,raw,mask,source_labels)
            final=raw if fallback else constrain(source,raw,mask)
            output=destination/f'{seed}.png';mask_path=destination/f'{seed}.mask.png';final.save(output);mask.save(mask_path)
            protected=np.asarray(mask)==0
            row={**prior,'experiment':protocol['experiment'],'protocol_sha256':sha(protocol_path),'constraint_applied':fallback is None,'fallback_reason':fallback,'boundary_guard':metrics,
                'output':output.relative_to(ROOT).as_posix(),'output_sha256':sha(output),'mask_sha256':sha(mask_path),'cached_label_paths':paths,
                'raw_protected_pixels_changed':int(np.count_nonzero(np.any(np.asarray(source)!=np.asarray(raw),axis=2)&protected)),
                'protected_pixels_changed':int(np.count_nonzero(np.any(np.asarray(source)!=np.asarray(final),axis=2)&protected)),
                'protected_region_pixels':int(np.count_nonzero(protected)),
                'revised_compositing_seconds':round(time.perf_counter()-started,6),'scores':None,'reviewer':None,'notes':None}
            results.append(row)
        (destination/'records.json').write_text(json.dumps(results,indent=2)+'\n')
        print(json.dumps(dict(case=case['id'],fallbacks=sum(bool(r['fallback_reason']) for r in results))),flush=True)
    print('All40 guarded outputs retained; visual review and evidence publication remain required.',flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--protocol',type=Path,required=True);run(parser.parse_args().protocol)
