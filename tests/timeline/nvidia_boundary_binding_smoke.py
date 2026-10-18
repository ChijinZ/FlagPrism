"""Installed compiler dependency/version contracts on real ordinary TTGIR.

This CPU compiler test runs only inside the server Docker. It does not certify
final SASS order, physical clocks or complete P01. Device math follows separately.
"""
import argparse
import json
from pathlib import Path
import re


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--ir', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(exist_ok=False)
    from triton._C.libtriton import ir, nvidia
    from flagtree.profiler.native import compiler_binding
    from flagtree.profiler.mode import Default
    b = compiler_binding()
    require(
        b.TIMELINE_BOUNDARY_VERSION == 3 and b.TIMELINE_MARKER_VERSION == 1,
        'Wrong installed boundary/marker compiler')
    context = ir.context()
    ir.load_dialects(context)
    nvidia.load_dialects(context)
    b.load_dialects(context)

    def parse(path):
        m = ir.parse_mlir_module(str(path), context)
        m.context = context
        return m

    def prepare(timeline):
        m = parse(a.ir)
        pm = ir.pass_manager(context)
        b.add_automatic_proton_scopes(pm, 8, False, timeline)
        pm.run(m, 'automatic-boundary-contract')
        return m

    def lower(m):
        mode = Default(buffer_size=32768)
        pm = ir.pass_manager(context)
        b.add_convert_proton_to_protongpu(
            pm, mode.metric_type, mode.sampling_strategy,
            mode.sampling_options, mode.granularity, mode.buffer_strategy,
            mode.buffer_type, mode.buffer_size, 65536, 1, 128, True)
        pm.run(m, 'boundary-contract-lower')

    m = prepare(True)
    plan = b.get_automatic_proton_plan(m)
    require(
        plan.get('timeline_marker_version') == 1
        and plan.get('timeline_boundary_version') == 3
        and plan.get('timeline_boundary_strategy')
        == 'runtime_zero_gated_calls_pending_region_audit',
        'Plan incorrectly describes compiler-only boundary strength')
    (a.output / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    original = str(m)
    lower(m)
    text = str(m)
    (a.output / 'dependency-lowered.ttgir').write_text(text)
    anchors = len(re.findall(r'proton_gpu\.boundary_anchor\b', text))
    dependent_reads = len(re.findall(r'proton_gpu\.read_counter\s*\(', text))
    require(anchors > 0 and dependent_reads > 0,
            'Actual ordinary source lost its compiler dependency chain')
    legacy = prepare(False)
    lower(legacy)
    require(
        'proton_gpu.boundary_anchor' not in str(legacy),
        'Legacy interval path silently acquired timeline value forwarding')
    old_text, changed = re.subn(
        r'proton\.timeline_boundary_version\s*=\s*3\s*:\s*i32',
        'proton.timeline_boundary_version = 2 : i32',
        original,
        count=1)
    require(changed == 1, 'Cannot construct explicit previous boundary IR')
    old_path = a.output / 'explicit-version-2.ttgir'
    old_path.write_text(old_text)
    old_module = parse(old_path)
    old_plan = b.get_automatic_proton_plan(old_module)
    require(
        old_plan['timeline_boundary_version'] == 2
        and old_plan['timeline_boundary_strategy']
        == 'outlined_device_calls_pending_region_audit',
        'Explicit version-2 IR lost its historical boundary strategy')
    lower(old_module)
    require('proton_gpu.boundary_anchor' in str(old_module),
            'Explicit version-2 IR lost its legacy operand anchors')
    old_record, changed = re.subn(
        r'proton\.timeline_record_version\s*=\s*3\s*:\s*i32',
        'proton.timeline_record_version = 2 : i32',
        original,
        count=1)
    require(changed == 1, 'Cannot construct explicit previous record IR')
    old_record_path = a.output / 'explicit-record-version-2.ttgir'
    old_record_path.write_text(old_record)
    old_record_module = parse(old_record_path)
    old_record_plan = b.get_automatic_proton_plan(old_record_module)
    require(
        old_record_plan['timeline_record_bytes'] == 16
        and old_record_plan['timeline_record_version'] == 2,
        'Previous record IR was silently upgraded')
    lower(old_record_module)
    require(' association ' not in str(old_record_module),
            'Previous record IR acquired a new payload')
    rejected = []
    for label, replacement in [('old-compiler', '1 : i32'),
                               ('unknown', '99 : i32'), ('wrong-type', '"1"'),
                               ('wrong-width', '3 : i64')]:
        bad_text, count = re.subn(
            r'proton\.timeline_boundary_version\s*=\s*3\s*:\s*i32',
            'proton.timeline_boundary_version = ' + replacement,
            original,
            count=1)
        require(count == 1, 'Cannot construct boundary version negative')
        path = a.output / (label + '.ttgir')
        path.write_text(bad_text)
        for name, action in [
            ('plan', lambda: b.get_automatic_proton_plan(parse(path))),
            ('lower', lambda: lower(parse(path)))
        ]:
            try:
                action()
            except RuntimeError:
                rejected.append(label + '-' + name)
            else:
                raise RuntimeError('Unknown boundary ABI accepted: ' + label +
                                   '-' + name)
    for label, replacement in [('unknown-marker', '99 : i32'),
                               ('string-marker', '"1"'),
                               ('boolean-marker', 'true')]:
        bad_text, count = re.subn(
            r'proton\.timeline_marker_version\s*=\s*1\s*:\s*i32',
            'proton.timeline_marker_version = ' + replacement,
            original,
            count=1)
        require(count == 1, 'Cannot construct marker version negative')
        path = a.output / (label + '.ttgir')
        path.write_text(bad_text)
        for name, action in [
            ('plan', lambda: b.get_automatic_proton_plan(parse(path))),
            ('lower', lambda: lower(parse(path)))
        ]:
            try:
                action()
            except RuntimeError:
                rejected.append(label + '-' + name)
            else:
                raise RuntimeError('Invalid marker ABI accepted: ' + label +
                                   '-' + name)
    require(
        'proton.timeline_site_id' in text
        and 'proton.timeline_is_start' in text,
        'Actual lowered counters lost their site/phase identities')
    (a.output / 'result.json').write_text(
        json.dumps(
            {
                'status':
                'compiler_dependency_contract_passed_not_machine_certified',
                'anchors': anchors,
                'dependent_counter_reads': dependent_reads,
                'rejected': rejected,
                'legacy_path_unchanged': True,
                'explicit_boundary_version_2_compatible': True,
            },
            indent=2) + '\n')


if __name__ == '__main__':
    main()
