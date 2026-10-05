"""Compare a declared mask-policy revision using the same cached parser labels.

No inference is resubmitted. Original parsing latency is retained separately from
the measured new compositing work. This command never assigns visual scores.
"""
import json,time,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
from semantic_constraints import semantic_mask
from protected_regions import constrain
ROOT=Path(__file__).resolve().parents[1]
source_experiment='semantic_full_v3'; experiment='semantic_occlusion_v2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
cases={c['id']:c for c in json.loads((ROOT/'evaluation/cases/phase1.json').read_text())['cases']}
for records_path in sorted((ROOT/'evaluation/benchmarks'/source_experiment).glob('*/records.json')):
    case=cases[records_path.parent.name];directory=ROOT/'evaluation/benchmarks'/experiment/case['id']
    if directory.exists():raise ValueError('Existing study must not be overwritten')
    directory.mkdir(parents=True);results=[]
    for record in json.loads(records_path.read_text()):
        raw=ROOT/record['original_output'];source_path=ROOT/'evaluation'/case['person_image'];seed=record['seed']
        assert sha(raw)==record['original_output_sha256'] and sha(source_path)==record['source_sha256']
        source_labels_path=records_path.parent/f'{seed}.source-labels.png';generated_labels_path=records_path.parent/f'{seed}.generated-labels.png'
        started=time.perf_counter()
        with Image.open(raw) as image:generated=image.convert('RGB')
        with Image.open(source_path) as image:source=image.convert('RGB').resize(generated.size,Image.Resampling.LANCZOS)
        source_labels=np.array(Image.open(source_labels_path));generated_labels=np.array(Image.open(generated_labels_path))
        fallback=None
        try:
            mask=semantic_mask(source_labels,generated_labels,policy='occlusion_v2',category=case['category']);output=constrain(source,generated,mask)
        except ValueError as e:
            fallback=str(e);mask=Image.new('L',generated.size,255);output=generated
        output_path=directory/f'{seed}.png';mask_path=directory/f'{seed}.mask.png';output.save(output_path);mask.save(mask_path)
        result={**record,'experiment':experiment,'mask_policy':'occlusion_v2','output':output_path.relative_to(ROOT).as_posix(),
            'output_sha256':sha(output_path),'mask_sha256':sha(mask_path),'constraint_applied':fallback is None,'fallback_reason':fallback,
            'cached_parser_experiment':source_experiment,'cached_label_hashes':{'source':sha(source_labels_path),'generated':sha(generated_labels_path)},
            'cached_label_paths':{'source':source_labels_path.relative_to(ROOT).as_posix(),'generated':generated_labels_path.relative_to(ROOT).as_posix()},
            'original_parser_and_constraint_seconds':record['constraint_wall_seconds'],'revised_compositing_seconds':round(time.perf_counter()-started,6),
            'scores':None,'reviewer':None,'notes':None}
        results.append(result)
    (directory/'records.json').write_text(json.dumps(results,indent=2)+'\n')
print('40 matched outputs prepared; visual review required.')
