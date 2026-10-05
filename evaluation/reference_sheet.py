"""Render declared reference/outfit inputs and complete outputs for visual review."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]


def render(experiment, sample_id=None):
    if experiment not in ('multiple_reference_v1', 'multiple_reference_v2', 'two_garment_v1', 'two_garment_v2', 'two_garment_v3', 'two_garment_v4', 'two_garment_v5'):
        raise ValueError('Choose a declared reference study')
    protocol = json.loads((ROOT / f'evaluation/{experiment}_protocol.json').read_text())
    baseline_path = ROOT / f"evaluation/reviewed_results_{protocol['baseline_experiment']}.json"
    baseline = {(r['case_id'], r['seed']): r for r in json.loads(baseline_path.read_text())} if baseline_path.exists() else {}
    for sample in protocol['samples']:
        if sample_id and sample['id'] != sample_id:
            continue
        rows = []
        for seed in protocol['seeds']:
            path = ROOT / 'evaluation/benchmarks' / experiment / sample['id'] / str(seed) / 'record.json'
            if path.exists():
                row = json.loads(path.read_text())
                if row['status'] == 'complete':
                    rows.append(row)
        if not rows:
            continue
        sheet = Image.new('RGB', (2000, 1620), '#eeeeee')
        draw = ImageDraw.Draw(sheet)

        def tile(label, path, x, y, width, height):
            with Image.open(path) as opened:
                image = ImageOps.contain(ImageOps.exif_transpose(opened).convert('RGB'), (width - 12, height - 35))
            sheet.paste(image, (x + (width - image.width) // 2, y + 30))
            draw.text((x + 8, y + 8), label, fill='black')

        inputs = list(sample['images'].items())
        for index, (role, value) in enumerate(inputs):
            tile(role, ROOT / value['path'], index * 400, 0, 400, 710)
        comparison = []
        for row in rows:
            raw = baseline.get((sample.get('baseline_case'), row['seed']))
            if raw:
                comparison.append((f"Single reference {row['seed']}", ROOT / raw['output']))
            comparison.append((f"{sample['mode']} {row['seed']}", ROOT / row['output']))
        width = 2000 // len(comparison)
        for index, (label, path) in enumerate(comparison):
            tile(label, path, index * width, 710, width, 910)
        target = ROOT / '.local' / f"{sample['id']}_{experiment}_review.jpg"
        sheet.save(target, quality=96)
        print(target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment', required=True)
    parser.add_argument('--sample')
    args = parser.parse_args()
    render(args.experiment, args.sample)
