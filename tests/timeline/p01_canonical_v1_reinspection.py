"""Read all 26 actual NVIDIA v1 batches with the current common validator."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--archive', type=Path, default=Path('/workspace/chijin-timeline-r014/input/nvidia-v1-original-evidence.tgz'))
    a = p.parse_args(); a.output.mkdir(exist_ok=False)
    if hashlib.sha256(a.archive.read_bytes()).hexdigest() != '079f43e6f8169a9eebc627a9e16c5ce198beafd100aa336f76485e056c37c7b8':
        raise RuntimeError('Original NVIDIA capture archive changed')
    from flagtree.profiler.timeline_events import validate_raw_batch
    captures = records = intervals = incomplete = 0
    with tarfile.open(a.archive) as archive:
        for member in archive.getmembers():
            if not member.isfile() or not member.name.endswith('.events.json'):
                continue
            batch = json.load(archive.extractfile(member))
            if batch.get('schema_version') != 1:
                continue
            value = validate_raw_batch(batch)
            if value != batch or value['clock_status'] != 'unverified' or value['boundary_status'] != 'unverified':
                raise RuntimeError('Existing v1 data were rewritten or qualified')
            captures += 1; records += len(value['records'])
            intervals += sum(e['kind']=='interval' for e in value['events'])
            incomplete += sum(e['kind']=='incomplete' for e in value['events'])
    if (captures, records, intervals, incomplete) != (26,11456,5720,16):
        raise RuntimeError('Real v1 backward-compatibility scope is incomplete')
    (a.output/'result.json').write_text(json.dumps(dict(
        status='real_v1_batches_unchanged_under_current_common_reader',
        actual_math_launches=0, captures=captures, raw_endpoint_records=records,
        intervals=intervals, incomplete_events=incomplete), indent=2)+'\n')


if __name__ == '__main__':
    main()
