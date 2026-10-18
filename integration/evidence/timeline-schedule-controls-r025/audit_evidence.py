"""Audit compile-only scheduling controls; no imports or qualification of product."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import tarfile


def need(condition, message):
    if not condition:
        raise ValueError(message)


CRITICAL = ('LDGSTS', 'LDGDEPBAR', 'DEPBAR', 'BAR.', 'LDSM', 'HMMA')


def critical_sequence(function, trip_count):
    """Expand this frozen control's one math loop, not arbitrary machine CFGs.

    This projection intentionally ignores logger-only paths and predicates. It
    describes committed attempts / wait guarantees, not actual copy traffic,
    valid endpoints, participating lanes, or hardware overlap.
    """
    instructions = [
        dict(pc=function['start'] + i * 16, **row)
        for i, row in enumerate(function['sass-instructions'])
    ]
    candidates = []
    for i, row in enumerate(instructions):
        if not row['opcode'].startswith('BRA'):
            continue
        targets = re.findall(r'0x([0-9a-fA-F]+)', row.get('operands', ''))
        if len(targets) != 1:
            continue
        target = int(targets[0], 16)
        body = [v for v in instructions if target <= v['pc'] < row['pc']]
        if target < row['pc'] and any(v['opcode'].startswith('HMMA')
                                      for v in body):
            candidates.append((i, target))
    need(
        len(candidates) <= 1,
        'This control audit cannot expand multiple math loops')
    if candidates:
        end, target = candidates[0]
        starts = [
            i for i, row in enumerate(instructions) if row['pc'] == target
        ]
        need(
            len(starts) == 1,
            'Math loop target not in actual instruction body')
        begin = starts[0]
        # BRA.U may carry its predicate in the operands rather than the JSON
        # predicate field. Do not label this edge unconditional.
        need(
            instructions[end]['opcode'] == 'BRA.U' and re.fullmatch(
                r'UP\d+,0x[0-9a-fA-F]+', instructions[end]['operands']),
            'Unknown math-loop branch form')
        sequence = (instructions[:begin] +
                    instructions[begin:end] * trip_count +
                    instructions[end + 1:])
    else:
        sequence = instructions
    return ([row for row in sequence
             if row['opcode'].startswith(CRITICAL)], len(candidates))


def analyze(function):
    sequence, loops = critical_sequence(function, trip_count=6)
    committed = guaranteed = 0
    waits, math, windows = [], [], []
    active = None
    for row in sequence:
        opcode = row['opcode']
        if opcode.startswith('LDGDEPBAR'):
            committed += 1
        elif opcode.startswith('DEPBAR'):
            match = re.fullmatch(r'SB0,0x([0-9a-fA-F]+)',
                                 row.get('operands', ''))
            need(opcode == 'DEPBAR.LE' and match is not None,
                 'Unknown wait-group instruction in frozen control')
            pending = int(match[1], 16)
            guaranteed = max(guaranteed, max(0, committed - pending))
            waits.append(pending)
            if pending == 2:
                active = dict(pc=row['pc'], operations=[])
                windows.append(active)
            else:
                active = None
        if opcode.startswith('HMMA'):
            math.append(
                dict(pc=row['pc'],
                     committed_groups=committed,
                     wait_guaranteed_prefix=guaranteed,
                     completion_not_established_groups=committed - guaranteed))
        if active is not None and opcode.startswith(('LDGSTS', 'HMMA')):
            active['operations'].append(opcode)
    need(waits == [2] * 6 + [0],
         'Unexpected original wait limits / occurrence projection')
    need(committed == 16 and guaranteed == 16 and len(math) == 24,
         'Unexpected projected committed attempts / matrix instructions')
    return dict(math_loops_expanded=loops,
                projected_critical_counts=dict(
                    Counter(row['opcode'] for row in sequence)),
                projected_wait_limits=waits,
                matrix_instructions=math,
                minimum_completion_not_established_groups_at_math=min(
                    row['completion_not_established_groups'] for row in math),
                wait_to_wait_windows=windows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with tarfile.open(args.archive) as archive:
        names = archive.getnames()
        need(len(names) == len(set(names)), 'Duplicate evidence members')

        def raw(name):
            member = archive.getmember(name)
            need(member.isfile(), 'Non-regular evidence member')
            return archive.extractfile(member).read()

        def doc(name):
            return json.loads(raw(name))

        inventory = doc('collection.json')
        need(
            set(names) == set(inventory['member_hashes'])
            | {'collection.json', 'inputs/ordinary_timeline_workload.py'},
            'Unexpected archive membership')
        for name, digest in inventory['member_hashes'].items():
            need(hashlib.sha256(raw(name)).hexdigest() == digest, name)
        need(inventory['active_owned_jobs'] == [], 'Owned jobs not closed')
        result = {}
        for run, expected_status in [('sparse-v1', 0), ('inline-v1', 0),
                                     ('expanded-v1', 1), ('expanded-v2', 0),
                                     ('nostore-v1', 0), ('deferred-v1', 0)]:
            prefix = 'runs/' + run + '/'
            terminal = doc(prefix + 'terminal.json')
            need(
                terminal['state'] == 'terminal'
                and terminal['returncode'] == expected_status,
                'Unexpected run termination: ' + run)
            if expected_status:
                need(
                    b'pm.run(src)' in raw(prefix + 'stderr.log')
                    and b'incompatible function arguments'
                    in raw(prefix + 'stderr.log'),
                    'First harness failure not retained')
                continue
            summary = doc(prefix + 'output/result.json')
            need(
                summary['actual_math_launches'] == 0
                and summary['canary_unchanged'] is True,
                'This evidence must remain compile-only')
            rows = doc(prefix + 'output/results.json')
            result[run] = {}
            for row in rows:
                folder = prefix + 'output/' + row['label'] + '/'
                need(
                    hashlib.sha256(raw(folder + 'kernel.cubin')).hexdigest() ==
                    row['cubin_sha256'], 'CUBIN identity mismatch')
                functions = doc(folder + 'json.stdout')[1]
                entries = [
                    f for f in functions if f['function-name'] == 'gemm'
                ]
                need(len(entries) == 1, 'Unexpected frozen kernel function')
                result[run][row['label']] = dict(
                    cubin_sha256=row['cubin_sha256'],
                    static_instruction_counts=row['instruction_counts'],
                    critical_projection=analyze(entries[0]))
        output = dict(
            status=
            'compile_controls_byte_audited_not_boundary_or_overlap_qualification',
            archive=dict(sha256=hashlib.sha256(
                args.archive.read_bytes()).hexdigest(),
                         bytes=args.archive.stat().st_size,
                         members=len(names)),
            frozen_control=dict(m=48,
                                n=56,
                                k=192,
                                block_k=32,
                                num_stages=3,
                                diagnostic_trip_count=6,
                                actual_math_launches=0),
            controls=result,
            limits=[
                'Diagnostic unrolling and LLVM store edits are not product policies.',
                'Inline controls intentionally lack source-boundary qualification.',
                'No-store controls also lose timer instructions; not a storage-only causal proof.',
                'Critical projection is not a full CFG, participation or endpoint proof.',
                'Groups lacking wait guarantees may already be complete; no measured hardware overlap.',
                'No same-throughput, numerical device, P01, or three-backend acceptance claim.'
            ])
    args.output.write_text(json.dumps(output, indent=2) + '\n')


if __name__ == '__main__':
    main()
