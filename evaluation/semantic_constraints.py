"""Local CPU clothing-parser pilot for source protection and garment boundaries.

Model files must already exist locally at the pinned revision. This script never
uploads images, fetches weights, or enables GPU inference. Visual review remains
required; exact pixel protection does not prove a good-looking garment boundary.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageFilter

from protected_regions import constrain

ROOT = Path(__file__).resolve().parents[1]
PROTECTED_LABELS = (1, 2, 3, 11, 14, 15, 16)  # hat, hair, eyewear, face, exposed arms/hands, bag


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def semantic_mask(source_labels, generated_labels, feather=4, growth=5, *, policy='legacy', category=None):
    if policy not in ('legacy','occlusion_v2','occlusion_v3'):raise ValueError('Unknown mask policy')
    if source_labels.shape != generated_labels.shape or source_labels.ndim != 2:
        raise ValueError('Both segmentation maps must share the same image geometry')
    target_labels = (4, 7) if policy in ('occlusion_v2','occlusion_v3') and category == 'coat' else (4,)
    generated_clothing = np.isin(generated_labels, target_labels)
    if not np.any(generated_clothing) or policy == 'legacy' and not np.any(source_labels == 4):
        raise ValueError('Parser did not identify an upper garment in both images')
    # The union accommodates a changed silhouette instead of clipping to the old garment.
    editable = (source_labels == 4) | generated_clothing
    if policy in ('occlusion_v2','occlusion_v3'):
        # A coarse hair map can include old blouse pixels. Reject that ambiguous
        # mask instead of pasting old clothing over the reference garment.
        overlap_limit=.10 if policy=='occlusion_v3' else .25
        if np.count_nonzero(editable & (source_labels == 2)) > overlap_limit * np.count_nonzero(editable):
            raise ValueError('Hair segmentation overlaps too much of the garment; retain raw preview')
    mask = Image.fromarray(editable.astype(np.uint8) * 255)
    if growth:
        mask = mask.filter(ImageFilter.MaxFilter(2 * growth + 1))
    if feather:
        mask = ImageChops.multiply(mask, mask.filter(ImageFilter.GaussianBlur(feather)))
    values = np.asarray(mask).copy()
    if policy in ('occlusion_v2','occlusion_v3'):
        protected = np.isin(source_labels, (1,2,3,11))
        # Covered source arms are a legitimate new-sleeve occlusion. Preserve
        # exposed arms/hands and bags where both images identify that region.
        protected |= np.isin(source_labels, (14,15,16)) & np.isin(generated_labels, (14,15,16))
        values[protected] = 0
    else:
        values[np.isin(source_labels, PROTECTED_LABELS)] = 0
    if not np.any(values > 0) or not np.any(values == 0):
        raise ValueError('Segmentation did not leave both editable and protected regions')
    return Image.fromarray(values)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', required=True)
    parser.add_argument('--experiment', required=True)
    parser.add_argument('--source-experiment', help='Matched raw experiment; omitted means the original baseline')
    parser.add_argument('--policy', choices=('legacy','occlusion_v2','occlusion_v3'), default='legacy')
    args = parser.parse_args()
    if not args.experiment or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in args.experiment):
        parser.error('Use a simple lower-case experiment name')
    manifest = json.loads((ROOT / 'evaluation/segmentation_environment.json').read_text())
    model_dir = ROOT / '.local/models/segformer_b2_clothes'
    for file in manifest['files']:
        if digest(model_dir / file['file']) != file['sha256']:
            raise ValueError('Local segmentation model differs from pinned file hashes')
    cases = json.loads((ROOT / 'evaluation/cases/phase1.json').read_text())['cases']
    case = next(c for c in cases if c['id'] == args.case)
    source_path = ROOT / 'evaluation' / case['person_image']
    if args.source_experiment and any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in args.source_experiment):
        parser.error('Use a simple source experiment name')
    storage = ROOT / ('evaluation/benchmarks/' + args.source_experiment if args.source_experiment else 'evaluation/results')
    record_paths = list(storage.glob(args.case + '_gguf_*/records.json'))
    if len(record_paths) != 1:
        raise ValueError('Expected unique canonical generation records')
    records = json.loads(record_paths[0].read_text())
    if len(records) != 2 or any(r['status'] != 'complete' for r in records):
        raise ValueError('Wait for both original seeds before a matched spatial comparison')
    destination = ROOT / 'evaluation/benchmarks' / args.experiment / args.case
    if destination.exists():
        raise ValueError('Existing experiment evidence must not be overwritten')
    import torch
    import psutil
    from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation

    torch.set_num_threads(1)
    cold_started = time.perf_counter()
    process = psutil.Process()
    before_load_rss = process.memory_info().rss
    processor = SegformerImageProcessor.from_pretrained(model_dir, local_files_only=True)
    model = SegformerForSemanticSegmentation.from_pretrained(model_dir, local_files_only=True, use_safetensors=True).to('cpu').eval()
    cold_load_seconds = time.perf_counter() - cold_started
    model_load_rss_delta_mib = round((process.memory_info().rss - before_load_rss) / 1048576, 3)
    destination.mkdir(parents=True)
    results = []

    def segment(image):
        with torch.inference_mode():
            inputs = processor(images=image, return_tensors='pt')
            logits = model(**inputs).logits
            resized = torch.nn.functional.interpolate(logits, size=image.size[::-1], mode='bilinear', align_corners=False)
            return resized.argmax(dim=1)[0].cpu().numpy().astype(np.uint8)

    for record in records:
        started = time.perf_counter()
        original_path = ROOT / record['output']
        if digest(original_path) != record['output_sha256'] or digest(source_path) != record['input_hashes']['person']:
            raise ValueError('Source or original generation bytes changed')
        with Image.open(source_path) as person, Image.open(original_path) as generated_image:
            generated = generated_image.convert('RGB')
            source = person.convert('RGB').resize(generated.size, Image.Resampling.LANCZOS)
        source_labels = segment(source)
        generated_labels = segment(generated)
        fallback = None
        try:
            mask = semantic_mask(source_labels, generated_labels, policy=args.policy, category=case['category'])
            result = constrain(source, generated, mask)
        except ValueError as error:
            # Preserve the raw preview when the parser cannot produce a usable mask.
            # Retain this case and its visual score in the matched denominator.
            fallback = str(error)
            mask = Image.new('L', generated.size, 255)
            result = generated
        seed = record['seed']
        result_path = destination / f'{seed}.png'
        mask_path = destination / f'{seed}.mask.png'
        result.save(result_path)
        mask.save(mask_path)
        Image.fromarray(source_labels).save(destination / f'{seed}.source-labels.png')
        Image.fromarray(generated_labels).save(destination / f'{seed}.generated-labels.png')
        protected=np.asarray(mask)==0
        raw_changed=np.any(np.asarray(source)!=np.asarray(generated),axis=2)
        final_changed=np.any(np.asarray(source)!=np.asarray(result),axis=2)
        results.append({'case_id': args.case, 'seed': seed, 'experiment': args.experiment,
                        'source_experiment': args.source_experiment,
                        'constraint_applied': fallback is None, 'fallback_reason': fallback,
                        'mask_policy': args.policy,
                        'source_sha256': digest(source_path), 'original_output': record['output'],
                        'original_output_sha256': record['output_sha256'],
                        'output': str(result_path.relative_to(ROOT)).replace('\\', '/'),
                        'output_sha256': digest(result_path), 'mask_sha256': digest(mask_path),
                        'output_size': list(result.size), 'protected_pixels_changed': int(np.count_nonzero(final_changed & protected)),
                        'raw_protected_pixels_changed': int(np.count_nonzero(raw_changed & protected)),
                        'protected_region_pixels': int(np.count_nonzero(protected)),
                        'cached_label_hashes': {name:digest(destination/f'{seed}.{name}-labels.png') for name in ('source','generated')},
                        'constraint_wall_seconds': round(time.perf_counter() - started, 6),
                        'cold_model_load_seconds': round(cold_load_seconds, 6) if len(results) == 0 else None,
                        'generation_execution_seconds': record.get('execution_seconds'),
                        'model_revision': manifest['revision'], 'device': 'cpu', 'threads': 1,
                        'cpu_model_load_rss_delta_mib': model_load_rss_delta_mib,
                        'cpu_process_peak_mib': round(process.memory_info()._asdict().get('peak_wset', process.memory_info().rss) / 1048576, 3),
                        'scores': None, 'reviewer': None, 'notes': None})
        (destination / 'records.json').write_text(json.dumps(results, indent=2) + '\n')
        print(json.dumps({k: results[-1][k] for k in ('case_id', 'seed', 'constraint_wall_seconds', 'protected_pixels_changed')}), flush=True)


if __name__ == '__main__':
    main()
