"""Re-export retained timeline inputs without executing the application.

Usage: python -m flagtree.profiler.timeline_reexport BUNDLE/timeline
Backend providers decode their physical records and supply independently
qualified views. The common consumer retains and validates canonical revisions.
"""
import argparse
import json
from pathlib import Path

from .timeline_events import validate_raw_batch
from .timeline_store import (bundle_path, export_lock, json_bytes, persist,
                             read_artifact, sha256)


def _json(directory, name):
    return json.loads(read_artifact(directory, name, limit=8 * 1024 * 1024))


def _original(directory, name):
    capture = _json(directory, name)
    owner = capture['owner']
    invocation = owner['invocation_id']
    if name != 'captures/' + invocation + '.input.json':
        raise ValueError('Original capture filename/identity mismatch')
    if owner.get('submission_outcome') != 'returned':
        raise ValueError('Capture did not complete a returned submission: ' +
                         invocation)
    if owner.get('readback_integrity', {}).get('status') == 'invalid':
        raise ValueError('Capture readback integrity is invalid: ' +
                         invocation)
    inputs = {}

    def retain(relative, *, digest=None, size=None):
        raw = read_artifact(directory, relative)
        actual = sha256(raw)
        if ((digest is not None and actual != digest)
                or (size is not None and
                    (type(size) is not int or len(raw) != size))):
            raise ValueError('Retained input differs from its capture: ' +
                             relative)
        inputs[relative] = dict(sha256=actual, bytes=len(raw))
        return raw

    retain(name)
    raw = retain(capture['raw_file'],
                 digest=capture['raw_sha256'],
                 size=owner['layout']['raw_bytes'])
    guard = capture.get('readback_guard')
    if guard is not None:
        retain(guard['file'], digest=guard['sha256'], size=guard['bytes'])
    for artifact in capture['metadata'].get('timeline_artifacts', []):
        retain(artifact['retained_file'], digest=artifact['sha256'])
    return capture, raw, inputs, retain


def reexport_capture(directory, original_file):
    """Decode actual bytes anew; cached canonical/view JSON cannot grant proof."""
    from .timeline_offline import offline_provider
    directory = Path(directory).resolve()
    capture, raw, sources, retain = _original(directory, original_file)
    owner = capture['owner']
    provider = offline_provider(capture)
    backend = provider.backend_name
    rules = provider.decoder_rules(capture)
    batch = validate_raw_batch(provider.decode_capture(capture, raw))
    if batch['identity']['binary_id'] != owner['binary_id']:
        raise ValueError(
            'Decoded canonical binary differs from the retained owner')
    # This revision is independent of any historical .events.json. New decoder
    # implementations can coexist without rewriting the first canonical result.
    decoder_inputs = dict(schema_version=1,
                          kind='canonical_timeline',
                          original_inputs=dict(sorted(sources.items())),
                          raw_sha256=sha256(raw),
                          canonical_sha256=sha256(json_bytes(batch)),
                          implementation_sha256={
                              Path(module.__file__).name:
                              sha256(Path(module.__file__).read_bytes())
                              for module in rules
                          })
    decoder_inputs['implementation_sha256']['timeline_reexport.py'] = sha256(
        Path(__file__).read_bytes())
    canonical_revision = sha256(json_bytes(decoder_inputs))
    canonical_base = 'derived/canonical/' + canonical_revision
    from .timeline_store import find_committed_canonical
    with export_lock(directory):
        complete_file = canonical_base + '/complete.json'
        if bundle_path(directory, complete_file).exists():
            # Later exports may add an earlier-sorting canonical alias. Keep
            # this revision's first committed storage choice on every retry.
            previous = _json(directory, complete_file)
            if previous.get('revision_id') != canonical_revision:
                raise ValueError(
                    'Committed canonical revision identity changed')
            previous_file = previous.get('canonical_file')
            reused = None
            if previous_file != canonical_base + '/events.json':
                payload = read_artifact(directory, previous_file)
                if payload != json_bytes(batch):
                    raise ValueError(
                        'Committed canonical alias differs from freshly decoded raw'
                    )
                reused = dict(file=previous_file,
                              bytes=len(payload),
                              sha256=sha256(payload))
        else:
            reused = find_committed_canonical(directory, batch)
        canonical_file = reused[
            'file'] if reused is not None else canonical_base + '/events.json'
        canonical_files = {
            canonical_base + '/inputs.json': json_bytes(decoder_inputs)
        }
        if reused is None:
            canonical_files[canonical_file] = json_bytes(batch)
        retained = [
            dict(file=name, bytes=len(payload), sha256=sha256(payload))
            for name, payload in sorted(canonical_files.items())
        ]
        if reused is not None:
            retained.append(reused)
        receipt = dict(schema_version=2,
                       revision_id=canonical_revision,
                       identity=batch['identity'],
                       canonical_file=canonical_file,
                       canonical_storage='committed_canonical_alias_v1'
                       if reused else 'standalone_json_v1',
                       files=sorted(retained, key=lambda row: row['file']))
        for name, payload in canonical_files.items():
            persist(directory, name, payload)
        persist(directory, canonical_base + '/complete.json',
                json_bytes(receipt))
    views = provider.reexport_views(directory, capture, raw, batch, sources,
                                    retain)
    return dict(invocation_id=owner['invocation_id'],
                backend=backend,
                canonical_file=canonical_file,
                canonical_revision=canonical_revision,
                status='counter_unit_only' if views['exports'] else 'raw_only',
                **views)


def reexport_bundle(directory, *, invocation_id=None):
    directory = Path(directory).resolve()
    originals = sorted(directory.glob('captures/*.input.json'))
    if not originals or len(originals) > 128:
        raise ValueError('Missing or excessive retained original captures')
    if invocation_id is not None:
        relative = 'captures/' + invocation_id + '.input.json'
        bundle_path(directory, relative)
        originals = [
            p for p in originals if str(p.relative_to(directory)) == relative
        ]
        if len(originals) != 1:
            raise ValueError('Requested invocation original is absent')
    rows = [
        reexport_capture(directory, str(p.relative_to(directory)))
        for p in originals
    ]
    # Reports have deterministic names and retain the first attempt unchanged.
    report = dict(schema_version=1, application_replayed=False, captures=rows)
    relative = 'derived/reexports/' + sha256(json_bytes(report)) + '.json'
    with export_lock(directory):
        persist(directory, relative, json_bytes(report))
    return dict(report_file=relative, **report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('timeline_directory', type=Path)
    parser.add_argument('--invocation-id')
    args = parser.parse_args()
    print(
        json.dumps(reexport_bundle(args.timeline_directory,
                                   invocation_id=args.invocation_id),
                   indent=2))


if __name__ == '__main__':
    main()
