"""Actual public dtype captures must retain automatic clock call provenance."""
import argparse
import json
from pathlib import Path
import runpy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    target = Path(__file__).with_name('p01_nvidia_boundary_math.py')
    # The existing real-math driver executes exactly its five requested calls.
    runpy.run_path(str(target), run_name='__main__')
    root = args.output / 'public/timeline'
    index = json.loads((root / 'index.json').read_text())
    calls = counters = 0
    for row in index['captures']:
        from flagtree.profiler.timeline_capture_store import load_capture_file
        capture = load_capture_file(root / row['capture_file'])
        proof = json.loads(
            (root / capture['machine_counter_mapping']['counter_map_file']
             ).read_text())
        if (proof.get('static_model_version') != 1 or proof['clock_qualified']
                or proof['region_boundaries_verified']
                or not all(p['direct_call_sites']
                           for p in proof['counter_call_sites'])):
            raise RuntimeError(
                'Public capture lost call provenance or overclaims qualification'
            )
        if not all(c['target_status'] == 'resolved'
                   for c in proof['call_sites']):
            raise RuntimeError(
                'These actual dtype helpers have an unresolved direct target')
        calls += len(proof['call_sites'])
        counters += len(proof['counter_pcs'])
    (args.output / 'call-model-result.json').write_text(
        json.dumps(dict(
            status='public_real_math_and_static_call_provenance_passed',
            actual_math_launches=5,
            captures=len(index['captures']),
            static_call_references=calls,
            static_getter_references=counters,
            region_boundaries_verified=False,
            clock_qualified=False),
                   indent=2) + '\n')


if __name__ == '__main__':
    main()
