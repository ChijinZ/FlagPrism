"""Actual native origin mapping and semantic corruption checks, without replay.

--fixture accepts SDK-generated CPU objects; --timeline accepts real captures.
Neither mode executes a device or compiles a kernel.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import tempfile


def run(args):
    from flagtree.profiler import timeline_nvidia_operation_origins as origins
    from flagtree.profiler import timeline_unit_nvidia_late as units
    from flagtree.profiler.timeline_nvidia_machine import counter_map
    from flagtree.profiler.timeline_nvidia_late_boundaries import derive_native_boundaries
    args.output.mkdir(parents=True)
    cases = []
    if args.fixture is not None:
        root = args.fixture
        plan = json.loads((root / 'manifest.json').read_text())
        cubin = (root / 'marked.cubin').read_bytes()
        plan['binary_id'] = hashlib.sha256(cubin).hexdigest()
        ptx = (root / 'marked.ptx').read_bytes()
        text, native = (root / 'ptx-lines.stdout').read_bytes(), (
            root / 'json.stdout').read_bytes()
        machine = counter_map(cubin=cubin,
                              ptx=ptx,
                              sass_lines=text,
                              sass_json=native,
                              binary_id=plan['binary_id'],
                              scope_ids=tuple(s['site_id']
                                              for s in plan['sites']),
                              expected_sm=(12, 0),
                              marker_version=1,
                              marker_flavor='late-v1',
                              expected_phases=units.late_expected_phases(plan))
        cases.append((machine, plan, ptx, text, native,
                      (root / 'source-lines.stdout').read_bytes()))
    else:
        root = args.timeline
        for entry in json.loads((root / 'index.json').read_text())['captures']:
            from flagtree.profiler.timeline_capture_store import load_capture_file
            capture = load_capture_file(root / entry['capture_file'])
            machine = units.load_late_machine_map(root, capture)
            base = root / 'machine' / capture['owner']['binary_id']
            ptxs = [
                r for r in capture['metadata']['timeline_artifacts']
                if r['retained_file'].endswith('.ptx')
            ]
            if len(ptxs) != 1:
                raise RuntimeError('Ambiguous actual PTX')
            cases.append((machine, capture['owner']['plan'],
                          (root / ptxs[0]['retained_file']).read_bytes(),
                          (base / 'lines.stdout').read_bytes(),
                          (base / 'json.stdout').read_bytes(),
                          (base / 'source-lines.stdout').read_bytes()))
    results, rejected = [], []

    def reject(name, callback):
        try:
            callback()
        except (ValueError, KeyError, TypeError):
            rejected.append(name)
        else:
            raise RuntimeError('Invalid origin mapping accepted: ' + name)

    for machine, plan, ptx, text, native, source in cases:
        inputs = dict(machine_map=machine,
                      source_lines=source,
                      sass_json=native,
                      plan=plan)
        report = origins.derive_operation_origins(**inputs)
        if not any(r['locations'] for r in report['origins']):
            raise RuntimeError('No actual native origin locations')
        boundaries = derive_native_boundaries(machine_map=machine,
                                              sass_lines=text,
                                              sass_json=native,
                                              ptx=ptx,
                                              plan=plan)['matrix_issue_sites']
        matrix = origins.matrix_member_locations(plan, boundaries, report)
        if any(r['status'] != 'matrix_member_native_locations_checked'
               for r in matrix):
            raise RuntimeError(
                'Actual LLVM matrix member/native association failed: ' +
                repr(matrix))
        if report['source_regions_qualified'] or report[
                'hardware_busy_qualified']:
            raise RuntimeError(
                'Debug source positions gained unrelated timing rights')
        wrong = copy.deepcopy(plan)
        markers = [
            m['native_origin_marker'] for s in wrong['sites']
            for m in s['members'] if m['native_origin_marker']['status'] ==
            'compiler_location_assigned'
        ]
        if len(markers) < 2:
            raise RuntimeError('Actual multiple-origin case missing')
        markers[1]['line'] = markers[0]['line']
        reject(
            'duplicate_origin_id', lambda: origins.derive_operation_origins(
                **dict(inputs, plan=wrong)))
        wrong_origins = dict(report, binary_id='0' * 64)
        reject(
            'different_matrix_origin_binary', lambda: origins.
            matrix_member_locations(plan, boundaries, wrong_origins))
        wrong = dict(plan, binary_id='0' * 64)
        reject(
            'different_binary', lambda: origins.derive_operation_origins(
                **dict(inputs, plan=wrong)))
        unknown = max(r['origin_line'] for r in report['origins']) + 1
        changed = re.sub(
            rb'(//## File "(?:\./)?__flagprism_native_origin_v1__", line )[1-9][0-9]*',
            lambda m: m[1] + str(unknown).encode(),
            source,
            count=1)
        if changed == source:
            raise RuntimeError('Actual source-origin annotation missing')
        reject(
            'unknown_native_origin', lambda: origins.derive_operation_origins(
                **dict(inputs, source_lines=changed)))
        missing = origins.derive_operation_origins(
            **dict(inputs,
                   source_lines=source.replace(origins.MARKER_FILE.encode(),
                                               b'missing_origin_file')))
        if not missing['missing_origin_lines'] or any(
                r['locations'] for r in missing['origins']):
            raise RuntimeError('Missing source locations were fabricated')
        if matrix:
            if any(r['status'] != 'unverified'
                   for r in origins.matrix_member_locations(
                       plan, boundaries, missing)):
                raise RuntimeError(
                    'Missing LLVM origin gained matrix identity')
            wrong = copy.deepcopy(plan)
            next(
                s for s in wrong['sites']
                if s['kind'] == 'matrix_issue_bracket'
            )['members'][0]['native_operation'] = 'different LLVM operation'
            if origins.matrix_member_locations(
                    wrong, boundaries, report)[0]['status'] != 'unverified':
                raise RuntimeError('Wrong LLVM member family accepted')
        # Exercise only retained sidecar reads: these owned fixtures use the
        # actual object outputs above and never modify the original capture.
        with tempfile.TemporaryDirectory(
                prefix='flagprism-origin-reader-') as tmp:
            directory = Path(tmp)
            base = directory / 'machine' / machine['binary_id']
            base.mkdir(parents=True)
            saved = dict(report,
                         tool_sha256='a' * 64,
                         origins=[],
                         source_regions_qualified=True)
            (base / 'operation-origins.json').write_text(json.dumps(saved))
            (base / 'counter-map.json').write_text(
                json.dumps(dict(tool_sha256='a' * 64)))
            (base / 'json.stdout').write_bytes(native)
            (base / 'source-lines.stdout').write_bytes(source)
            capture = dict(owner=dict(plan=plan))
            loaded = origins.load_operation_origins(directory, capture,
                                                    machine, boundaries)
            if loaded.get('origins') != report['origins'] or loaded[
                    'source_regions_qualified']:
                raise RuntimeError(
                    'Offline reader trusted saved qualification')
            for name, change in [('source_hash',
                                  dict(source_lines_sha256='0' * 64)),
                                 ('tool_hash', dict(tool_sha256='b' * 64))]:
                (base / 'operation-origins.json').write_text(
                    json.dumps(dict(saved, **change)))
                loaded = origins.load_operation_origins(
                    directory, capture, machine, boundaries)
                if loaded['status'] != 'unverified_native_operation_origins':
                    raise RuntimeError('Offline reader accepted corrupt ' +
                                       name)
                rejected.append('offline_' + name)
            (base / 'operation-origins.json').write_text(json.dumps(saved))
            for name in ['operation-origins.json', 'counter-map.json']:
                path = base / name
                original = path.read_bytes()
                for invalid in ([], None, 'invalid'):
                    path.write_text(json.dumps(invalid))
                    loaded = origins.load_operation_origins(
                        directory, capture, machine, boundaries)
                    if loaded[
                            'status'] != 'unverified_native_operation_origins':
                        raise RuntimeError(
                            'Wrong JSON type escaped isolation: ' + name)
                    rejected.append('offline_wrong_type_' + name)
                path.write_bytes(original)
            (base / 'source-lines.stdout').unlink()
            loaded = origins.load_operation_origins(directory, capture,
                                                    machine, boundaries)
            if loaded['status'] != 'unverified_native_operation_origins':
                raise RuntimeError(
                    'Offline reader invented missing source data')
            rejected.append('offline_missing_source')
        results.append(
            dict(binary_id=machine['binary_id'],
                 origins=len(report['origins']),
                 mapped_origins=sum(
                     bool(r['locations']) for r in report['origins']),
                 missing_origins=report['missing_origin_lines'],
                 matrix_members=matrix,
                 source_lines_sha256=report['source_lines_sha256']))
    (args.output / 'result.json').write_text(
        json.dumps(dict(
            status='actual_native_operation_origins_and_corruptions_passed',
            cases=results,
            rejected=rejected,
            fixture=args.fixture is not None,
            device_executed=False,
            application_replayed=False),
                   indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--timeline', type=Path)
    group.add_argument('--fixture', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
