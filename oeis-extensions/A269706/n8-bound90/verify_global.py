"""Independently check every target-89 binary corner proof."""
import argparse
import hashlib
import importlib.util
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CHECKER = None


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def initialize():
    global CHECKER
    CHECKER = load(BASE / 'n8-corner-priority/verify.py', 'binary_checker')


def check_case(record):
    idx = record['index']
    path = BASE / f'n8-binary-branch/global90/case-{idx}.json'
    if not path.exists():
        return {'case_index': idx, 'status': 'UNRESOLVED'}
    raw = path.read_bytes()
    proof = json.loads(raw)
    if proof.get('status') != 'UNSAT':
        return {'case_index': idx, 'status': 'UNRESOLVED'}
    root = {'case_index': idx, 'fixed_points': [
        [i // 64, (i // 8) % 8, i % 8] for i in record['fixed']]}
    # Corner-first assignment is equivariant under every cube symmetry.
    # A proof with fewer exclusions (including old empty-root proofs) is
    # stronger than the required refined case and may be used as well.
    corners = {64*x + 8*y + z for x in (0, 7) for y in (0, 7) for z in (0, 7)}
    root_excluded = CHECKER.indices(proof['proof_tree'][0]['excluded'])
    if not root_excluded <= corners - set(record['fixed']):
        raise ValueError('root excludes more than the canonical corner-first case')
    root['excluded_points'] = [[i // 64, (i // 8) % 8, i % 8] for i in sorted(root_excluded)]
    check = CHECKER.verify(proof, root, 89)
    digest = hashlib.sha256(raw).hexdigest()
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError('proof changed during verification')
    return {**check, 'sha256': digest, 'root_excluded_count': len(root_excluded), 'bytes': len(raw)}


def main(workers):
    corner = load(BASE / 'n8-corner-bound/verify_corner_lp.py', 'corner_checker')
    source = BASE / 'n8-corner-bound/corner-lp-result.json'
    base = corner.verify(source)
    if not base['complete'] or base['records'] != 1474 or base['expanded_corner_cases'] != 65536:
        raise ValueError('incomplete canonical corner coverage')
    records_path = source.with_suffix('.jsonl')
    records = [json.loads(line) for line in records_path.read_text().splitlines() if line.strip()]
    if len(records) != 1474 or len({r['index'] for r in records}) != 1474:
        raise ValueError('duplicate or missing corner records')
    with ProcessPoolExecutor(max_workers=workers, initializer=initialize) as pool:
        results = list(pool.map(check_case, records, chunksize=1))
    checks = [r for r in results if r['status'] == 'PASS']
    unresolved = [r['case_index'] for r in results if r['status'] != 'PASS']
    report = {'status': 'PASS' if not unresolved else 'PARTIAL',
              'global_lower_bound': 90 if not unresolved else None,
              'verified_cases': len(checks), 'total_cases': 1474,
              'nodes': sum(c['nodes'] for c in checks),
              'cases_with_root_exclusions': sum(c['root_excluded_count'] > 0 for c in checks),
              'proof_bytes': sum(c['bytes'] for c in checks),
              'source_records_sha256': hashlib.sha256(records_path.read_bytes()).hexdigest(),
              'checker_path': 'n8-corner-priority/verify.py',
              'checker_sha256': hashlib.sha256((BASE / 'n8-corner-priority/verify.py').read_bytes()).hexdigest(),
              'global_checker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'unresolved': unresolved, 'checks': checks}
    Path(__file__).with_name('verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('checks', 'unresolved')}))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=4)
    args = ap.parse_args()
    main(args.workers)
