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
    require(b.TIMELINE_BOUNDARY_VERSION == 1, 'Wrong installed boundary compiler')
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
            pm, mode.metric_type, mode.sampling_strategy, mode.sampling_options,
            mode.granularity, mode.buffer_strategy, mode.buffer_type,
            mode.buffer_size, 65536, 1, 128, True)
        pm.run(m, 'boundary-contract-lower')

    m = prepare(True)
    plan = b.get_automatic_proton_plan(m)
    require(plan.get('timeline_boundary_version') == 1 and
            plan.get('timeline_boundary_strategy') == 'llvm_ssa_pending_machine_audit',
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
    require('proton_gpu.boundary_anchor' not in str(legacy),
            'Legacy interval path silently acquired timeline value forwarding')
    rejected = []
    for label, replacement in [('unknown', '99 : i32'), ('wrong-type', '"1"')]:
        bad_text, count = re.subn(r'proton\.timeline_boundary_version\s*=\s*1\s*:\s*i32',
                                 'proton.timeline_boundary_version = ' + replacement,
                                 original, count=1)
        require(count == 1, 'Cannot construct boundary version negative')
        path = a.output / (label + '.ttgir')
        path.write_text(bad_text)
        for name, action in [('plan', lambda: b.get_automatic_proton_plan(parse(path))),
                             ('lower', lambda: lower(parse(path)))]:
            try:
                action()
            except RuntimeError:
                rejected.append(label + '-' + name)
            else:
                raise RuntimeError('Unknown boundary ABI accepted: ' + label + '-' + name)
    (a.output / 'result.json').write_text(json.dumps({
        'status': 'compiler_dependency_contract_passed_not_machine_certified',
        'anchors': anchors, 'dependent_counter_reads': dependent_reads,
        'rejected': rejected, 'legacy_path_unchanged': True,
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
