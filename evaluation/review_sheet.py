"""Make local comparison sheets for visual review; never assigns quality scores."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', required=True)
    parser.add_argument('--experiment')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'evaluation/cases/phase1.json').read_text())
    case = next(c for c in manifest['cases'] if c['id'] == args.case)
    storage = ROOT / ('evaluation/benchmarks/' + args.experiment if args.experiment else 'evaluation/results')
    paths = list(storage.glob(args.case + '_gguf_*/records.json'))
    if len(paths) != 1:
        raise ValueError('Expected one canonical run')
    records = json.loads(paths[0].read_text())
    items = [('Source', ROOT / 'evaluation' / case['person_image']),
             ('Reference', ROOT / 'evaluation' / case['garment_image'])]
    items += [(str(r['seed']), ROOT / r['output']) for r in records if r['status'] == 'complete']
    sheet = Image.new('RGB', (500 * len(items), 820), '#eeeeee')
    draw = ImageDraw.Draw(sheet)
    for i, (label, path) in enumerate(items):
        with Image.open(path) as image:
            tile = ImageOps.contain(image.convert('RGB'), (492, 780))
        sheet.paste(tile, (i * 500 + (500 - tile.width) // 2, 30))
        draw.text((i * 500 + 8, 8), label, fill='black')
    destination = ROOT / '.local' / (args.case + ('_' + args.experiment if args.experiment else '') + '_review.jpg')
    sheet.save(destination, quality=95)
    print(destination)
    print(json.dumps(case['garment_features']))


if __name__ == '__main__':
    main()
