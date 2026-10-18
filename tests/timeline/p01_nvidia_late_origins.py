"""Real native launch header origins and CPU-only corruption/generalization."""
import argparse
import copy
import hashlib
import json
import struct
from pathlib import Path


def run(timeline, output, *, units, origins, raws):
    output.mkdir(parents=True)
    original = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in timeline.rglob('*') if p.is_file()
    }
    rejected, reports = [], []

    def reject(name, call):
        try:
            call()
        except (ValueError, KeyError, TypeError, RecursionError) as error:
            rejected.append(dict(case=name, reason=str(error)))
        else:
            raise RuntimeError('Invalid native header origin accepted: ' +
                               name)

    reject('out_of_range_native_source_annotation',
           lambda: origins._grid_roots([''], {('entry', 9): [0]}, 'entry', {}))

    for item in json.loads((timeline / 'index.json').read_text())['captures']:
        capture = json.loads((timeline / item['capture_file']).read_text())
        machine = units.load_late_machine_map(timeline, capture)
        base = timeline / 'machine' / capture['owner']['binary_id']

        def artifact(suffix):
            return (timeline /
                    next(r['retained_file']
                         for r in capture['metadata']['timeline_artifacts']
                         if r['retained_file'].endswith(suffix))).read_bytes()

        owner = capture['owner']
        decoded = raws.decode_late_raw(
            owner['plan'], (timeline / capture['raw_file']).read_bytes(),
            slots=owner['layout']['slots'])
        inputs = dict(machine_map=machine,
                      sass_lines=(base / 'lines.stdout').read_bytes(),
                      sass_json=(base / 'json.stdout').read_bytes(),
                      ptx=artifact('.ptx'),
                      cubin=artifact('.cubin'),
                      owner=owner,
                      decoded=decoded)
        proof = origins.load_native_header_origins(timeline, capture, machine)
        if proof[
                'status'] != 'native_launch_header_origins_checked' or not proof[
                    'header_allocation_origin_verified'] or not proof[
                        'shared_symbol_header_value_origin_verified']:
            raise RuntimeError('Actual native header binding missing')
        if len(proof['rows']) != len(decoded['programs']) * owner['plan'][
                'actors'] or proof['time_flows_qualified']:
            raise RuntimeError(
                'Actual native header coverage or proof scope differs')
        reject(
            'changed_actual_cubin',
            lambda: origins.derive_header_origin_bindings(**dict(
                inputs, cubin=inputs['cubin'] + b'X')))
        reject(
            'changed_actual_ptx',
            lambda: origins.derive_header_origin_bindings(**dict(
                inputs, ptx=inputs['ptx'] + b'\n// changed\n')))
        wrong = copy.deepcopy(owner)
        wrong['plan']['block_dimensions'][0] *= 2
        reject(
            'different_compiled_block',
            lambda: origins.derive_header_origin_bindings(**dict(inputs,
                                                                 owner=wrong)))
        wrong = copy.deepcopy(owner)
        wrong['layout']['grid'][0] += 1
        reject(
            'different_actual_grid',
            lambda: origins.derive_header_origin_bindings(**dict(inputs,
                                                                 owner=wrong)))
        wrong = copy.deepcopy(capture)
        wrong['owner']['layout']['slots'][1][1] -= 1
        reject(
            'different_actual_program_slot', lambda: origins.
            load_native_header_origins(timeline, wrong, machine))
        wrong = copy.deepcopy(decoded)
        wrong['programs'][0]['observers'][0]['header_offset_bytes'] += 8
        reject(
            'different_raw_header_offset', lambda: origins.
            derive_header_origin_bindings(**dict(inputs, decoded=wrong)))
        wrong = copy.deepcopy(decoded)
        wrong['programs'][0]['observers'].pop()
        reject(
            'incomplete_actual_header_actors', lambda: origins.
            derive_header_origin_bindings(**dict(inputs, decoded=wrong)))
        wrong = copy.deepcopy(owner['plan'])
        wrong['scratch_arg'] -= 1
        function = next(
            iter(
                origins._bound_functions(machine, inputs['sass_lines'],
                                         inputs['sass_json'])))
        reject(
            'scratch_is_not_reserved_final_parameter', lambda: origins.
            _parameter_root(inputs['cubin'], inputs['ptx'], function, wrong))
        reject(
            'wrong_parameter_bank_symbol', lambda: origins.
            _parameter_bank_symbol(inputs['cubin'], 0, function))

        # Mutate only an independently located ELF metadata payload. The test
        # never executes these bytes and does not forge a new machine receipt.
        elf = inputs['cubin']
        section = origins._elf_section(elf, '.nv.info.' + function)
        position = elf.find(section)
        if position < 0 or elf.find(section, position + 1) >= 0:
            raise RuntimeError('ELF metadata mutation fixture is ambiguous')
        at, metadata_cases = 0, []
        while at < len(section):
            kind, tag, size = struct.unpack_from('<BBH', section, at)
            payload = at + 4
            if kind == 4 and tag == 0x0a:
                metadata_cases.extend([('wrong_bank_symbol', payload, '<I', 0),
                                       ('empty_bank_extent', payload + 6, '<H',
                                        0)])
            if kind == 4 and tag == 0x17 and struct.unpack_from(
                    '<H', section,
                    payload + 4)[0] == owner['plan']['scratch_arg']:
                flags = struct.unpack_from('<I', section, payload + 8)[0]
                metadata_cases.append(
                    ('wrong_scratch_width', payload + 8, '<I',
                     (flags & ((1 << 18) - 1)) | (4 << 18)))
            at += 4 + (size if kind == 4 else 0)
        if len(metadata_cases) != 3:
            raise RuntimeError(
                'Actual parameter metadata negative cases not exercised')
        for name, at, fmt, value in metadata_cases:
            changed = bytearray(elf)
            struct.pack_into(fmt, changed, position + at, value)
            reject(
                name, lambda: origins._parameter_root(bytes(changed), inputs[
                    'ptx'], function, owner['plan']))

        arithmetic = origins.derive_record_addresses(**{
            k: inputs[k]
            for k in ('machine_map', 'sass_lines', 'sass_json', 'ptx')
        },
                                                     plan=owner['plan'])
        header = arithmetic['functions'][0]['header']
        body = origins._bound_functions(machine, inputs['sass_lines'],
                                        inputs['sass_json'])[function]
        graph = origins._predecessors(body)
        wide = origins._Wide(body, graph, counter=header['value_register'])
        expression = origins._published_header_address(wide, header)
        scratch = wide.node('constant_memory_u64',
                            proof['parameter']['bank_operand'])
        lines, _ = origins._lex(inputs['ptx'].decode(), 'late-v1')
        roots = origins._grid_roots(
            lines, origins._native_lines(inputs['sass_lines'],
                                         {function: body}), function, body)
        context = origins._Context(wide,
                                   grid=owner['layout']['grid'],
                                   block=owner['plan']['block_dimensions'],
                                   program=0,
                                   actor=0,
                                   grid_inputs=roots)
        reject(
            'duplicated_pointer_root', lambda: context.pointer_offset(
                wide.add(expression, scratch), scratch))
        reject(
            'unbound_pointer_root', lambda: context.pointer_offset(
                expression, wide.node('constant_memory_u64', 'c[0x0][0x0]')))
        contexts = []
        # These extra contexts test the native arithmetic model on asymmetric
        # grids; they are CPU fixtures, not new captured device programs.
        for grid in [(3, 2, 1), (1, 3, 2)]:
            for program in range(6):
                for actor in (0, 31, 32, 127):
                    context = origins._Context(
                        wide,
                        grid=grid,
                        block=owner['plan']['block_dimensions'],
                        program=program,
                        actor=actor,
                        grid_inputs=roots)
                    for label, value in [('program', program),
                                         ('actor', actor)]:
                        native = proof['identity_stores'][label]
                        if context.operand64(
                                native['pc'],
                                native['value_register']) != value:
                            raise RuntimeError(
                                'Generalized native hardware identity arithmetic differs'
                            )
                    expected = (owner['plan']['segment_words'] *
                                (program != 0) + actor) * 8
                    if context.pointer_offset(expression, scratch) != expected:
                        raise RuntimeError(
                            'Generalized native scratch offset arithmetic differs'
                        )
                    contexts.append([list(grid), program, actor])
        failed = origins.inspect_native_header_origins(
            timeline, dict(capture, raw_sha256='0' * 64), machine)
        if failed[
                'status'] != 'unverified_native_header_origins_or_pattern' or not failed[
                    'implementation_sha256'] or failed[
                        'header_allocation_origin_verified']:
            raise RuntimeError(
                'Failed origin did not retain unverified rule fingerprints')
        reports.append(dict(proof=proof,
                            additional_cpu_contexts=len(contexts)))
    if original != {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in timeline.rglob('*') if p.is_file()
    }:
        raise RuntimeError('Original artifacts changed')
    (output / 'result.json').write_text(
        json.dumps(dict(reports=reports,
                        rejected=rejected,
                        negative_checks=len(rejected),
                        original_files_unchanged=len(original),
                        application_replayed=False),
                   indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--timeline', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    from flagtree.profiler import timeline_unit_nvidia_late, timeline_nvidia_late_origins, timeline_nvidia_late_raw
    run(args.timeline,
        args.output,
        units=timeline_unit_nvidia_late,
        origins=timeline_nvidia_late_origins,
        raws=timeline_nvidia_late_raw)
