"""Inspect retained ordinary/default/sparse copy and branch register inputs.

This qualification script does not compile or execute a kernel. It accepts the
original object inventory and vendor-disassembly receipt from the retained
pipeline run. Profile instructions are additionally rebound by the installed
machine-map reader. Passing this script does not by itself qualify pipeline
preservation, memory aliasing, physical overlap or measured engine busy time.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


def main():
    from flagtree.profiler.timeline_nvidia_control import _bound_functions, _branch
    from flagtree.profiler.timeline_nvidia_machine import normalized_json_instruction
    from flagtree.profiler.timeline_unit_nvidia_late import load_late_machine_map
    spec = importlib.util.spec_from_file_location(
        'native_pipeline_relations',
        Path(__file__).with_name('native_pipeline_relations.py'))
    rules = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rules)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--native-receipt', type=Path, required=True)
    parser.add_argument('--ordinary-native-json', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True)
    inputs = {}

    def read(path):
        raw = path.read_bytes()
        inputs[str(path)] = hashlib.sha256(raw).hexdigest()
        return raw

    inventory = json.loads(read(args.inventory))
    receipt = json.loads(read(args.native_receipt))
    ordinary = inventory['ordinary']
    if len(ordinary) != 1:
        raise ValueError(
            'Expected one original ordinary object across runtime K')
    ordinary = ordinary[0]
    cubin = read(Path(ordinary['cubin']))
    if hashlib.sha256(cubin).hexdigest() != ordinary['cubin_sha256']:
        raise ValueError(
            'Ordinary native bytes differ from the math-bound object')
    native = read(args.ordinary_native_json)
    matches = [c for c in receipt['cases'] if c['case'] == 'ordinary']
    if len(matches) != 1 or matches[0]['cubin_sha256'] != ordinary[
            'cubin_sha256'] or (matches[0]['native_json_sha256']
                                != hashlib.sha256(native).hexdigest()):
        raise ValueError(
            'Ordinary native JSON differs from original vendor receipt')
    records = [
        r for r in inventory['registered_math'] if r['phase'] == 'ordinary'
    ]
    if not records or any(r['hash'] != ordinary['compiled_hash'] or not all(
            r[k] for k in ('math', 'input', 'tail', 'calls'))
                          for r in records):
        raise ValueError(
            'Ordinary object is not the independently checked workload')
    doc = json.loads(native)
    functions = {
        fn['function-name']: {
            fn['start'] + i * 16: normalized_json_instruction(row)
            for i, row in enumerate(fn['sass-instructions'])
        }
        for fn in doc[1]
    }
    cases = [('ordinary', ordinary['cubin_sha256'], functions)]
    for item in inventory['profile']:
        if hashlib.sha256(read(Path(
                item['cubin']))).hexdigest() != item['cubin_sha256']:
            raise ValueError(
                'Profile native bytes differ from original inventory')
        root = Path(item['root'])
        entry = json.loads(read(root / 'index.json'))['captures'][0]
        from flagtree.profiler.timeline_capture_store import load_capture

        def retain_capture(relative, *, digest, size):
            raw = read(root / relative)
            if len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError('Capture input changed during qualification')

        capture = load_capture(root,
                               entry['capture_file'],
                               retain=retain_capture)
        if capture['owner']['binary_id'] != item['binary_id']:
            raise ValueError('Profile capture and object inventory differ')
        machine = load_late_machine_map(root, capture)
        if machine['artifacts']['cubin_sha256'] != item['cubin_sha256']:
            raise ValueError(
                'Machine map and original object inventory differ')
        base = root / 'machine' / item['binary_id']
        functions = _bound_functions(machine, read(base / 'lines.stdout'),
                                     read(base / 'json.stdout'))
        cases.append((item['case'], item['cubin_sha256'], functions))
    reports = []
    failed = False
    for label, identity, functions in cases:
        for name, body in functions.items():
            if not any(r['opcode'].startswith('HMMA') for r in body.values()):
                continue
            copies, branches = [], []
            for pc, row in body.items():
                roots, destination = None, None
                if row['opcode'].startswith('LDGSTS'):
                    roots, destination = rules.sources(row), copies
                elif row['opcode'] in ('BRA', 'BRA.U'):
                    predicate, _ = _branch(row)
                    if predicate is not None:
                        roots, destination = rules.registers(
                            predicate), branches
                elif row['opcode'] == 'EXIT' and row.get('predicate') not in (
                        None, '@PT', '@UPT', '@!PT', '@!UPT'):
                    roots, destination = rules.registers(
                        row['predicate']), branches
                if roots is None:
                    continue
                try:
                    check = rules.audit(body, pc, roots)
                except ValueError as error:
                    check = dict(status='unverified',
                                 seed_pc=pc,
                                 reason=str(error))
                destination.append(check)
                failed |= check[
                    'status'] != 'no_matrix_or_clock_result_in_native_register_cone'
            if not copies:
                raise ValueError(
                    'The original matrix function has no actual async copy')
            reports.append(
                dict(case=label,
                     cubin_sha256=identity,
                     function=name,
                     copy_inputs=copies,
                     branch_predicates=branches))
    if {r['case'] for r in reports} != {c[0] for c in cases}:
        raise ValueError('Missing a registered native matrix body')
    for path, digest in inputs.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
            raise ValueError('Retained input changed during the check')
    (args.output / 'result.json').write_text(
        json.dumps(dict(status='actual_use_native_input_cones_checked'
                        if not failed else 'unverified',
                        cases=reports,
                        input_hashes=inputs,
                        ordinary_preservation_verified=False,
                        hardware_overlap_verified=False,
                        device_executed=False,
                        application_replayed=False),
                   indent=2))
    if failed:
        raise ValueError(
            'A necessary native input cone was not independently verified')


if __name__ == '__main__':
    main()
