"""Bind actual native matrix input words to fresh raw-backed generations.

Offline qualification in the NVIDIA SDK Docker; no application replay. This
checks the registered single-matrix-group loop. It is not a scheduler, alias,
physical overlap, tensor completion or source-exclusive timing certificate.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


def main():
    from flagtree.profiler.timeline_nvidia_control import _bound_functions
    from flagtree.profiler.timeline_nvidia_machine import normalized_json_instruction
    from flagtree.profiler.timeline_unit_nvidia_late import load_late_machine_map
    from flagtree.profiler.timeline_nvidia_late_boundaries import load_native_boundary_report
    from flagtree.profiler.timeline_nvidia_late_raw import decode_late_raw
    from flagtree.profiler.timeline_nvidia_late_async import derive_late_async
    from flagtree.profiler.timeline_nvidia_dependencies import load_observed_dependency_inputs
    spec = importlib.util.spec_from_file_location(
        'native_matrix_inputs',
        Path(__file__).with_name('native_matrix_inputs.py'))
    rules = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rules)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inventory', type=Path, required=True)
    p.add_argument('--native-receipt', type=Path, required=True)
    p.add_argument('--ordinary-native-json', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True)
    inputs = {}

    def read(path):
        raw = path.read_bytes()
        inputs[str(path)] = hashlib.sha256(raw).hexdigest()
        return raw

    inventory = json.loads(read(args.inventory))
    receipt = json.loads(read(args.native_receipt))
    if len(inventory['ordinary']) != 1:
        raise ValueError('Expected one original ordinary object')
    ordinary = inventory['ordinary'][0]
    raw = read(Path(ordinary['cubin']))
    native = read(args.ordinary_native_json)
    registered = [row for row in receipt['cases'] if row['case'] == 'ordinary']
    if (len(registered) != 1
            or hashlib.sha256(raw).hexdigest() != ordinary['cubin_sha256']
            or registered[0]['cubin_sha256'] != ordinary['cubin_sha256']
            or registered[0]['native_json_sha256']
            != hashlib.sha256(native).hexdigest()):
        raise ValueError('Ordinary object and original vendor receipt differ')
    math = [
        row for row in inventory['registered_math']
        if row['phase'] == 'ordinary'
    ]
    if not math or any(row['hash'] != ordinary['compiled_hash'] or not all(
            row[key] for key in ('math', 'input', 'tail', 'calls'))
                       for row in math):
        raise ValueError('Original ordinary math identity differs')
    results = []
    for function in json.loads(native)[1]:
        body = {
            function['start'] + i * 16: normalized_json_instruction(row)
            for i, row in enumerate(function['sass-instructions'])
        }
        if any(row['opcode'].startswith('HMMA') for row in body.values()):
            results.append(
                dict(case='ordinary',
                     cubin_sha256=ordinary['cubin_sha256'],
                     function=function['function-name'],
                     matrix_inputs=rules.matrix_inputs(body,
                                                       require_loop=True),
                     raw_generation_binding_verified=False))
    for item in inventory['profile']:
        root = Path(item['root'])
        entries = json.loads(read(root / 'index.json'))['captures']
        math = [
            row for row in json.loads(read(root.parent.parent / 'math.json'))
            if row['phase'] == 'profile'
        ]
        if len(entries) != len(math) or not math:
            raise ValueError(
                'Actual captures differ from registered runtime calls')
        for entry, expected in zip(entries, math):
            if not all(expected[key]
                       for key in ('math', 'input', 'tail', 'calls')):
                raise ValueError('Original profiled math failed')
            from flagtree.profiler.timeline_capture_store import load_capture

            def retain_capture(relative, *, digest, size):
                raw = read(root / relative)
                if len(raw) != size or hashlib.sha256(
                        raw).hexdigest() != digest:
                    raise ValueError(
                        'Capture input changed during qualification')

            capture = load_capture(root,
                                   entry['capture_file'],
                                   retain=retain_capture)
            raw = read(root / capture['raw_file'])
            if hashlib.sha256(raw).hexdigest() != capture['raw_sha256']:
                raise ValueError('Original raw changed')
            machine = load_late_machine_map(root, capture)
            if machine['artifacts']['cubin_sha256'] != item['cubin_sha256']:
                raise ValueError(
                    'Profile native object differs from registered inventory')
            base = root / 'machine' / item['binary_id']
            functions = _bound_functions(machine, read(base / 'lines.stdout'),
                                         read(base / 'json.stdout'))
            native = load_native_boundary_report(root, capture, machine)
            # Reuse the installed native/raw/address/payload provenance chain.
            canonical, proofs = load_observed_dependency_inputs(
                root, capture, raw)
            if canonical['identity'] != {
                    key: capture['owner'][key]
                    for key in ('capture_id', 'invocation_id', 'binary_id')
            } or not proofs:
                raise ValueError(
                    'Dependency provenance crosses invocation identity')
            decoded = decode_late_raw(
                capture['owner']['plan'],
                raw,
                slots=capture['owner']['layout']['slots'])
            facts = derive_late_async(decoded,
                                      capture['owner']['plan'],
                                      shared_bytes=capture['metadata']
                                      ['compiler_metadata']['shared'])
            if facts['status'] != 'dynamic_byte_model_consistent':
                raise ValueError('Fresh collective byte model is unavailable')
            groups = native['matrix_issue_sites']
            if len(groups) != 1 or groups[0][
                    'status'] != 'matrix_issue_control_order_checked':
                raise ValueError(
                    'Expected one checked matrix group in the registered loop')
            group = groups[0]
            associations = rules.matrix_inputs(functions[group['function']],
                                               require_loop=True)
            if {row['matrix_pc']
                    for row in associations
                } != {i['native_pc']
                      for i in group['issues']}:
                raise ValueError(
                    'Native input checks omit or cross matrix group members')
            loops = [
                loop for loop in native['native_loop_sites']
                if loop['site_id'] == group['site_id']
            ]
            if len(loops) != 1 or loops[0][
                    'status'] != 'native_iteration_control_checked' or any(
                        row['native_loop_header_pc'] != loops[0]
                        ['loop_header_pc'] for row in associations):
                raise ValueError(
                    'Matrix input association differs from checked native iteration'
                )
            sites = {}
            for site in native['sites']:
                if site['kind'] == 'shared_load_issue_bracket':
                    if site['status'] != 'native_boundary_control_order_checked':
                        raise ValueError(
                            'A shared load lacks checked native boundaries')
                    if site['function'] == group['function']:
                        sites.setdefault(site['native_pc'],
                                         []).append(site['site_id'])
            bindings = []
            for program in decoded['programs']:
                models = [
                    model for model in facts['programs']
                    if model['program'] == program['program_id']
                ]
                if len(models) != 1:
                    raise ValueError(
                        'Dynamic byte model does not bind this program')
                rows = rules.bind_generations(
                    associations, sites, group['site_id'],
                    program['observers'][0]['events'], models[0])
                if len(rows) != expected['tiles']:
                    raise ValueError(
                        'Input associations differ from original runtime trip argument'
                    )
                bindings.append(
                    dict(program=program['program_id'],
                         matrix_occurrences=rows))
            results.append(
                dict(case=item['case'],
                     binary_id=item['binary_id'],
                     invocation_id=entry['invocation_id'],
                     raw_sha256=capture['raw_sha256'],
                     expected_runtime_tiles=expected['tiles'],
                     matrix_inputs=associations,
                     programs=bindings,
                     raw_generation_binding_verified=True,
                     provenance_evidence_ids=[
                         list(proof.evidence_ids) for proof in proofs
                     ]))
    if not any(row['case'] == 'ordinary' for row in results):
        raise ValueError('Missing actual ordinary matrix function')
    for path, digest in inputs.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
            raise ValueError('An original input changed')
    (args.output / 'result.json').write_text(
        json.dumps(dict(
            status='native_matrix_input_words_and_raw_generations_checked',
            cases=results,
            input_hashes=inputs,
            device_executed=False,
            application_replayed=False,
            ordinary_preservation_verified=False,
            hardware_overlap_verified=False),
                   indent=2))


if __name__ == '__main__':
    main()
