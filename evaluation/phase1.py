"""Offline Phase 1 admission and scoring checks; no production backend."""
import argparse
import json
from collections import Counter
from pathlib import Path

CATEGORIES = ('shirt', 'hoodie', 'jacket', 'coat')
SEEDS = (2026093001, 2026093002)
FLOORS = {'identity': 2, 'body_pose': 2, 'garment_transfer': 2, 'background_lighting': 1, 'artifacts': 1}


def admission(manifest, root):
    errors = []
    cases = manifest.get('cases', [])
    if manifest.get('seeds') != list(SEEDS):
        errors.append('The two locked seeds must be used.')
    if Counter(case.get('category') for case in cases) != Counter(dict.fromkeys(CATEGORIES, 5)):
        errors.append('Exactly five pairs per category are required.')
    ids = [case.get('id') for case in cases]
    if any(not value for value in ids) or len(set(ids)) != len(ids):
        errors.append('Case IDs must be present and unique.')
    for case in cases:
        for field in ('person_image', 'garment_image'):
            value = case.get(field)
            if not value or not (root / value).is_file():
                errors.append(f"{case.get('id')}: missing {field}")
        rights = case.get('asset_rights') or {}
        for role in ('person', 'garment'):
            if not rights.get(role):
                errors.append(f"{case.get('id')}: missing {role} consent/license record")
        if not case.get('garment_features'):
            errors.append(f"{case.get('id')}: specify visible reference garment features before scoring")
    if not manifest.get('coverage_review'):
        errors.append('Input diversity/pose/pattern coverage has not been reviewed.')
    return errors


def summarize(manifest, records):
    expected = {(case['id'], seed): case['category'] for case in manifest['cases'] for seed in manifest['seeds']}
    counts = {category: {'expected': 10, 'recorded': 0, 'scored': 0, 'failed': 0, 'passed': 0} for category in CATEGORIES}
    problems = []
    seen = set()
    for record in records:
        key = (record.get('case_id'), record.get('seed'))
        if key not in expected or key in seen:
            raise ValueError(f'Unexpected or duplicate result: {key}')
        seen.add(key)
        category = expected[key]
        if record.get('category') != category:
            raise ValueError(f'Wrong category for {key}')
        counts[category]['recorded'] += 1
        if record.get('status') == 'failed':
            counts[category]['failed'] += 1
            if not record.get('error'):
                problems.append(f'{key}: failed run has no error evidence')
            continue
        if record.get('status') != 'complete':
            problems.append(f'{key}: run is not complete or failed')
            continue
        scores = record.get('scores') or {}
        if set(scores) != set(FLOORS) or any(type(value) is not int or value not in (0, 1, 2) for value in scores.values()):
            problems.append(f'{key}: all five integer scores are required')
            continue
        evidence_fields = ('output', 'prompt', 'workflow_sha256', 'input_hashes', 'reviewer', 'notes')
        if any(record.get(field) is None or record.get(field) == '' for field in evidence_fields):
            problems.append(f'{key}: generation/review evidence is incomplete')
            continue
        if record.get('execution_seconds') is None and record.get('recovery_evidence', {}).get('kind') != 'png_embedded_graph':
            problems.append(f'{key}: missing execution timing without documented output recovery')
            continue
        hashes = record['input_hashes']
        if not isinstance(hashes, dict) or not hashes.get('person') or not hashes.get('garment'):
            problems.append(f'{key}: both input hashes are required')
            continue
        counts[category]['scored'] += 1
        if all(scores[name] >= floor for name, floor in FLOORS.items()):
            counts[category]['passed'] += 1
    recorded = sum(row['recorded'] for row in counts.values())
    scored = sum(row['scored'] for row in counts.values())
    failed = sum(row['failed'] for row in counts.values())
    passed = sum(row['passed'] for row in counts.values())
    terminal_and_reviewed = recorded == 40 and scored + failed == 40 and not problems
    gate = terminal_and_reviewed and passed >= 32 and all(row['passed'] >= 8 for row in counts.values())
    return {'status': 'passed' if gate else ('failed' if terminal_and_reviewed else 'incomplete'), 'expected': 40, 'recorded': recorded, 'scored': scored, 'inference_failures': failed, 'passed': passed, 'categories': counts, 'problems': problems, 'quality_gate_passed': gate}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('preflight', 'summarize'))
    parser.add_argument('--manifest', type=Path, default=Path(__file__).parent / 'cases/phase1.json')
    parser.add_argument('--records', type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    errors = admission(manifest, args.manifest.parent.parent)
    if errors:
        print(json.dumps({'status': 'not_ready', 'errors': errors}, indent=2))
        return 1
    if args.command == 'preflight':
        print('Ready: 20 pairs, 40 planned runs. Visually check input suitability before inference.')
        return 0
    if args.records is None:
        parser.error('--records is required for summarize')
    summary = summarize(manifest, json.loads(args.records.read_text(encoding='utf-8')))
    print(json.dumps(summary, indent=2))
    return 0 if summary['quality_gate_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
