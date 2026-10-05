"""Evaluate explicit editable/protected regions against retained inference outputs.

This is a separate spatial-constraint experiment, never a replacement of baseline
evidence. It uses local images only and does not assign visual quality scores.
"""
import argparse
import hashlib
import json
import math
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def polygon_points(polygon, size):
    if not isinstance(polygon, list) or len(polygon) < 3:
        raise ValueError('A region needs at least three polygon vertices')
    points = []
    for point in polygon:
        if len(point) != 2 or any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in point):
            raise ValueError('Region coordinates must be finite fractions from 0 to 1')
        points.append(tuple(round(v * (dimension - 1)) for v, dimension in zip(point, size)))
    return points


def build_mask(size, definition):
    feather = definition.get('feather_pixels', 0)
    if type(feather) not in (float, int) or not math.isfinite(feather) or not 0 <= feather <= 32:
        raise ValueError('Feather radius must be between 0 and 32 pixels')
    editable = definition.get('editable_polygons') or []
    if not editable:
        raise ValueError('Specify an editable garment region')
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    for polygon in editable:
        draw.polygon(polygon_points(polygon, size), fill=255)
    if feather:
        # Feather inward only: no blur leakage into protected/background pixels.
        mask = ImageChops.multiply(mask, mask.filter(ImageFilter.GaussianBlur(feather)))
    draw = ImageDraw.Draw(mask)
    for polygon in definition.get('protected_polygons', []):
        draw.polygon(polygon_points(polygon, size), fill=0)
    if mask.getextrema() == (0, 0):
        raise ValueError('No editable pixels remain after applying protection')
    if mask.getextrema()[0] != 0:
        raise ValueError('A constrained edit must leave protected pixels')
    return mask


def constrain(source, generated, mask):
    if source.size != generated.size or mask.size != source.size or mask.mode != 'L':
        raise ValueError('Source, generated image and grayscale mask must share the same canvas')
    source = source.convert('RGB')
    generated = generated.convert('RGB')
    result = Image.composite(generated, source, mask)
    difference = ImageChops.difference(result, source)
    protected = mask.point(lambda value: 255 if value == 0 else 0)
    changed_protected = ImageChops.multiply(difference, protected.convert('RGB'))
    if changed_protected.getbbox() is not None:
        raise RuntimeError('Protected source pixels changed')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', required=True)
    parser.add_argument('--regions', required=True, type=Path)
    parser.add_argument('--experiment', required=True)
    args = parser.parse_args()
    if not args.experiment or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in args.experiment):
        parser.error('Use a simple lower-case experiment name')
    cases = json.loads((ROOT / 'evaluation/cases/phase1.json').read_text())['cases']
    case = next(c for c in cases if c['id'] == args.case)
    paths = list((ROOT / 'evaluation/results').glob(args.case + '_gguf_*/records.json'))
    if len(paths) != 1:
        raise ValueError('Expected a unique canonical inference run')
    records = json.loads(paths[0].read_text())
    if len(records) != 2 or any(r['status'] != 'complete' for r in records):
        raise ValueError('Both original seeds must finish before spatial comparison')
    regions_bytes = args.regions.read_bytes()
    definition = json.loads(regions_bytes)
    source_path = ROOT / 'evaluation' / case['person_image']
    source_bytes = source_path.read_bytes()
    if definition.get('person_sha256') != digest(source_bytes):
        raise ValueError('Region annotation belongs to a different source image')
    destination = ROOT / 'evaluation/benchmarks' / args.experiment / args.case
    if destination.exists():
        raise ValueError('Existing experiment evidence must not be overwritten')
    destination.mkdir(parents=True)
    (destination / 'regions.json').write_bytes(regions_bytes)
    results = []
    for record in records:
        started = time.perf_counter()
        input_path = ROOT / record['output']
        if digest(input_path.read_bytes()) != record['output_sha256']:
            raise ValueError('Original inference output changed')
        with Image.open(input_path) as original, Image.open(source_path) as person:
            if original.size != tuple(record['output_size']):
                raise ValueError('Original output dimensions changed')
            source = person.convert('RGB').resize(original.size, Image.Resampling.LANCZOS)
            mask = build_mask(original.size, definition)
            result = constrain(source, original, mask)
        output_path = destination / f"{record['seed']}.png"
        mask_path = destination / f"{record['seed']}.mask.png"
        result.save(output_path)
        mask.save(mask_path)
        results.append({'case_id': args.case, 'seed': record['seed'], 'experiment': args.experiment,
                        'source_sha256': digest(source_bytes), 'regions_sha256': digest(regions_bytes),
                        'original_output': record['output'], 'original_output_sha256': record['output_sha256'],
                        'output': str(output_path.relative_to(ROOT)).replace('\\', '/'),
                        'output_sha256': digest(output_path.read_bytes()), 'mask_sha256': digest(mask_path.read_bytes()),
                        'output_size': list(result.size), 'protected_pixels_changed': 0,
                        'constraint_wall_seconds': round(time.perf_counter() - started, 6),
                        'generation_execution_seconds': record.get('execution_seconds'),
                        'scores': None, 'reviewer': None, 'notes': None})
    (destination / 'records.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
