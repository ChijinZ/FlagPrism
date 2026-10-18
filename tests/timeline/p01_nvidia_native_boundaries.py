"""Actual retained late objects plus negative conditional boundary fixtures."""
import argparse
import copy
import hashlib
import json
from pathlib import Path


def run(timeline, output, *, units, boundaries, native_control):
    output.mkdir(parents=True)
    originals = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in timeline.rglob('*') if p.is_file()
    }
    reports = []
    checks = 0

    def reject(call):
        nonlocal checks
        try:
            call()
        except (ValueError, KeyError, TypeError):
            checks += 1
        else:
            raise RuntimeError('Invalid native boundary fixture accepted')

    index = json.loads((timeline / 'index.json').read_text())
    for item in index['captures']:
        capture = json.loads((timeline / item['capture_file']).read_text())
        machine = units.load_late_machine_map(timeline, capture)
        base = timeline / 'machine' / capture['owner']['binary_id']
        lines = (base / 'lines.stdout').read_bytes()
        native = (base / 'json.stdout').read_bytes()
        ptx_rows = [
            r for r in capture['metadata']['timeline_artifacts']
            if r['retained_file'].endswith('.ptx')
        ]
        if len(ptx_rows) != 1:
            raise RuntimeError('Ambiguous retained PTX')
        ptx = (timeline / ptx_rows[0]['retained_file']).read_bytes()
        args = dict(machine_map=machine,
                    sass_lines=lines,
                    sass_json=native,
                    ptx=ptx,
                    plan=capture['owner']['plan'])
        report = boundaries.derive_native_boundaries(**args)
        sites = report['sites']
        if not sites or any(
                r['status'] != 'native_boundary_control_order_checked'
                for r in sites):
            raise RuntimeError('Actual native boundary rejected: ' +
                               str(report))
        if {r['kind'] for r in sites} != set(boundaries._KINDS):
            raise RuntimeError('Actual sample lacks a native operation family')
        functions = native_control._bound_functions(machine, lines, native)
        for site in sites:
            body = functions[site['function']]
            row = body[site['native_pc']]
            bad = dict(row, predicate='@P0')
            reject(lambda: boundaries._matches(site['kind'], site[
                'ptx_operation'], bad))
            bad = dict(row, opcode='NOP')
            reject(lambda: boundaries._matches(site['kind'], site[
                'ptx_operation'], bad))
            reject(
                lambda: boundaries._matches(site['kind'], 'bar.sync1;', row))
            first = site['begin_reader_pc'] if site[
                'begin_reader_pc'] is not None else site['native_pc']
            last = site['end_reader_pc']
            reject(lambda: boundaries._straight_path(body, last, first))
            # A branch may skip the native operation, even if both readers exist.
            changed = copy.deepcopy(body)
            changed[first] = dict(opcode='BRA',
                                  operands=hex(last),
                                  predicate='@P0')
            reject(lambda: boundaries._straight_path(changed, first, last))
            if first + 16 < last:
                changed = copy.deepcopy(body)
                outside = min(changed)
                if outside < first:
                    changed[outside] = dict(opcode='BRA',
                                            operands=hex(first + 16),
                                            predicate='@P0')
                    reject(lambda: boundaries._straight_path(
                        changed, first, last))
        reject(lambda: boundaries.derive_native_boundaries(**dict(
            args, ptx=ptx + b'\n')))
        reject(lambda: boundaries.derive_native_boundaries(**dict(
            args, sass_lines=lines + b'\n')))
        bad = copy.deepcopy(machine)
        bad['counter_pcs'].append(copy.deepcopy(bad['counter_pcs'][0]))
        reject(lambda: boundaries.derive_native_boundaries(**dict(
            args, machine_map=bad)))
        bad = copy.deepcopy(machine)
        bad['counter_pcs'][0]['annotation_line'] += 1
        reject(lambda: boundaries.derive_native_boundaries(**dict(
            args, machine_map=bad)))
        if any(report[key] is not False
               for key in ('record_value_provenance_verified',
                           'participation_verified', 'source_region_qualified',
                           'clock_qualified', 'hardware_overlap_verified',
                           'time_flows_qualified')):
            raise RuntimeError('Conditional order promoted unrelated rights')
        reports.append(report)
    if originals != {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in timeline.rglob('*') if p.is_file()
    }:
        raise RuntimeError('Retained actual source artifacts changed')
    result = dict(captures=len(reports),
                  negative_checks=checks,
                  reports=reports,
                  original_files_unchanged=len(originals))
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return dict(captures=len(reports),
                negative_checks=checks,
                sites=[len(r['sites']) for r in reports])


def main():
    from flagtree.profiler import timeline_unit_nvidia_late as units
    from flagtree.profiler import timeline_nvidia_late_boundaries as boundaries
    from flagtree.profiler import timeline_nvidia_control as native_control
    parser = argparse.ArgumentParser()
    parser.add_argument('--timeline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            run(args.timeline,
                args.output,
                units=units,
                boundaries=boundaries,
                native_control=native_control)))


if __name__ == '__main__':
    main()
