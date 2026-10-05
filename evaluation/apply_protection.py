"""Private local CPU helper. Accepts owned files; never uploads or downloads assets."""
import argparse,json,time
from pathlib import Path
from PIL import Image
from protection_engine import Engine,sha
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for flag in ('source','raw','output','metadata','model-directory'):parser.add_argument('--'+flag,type=Path,required=True)
    parser.add_argument('--category',choices=('shirt','hoodie','jacket','coat'),required=True);args=parser.parse_args()
    for path in (args.source,args.raw):
        if path.is_symlink() or not path.is_file():raise ValueError('Source files must be regular owned images')
    for path in (args.output,args.metadata):
        if path.exists():raise ValueError('New helper output paths required')
    started=time.perf_counter();engine=Engine(args.model_directory)
    with Image.open(args.source) as source,Image.open(args.raw) as raw:
        final,mask,metrics=engine.apply(source,raw,args.category)
    final.save(args.output);mask.save(args.output.with_suffix('.mask.png'))
    metrics.update(source_sha256=sha(args.source),raw_sha256=sha(args.raw),result_sha256=sha(args.output),wall_seconds=time.perf_counter()-started)
    args.metadata.write_text(json.dumps(metrics,indent=2)+'\n')
if __name__=='__main__':main()
