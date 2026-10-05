"""Render raw and constrained outputs together without assigning scores."""
import argparse,json
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--experiment',required=True)
parser.add_argument('--case',help='Render one declared case instead of the full study')
args=parser.parse_args()
assert args.experiment and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in args.experiment)
cases=json.loads((ROOT/'evaluation/cases/phase1.json').read_text())['cases']
for case in cases:
    if args.case and case['id']!=args.case:continue
    p=ROOT/'evaluation/benchmarks'/args.experiment/case['id']/'records.json'
    if not p.exists():continue
    rows=json.loads(p.read_text())
    items=[('Source',ROOT/'evaluation'/case['person_image']),('Reference',ROOT/'evaluation'/case['garment_image'])]
    items += [(f"Raw {r['seed']}",ROOT/r['original_output']) for r in rows]
    items += [(f"Constrained {r['seed']}"+(' fallback' if r.get('fallback_reason') else ''),ROOT/r['output']) for r in rows]
    sheet=Image.new('RGB',(400*len(items),750),'#eeeeee');draw=ImageDraw.Draw(sheet)
    for i,(label,path) in enumerate(items):
        with Image.open(path) as image:tile=ImageOps.contain(image.convert('RGB'),(392,708))
        sheet.paste(tile,(i*400+(400-tile.width)//2,30));draw.text((i*400+5,8),label,fill='black')
    dest=ROOT/'.local'/f"{case['id']}_{args.experiment}_matched.jpg";sheet.save(dest,quality=95)
    print(dest)
