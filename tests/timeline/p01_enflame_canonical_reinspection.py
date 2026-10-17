"""Consume the three actual GCU captures using the installed common adapter.

CPU only inside server Docker. No new device call or application replay; original
math/producer evidence is bound by the original archive's SHA256.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import struct
import tarfile


def need(value, message):
    if not value:
        raise RuntimeError(message)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--archive', type=Path, default=Path('/workspace/chijin-timeline-r014/input/gcu-dynamic-original-evidence.tgz'))
    a = p.parse_args()
    a.output.mkdir(exist_ok=False)
    need(hashlib.sha256(a.archive.read_bytes()).hexdigest() ==
         'ea3fbe96cf5d8c985dd39c2d54a1d2ddaa59c229ad14c3fe85965bac97afb62b',
         'The original real GCU sample archive changed')
    from flagtree.profiler.timeline_events import stable_id, validate_raw_batch
    from flagtree.profiler.timeline_events_enflame import canonicalize_enflame_capture
    with tarfile.open(a.archive) as archive:
        def read(name):
            return archive.extractfile(name).read()
        result = json.loads(read('run-v1/output/result.json'))
        identities, rows = set(), []
        for call in result['calls']:
            k = call['steps']
            original = read('run-v1/output/k'+str(k)+'/raw/native/capture.observations.json')
            document = json.loads(original)
            need(len(document['captures']) == 1, 'Unexpected original capture count')
            capture = document['captures'][0]
            metadata = json.loads(read('run-v1/output/metadata-k'+str(k)+'.json'))
            namespace = stable_id(('retained-byte-reinspection',), 'capture', hashlib.sha256(original).hexdigest())
            batch = canonicalize_enflame_capture(capture, compiler_metadata=metadata, capture_id=namespace)
            validate_raw_batch(batch)
            raw = base64.b64decode(capture['raw_base64'], validate=True)
            need(batch['schema_version'] == 2 and batch['complete'] and
                 batch['raw_artifact']['sha256'] == capture['raw_sha256'] and
                 len(batch['events']) == call['events'] and len(batch['records']) == 2*call['events'],
                 'Common conversion lost actual pairs or provenance')
            for record in batch['records']:
                need(record['length'] == 8 and struct.unpack_from('<Q', raw, record['offset'])[0] == record['tick'],
                     'Canonical tick does not point to its actual raw field')
            keys = {row['id'] for field in ['records','events','observers'] for row in batch[field]}
            need(identities.isdisjoint(keys), 'Export-local IDs aliased owning captures')
            identities.update(keys)
            observer = batch['observers'][0]
            need(observer['kind'] == 'enflame.work_item' and observer['timer_bits'] == 46 and
                 observer['record_order'] == 'paired_endpoints' and
                 observer['dropped_records'] == observer['filtered_records'] == observer['overwritten_records'] == 0,
                 'GCU actor/loss semantics were replaced by NVIDIA assumptions')
            need(batch['clock_status'] == batch['boundary_status'] == 'unverified' and
                 all(e['iteration_id'] is None for e in batch['events']), 'Unearned timing/iteration qualification')
            path = a.output/('k'+str(k)+'.canonical.json')
            path.write_text(json.dumps(batch, indent=2)+'\n')
            rows.append(dict(steps=k, events=len(batch['events']), endpoint_references=len(batch['records']),
                             raw_sha256=batch['raw_artifact']['sha256'],
                             canonical_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    need(sum(r['events'] for r in rows) == 42, 'Actual three-capture scope incomplete')
    (a.output/'result.json').write_text(json.dumps(dict(
        status='actual_gcu_raw_pairs_consumed_by_common_contract_not_full_P01',
        actual_math_launches=0, captures=rows,
        limits=['Original producer is the advanced API; default timeline integration is still required.',
                'No clock/region/native-engine/async or Perfetto qualification.']), indent=2)+'\n')


if __name__ == '__main__':
    main()
