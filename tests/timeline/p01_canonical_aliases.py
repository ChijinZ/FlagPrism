"""Compare retained canonical aliases with fresh decoding of real NVIDIA raw."""
import argparse
import copy
import hashlib
import json
from pathlib import Path


def run(timeline, output, *, require_alias):
    from flagtree.profiler.timeline_events_nvidia_late import canonicalize_late_capture
    from flagtree.profiler import timeline_store as store
    output.mkdir(parents=True)
    before = {
        str(f): hashlib.sha256(f.read_bytes()).hexdigest()
        for f in timeline.rglob('*') if f.is_file()
    }
    reports = []
    for item in json.loads((timeline / 'index.json').read_text())['captures']:
        capture = json.loads((timeline / item['capture_file']).read_text())
        raw = store.read_artifact(timeline, capture['raw_file'])
        fresh = canonicalize_late_capture(raw,
                                          owner=capture['owner'],
                                          metadata=capture['metadata'])
        with store.export_lock(timeline):
            alias = store.find_committed_canonical(timeline, fresh)
            if alias is None or store.read_artifact(
                    timeline, alias['file']) != store.json_bytes(fresh):
                raise RuntimeError(
                    'No exact committed canonical for freshly decoded raw')
            for field in ('identity', 'tick'):
                changed = copy.deepcopy(fresh)
                if field == 'identity':
                    changed['identity']['invocation_id'] += '-different'
                else:
                    changed['records'][0]['tick'] += 1
                if store.find_committed_canonical(timeline,
                                                  changed) is not None:
                    raise RuntimeError(
                        'Changed canonical incorrectly reused: ' + field)
        if require_alias:
            storage = capture.get('events_storage') or {}
            if storage != dict(
                    kind='committed_canonical_alias_v1', **
                    alias) or capture['events_file'] != alias['file']:
                raise RuntimeError(
                    'Default capture did not retain the verified canonical alias'
                )
            old = Path('captures') / (capture['owner']['invocation_id'] +
                                      '.late-events.json')
            if (timeline / old).exists():
                raise RuntimeError(
                    'Default capture retained a redundant canonical sidecar')
        reports.append(
            dict(identity=fresh['identity'],
                 alias=alias,
                 different_identity_and_tick_rejected=True))
    after = {
        str(f): hashlib.sha256(f.read_bytes()).hexdigest()
        for f in timeline.rglob('*') if f.is_file()
    }
    if before != after:
        raise RuntimeError('Original capture bytes changed')
    if not reports:
        raise RuntimeError('No real captures checked')
    result = dict(status='fresh_raw_canonical_aliases_checked',
                  checks=reports,
                  original_files_unchanged=len(before),
                  application_replayed=False)
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(captures=len(reports), require_alias=require_alias)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--require-alias', action='store_true')
    args = parser.parse_args()
    run(args.timeline, args.output, require_alias=args.require_alias)


if __name__ == '__main__':
    main()
