"""Reinspect retained real cubins without device launches or application replay."""
import argparse
import hashlib
import json
from pathlib import Path


def need(value, message):
    if not value:
        raise RuntimeError(message)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    a.output.mkdir(exist_ok=False)
    from flagtree.profiler.timeline_nvidia_machine import counter_map
    roots = [Path('/workspace/chijin-timeline-r012/runs/boundary-math-v1/output'),
             Path('/workspace/chijin-timeline-r012/runs/public-outlined-v1/output')]
    by_sha = {}
    for root in roots:
        for f in root.rglob('*.cubin'):
            by_sha[hashlib.sha256(f.read_bytes()).hexdigest()] = f
    seen, rows = set(), []
    for root in roots:
        for f in root.rglob('counter-map.json'):
            original = json.loads(f.read_text())
            identity = original['artifacts']['cubin_sha256']
            if identity in seen:
                continue
            seen.add(identity)
            need(identity in by_sha, 'Actual object is not retained')
            cubin = by_sha[identity]
            ptx = cubin.with_name('4.ptx')
            need(hashlib.sha256(ptx.read_bytes()).hexdigest() == original['artifacts']['ptx_sha256'],
                 'Actual retained PTX changed')
            value = counter_map(cubin=cubin.read_bytes(), ptx=ptx.read_bytes(),
                sass_lines=f.with_name('lines.stdout').read_bytes(),
                sass_json=f.with_name('json.stdout').read_bytes(),
                binary_id=original['binary_id'],
                scope_ids=tuple(sorted({p['site_id'] for p in original['counter_pcs']})),
                expected_sm=tuple(original['expected_sm']))
            need(value['artifacts'] == original['artifacts'] and
                 value['counter_pcs'] == original['counter_pcs'],
                 'Reinspection changed exact counter inputs or locations')
            need(value['static_model_version'] == 1 and
                 not value['clock_qualified'] and not value['region_boundaries_verified'],
                 'Static provenance incorrectly grants qualification')
            need(all(len(p['direct_call_sites']) == 1 for p in value['counter_call_sites']),
                 'These development helpers require an exact direct caller')
            need(all(p['target_status'] == 'resolved' for p in value['call_sites']),
                 'A development helper target is unresolved')
            (a.output/(identity+'.json')).write_text(json.dumps(value, indent=2)+'\n')
            rows.append(dict(cubin_sha256=identity, counter_pcs=len(value['counter_pcs']),
                             call_sites=len(value['call_sites']),
                             synchronization_sites=len(value['synchronization_sites'])))
    need(len(rows) == 7 and sum(r['counter_pcs'] for r in rows) == 140,
         'The actual retained seven-object regression is incomplete')
    (a.output/'result.json').write_text(json.dumps(dict(
        status='real_retained_counter_calls_and_sync_sites_passed_not_region_certified',
        actual_math_launches=0, objects=rows), indent=2)+'\n')


if __name__ == '__main__':
    main()
