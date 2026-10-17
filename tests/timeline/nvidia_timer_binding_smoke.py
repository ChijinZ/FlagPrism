"""Installed native timer contract smoke, using actual ordinary-kernel TTGIR.

CPU compiler validation only: no claim of device intervals or async/P01 passage.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ir', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    import triton
    import flagtree.profiler as profiler
    from flagtree.profiler.native import compiler_binding, runtime_binding
    from triton._C import libtriton
    from triton._C.libtriton import ir, nvidia

    prefix = Path(sys.prefix).resolve()
    module_paths = {
        'triton': triton.__file__, 'profiler': profiler.__file__,
        'compiler': libtriton.__file__, 'runtime': runtime_binding().__file__,
    }
    for name, filename in module_paths.items():
        require(Path(filename).resolve().is_relative_to(prefix),
                'Module fell back outside the new installation: ' + name)
    binding = compiler_binding()
    require(binding.TIMELINE_TIMER_VERSION == 1, 'New native timer is absent')
    require(binding.TIMELINE_RECORD_VERSION == 2, 'New native record is absent')
    require(binding.TIMELINE_STORAGE_VERSION == 1, 'Compact native storage is absent')
    context = ir.context()
    ir.load_dialects(context)
    nvidia.load_dialects(context)
    binding.load_dialects(context)

    def parse(path):
        module = ir.parse_mlir_module(str(path), context)
        module.context = context
        return module

    def transform(timeline):
        module = parse(args.ir)
        pm = ir.pass_manager(context)
        binding.add_automatic_proton_scopes(pm, 8, False, timeline)
        pm.run(module, 'timeline-native-contract-smoke')
        plan = binding.get_automatic_proton_plan(module)
        return module, plan

    module, plan = transform(True)
    require(plan['timeline_timer'] == 'nvidia.globaltimer.ns',
            'Compiler omitted the selected timer identity')
    require(plan['timeline_getter_bits'] == 64 and
            plan['timeline_record_clock_bits'] == 64 and
            plan['timeline_record_version'] == 2 and
            plan['timeline_record_bytes'] == 16,
            'Timeline v2 did not preserve the complete 64-bit timer')
    require(plan['timeline_timer_version'] == 1 and plan['inventory'],
            'Compiler failed to retain its versioned actual inventory')
    require(binding.TIMELINE_PLAN_VERSION == 1 and
            plan['timeline_plan_version'] == 1,
            'Native timeline planner version missing')
    async_sites = [row for row in plan['inventory']
                   if row.get('timeline_mechanism')]
    require(len(async_sites) == plan['timeline_async_boundary_count'] and
            all(row['selected'] for row in async_sites),
            'Required async boundaries were silently excluded')
    require(any(row.get('timeline_wait_pending') == 2 for row in async_sites),
            'Actual ordinary partial-wait coverage metadata was lost')
    require(plan.get('timeline_storage_version') == 1 and
            plan.get('timeline_storage_policy') == 'compact_selected_programs' and
            plan.get('timeline_default_program_selection') == 'runtime_first_last',
            'Compact storage capability was not exported')
    _, legacy = transform(False)
    require('timeline_timer' not in legacy,
            'Legacy source intervals silently changed their clock')
    rejected = []
    for name, budget, census, timeline in [
            ('census-is-not-time', 8, True, True),
            ('zero-site-budget', 0, False, True),
            ('excessive-site-budget', 129, False, True)]:
        try:
            binding.add_automatic_proton_scopes(
                ir.pass_manager(context), budget, census, timeline)
        except ValueError:
            rejected.append(name)
        else:
            raise RuntimeError('Invalid native timer request accepted: ' + name)
    text, count = re.subn(
        r'(proton\.timeline_timer_version\s*=\s*)1(\s*:\s*i32)',
        r'\g<1>2\g<2>', str(module), count=1)
    require(count == 1, 'Cannot construct the stale-version negative')
    stale = args.output / 'stale-version.ttgir'
    stale.write_text(text)
    try:
        binding.get_automatic_proton_plan(parse(stale))
    except RuntimeError:
        rejected.append('unknown-timer-version')
    else:
        raise RuntimeError('Unknown timer metadata version was accepted')
    bad_record, count = re.subn(
        r'(proton\.timeline_record_version\s*=\s*)2(\s*:\s*i32)',
        r'\g<1>99\g<2>', str(module), count=1)
    require(count == 1, 'Cannot construct the unknown-record negative')
    bad_record_file = args.output / 'unknown-record.ttgir'
    bad_record_file.write_text(bad_record)
    try:
        binding.get_automatic_proton_plan(parse(bad_record_file))
    except RuntimeError:
        rejected.append('unknown-record-version')
    else:
        raise RuntimeError('Unknown record version was accepted')
    unknown_plan, count = re.subn(
        r'(proton\.timeline_plan_version\s*=\s*)1(\s*:\s*i32)',
        r'\g<1>99\g<2>', str(module), count=1)
    require(count == 1, 'Cannot construct unknown-plan negative')
    unknown_plan_file = args.output / 'unknown-plan.ttgir'
    unknown_plan_file.write_text(unknown_plan)
    try:
        binding.get_automatic_proton_plan(parse(unknown_plan_file))
    except RuntimeError:
        rejected.append('unknown-plan-version')
    else:
        raise RuntimeError('Unknown timeline plan version was accepted')
    from flagtree.profiler.mode import Default
    for name, max_shared, clock64 in [
            ('explicit-capacity-exceeds-shared', 1024, True),
            ('timeline-cannot-use-clock32', 65536, False)]:
        bad_module, _ = transform(True)
        mode = Default(buffer_size=32768)
        pm = ir.pass_manager(context)
        binding.add_convert_proton_to_protongpu(
            pm, mode.metric_type, mode.sampling_strategy, mode.sampling_options,
            mode.granularity, mode.buffer_strategy, mode.buffer_type,
            mode.buffer_size, max_shared, 1, 128, clock64)
        try:
            pm.run(bad_module, 'timeline-capacity-negative')
        except RuntimeError:
            rejected.append(name)
        else:
            raise RuntimeError('Invalid timeline lowering was accepted: ' + name)
    for name, selection in [('empty-compact-selection', []),
                            ('duplicate-compact-selection', [0, 0])]:
        bad_module, _ = transform(True)
        mode = Default(buffer_size=32768)
        pm = ir.pass_manager(context)
        binding.add_select_proton_programs(pm, selection)
        binding.add_convert_proton_to_protongpu(
            pm, mode.metric_type, mode.sampling_strategy, mode.sampling_options,
            mode.granularity, mode.buffer_strategy, mode.buffer_type,
            mode.buffer_size, 65536, 1, 128, True)
        try:
            pm.run(bad_module, 'timeline-storage-negative')
        except RuntimeError:
            rejected.append(name)
        else:
            raise RuntimeError('Invalid compact selection accepted: ' + name)
    bad_storage, count = re.subn(
        r'(proton\.timeline_storage_version\s*=\s*)1(\s*:\s*i32)',
        r'\g<1>99\g<2>', str(module), count=1)
    require(count == 1, 'Cannot construct unknown-storage negative')
    bad_storage_file = args.output / 'unknown-storage.ttgir'
    bad_storage_file.write_text(bad_storage)
    try:
        binding.get_automatic_proton_plan(parse(bad_storage_file))
    except RuntimeError:
        rejected.append('unknown-storage-version')
    else:
        raise RuntimeError('Unknown storage metadata was accepted')
    (args.output / 'timeline-plan.json').write_text(json.dumps(plan, indent=2))
    (args.output / 'legacy-plan.json').write_text(json.dumps(legacy, indent=2))
    (args.output / 'timeline.ttgir').write_text(str(module))
    (args.output / 'result.json').write_text(json.dumps({
        'status': 'installed_native_contract_passed_not_device_qualified',
        'optimized_python': bool(sys.flags.optimize),
        'module_paths': module_paths,
        'module_sha256': {name: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                          for name, path in module_paths.items()},
        'input_ttgir_sha256': hashlib.sha256(args.ir.read_bytes()).hexdigest(),
        'rejected': rejected, 'device_work': False,
        'limits': ['No final LLVM/ISA getter-order verification yet',
                   'No new automatic timeline/Perfetto/P01 qualification yet'],
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
