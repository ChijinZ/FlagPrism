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
