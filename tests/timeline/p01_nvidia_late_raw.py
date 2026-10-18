"""Actual late raw decode and damaged-byte contracts, without device replay."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--module', type=Path, required=True)
    p.add_argument('--math-root', type=Path, required=True)
    p.add_argument('--generic-root', type=Path, required=True)
    p.add_argument('--overflow-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location('late_raw', a.module)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    inputs = {}
    results = []
    rejects = []

    def decode(folder, manifest_name, file_name, programs):
        manifest_path = folder / manifest_name
        raw_path = folder / file_name
        for path in (manifest_path, raw_path):
            inputs[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        plan = json.loads(manifest_path.read_text())
        allocation = raw_path.read_bytes()
        guard = 16 * 8
        if allocation[:guard] != allocation[-guard:] or struct.unpack(
                '<16Q', allocation[:guard]) != (0x5A5A1234, ) * 16:
            raise RuntimeError('Original device allocation guards differ')
        raw = allocation[guard:-guard]
        result = module.decode_late_raw(plan,
                                        raw,
                                        slots=list(enumerate(programs)))
        results.append(
            dict(file=str(raw_path),
                 complete=result['complete'],
                 programs=len(result['programs']),
                 actors=plan['actors'],
                 events=sum(
                     len(actor['events']) for program in result['programs']
                     for actor in program['observers']),
                 raw_sha256=result['raw_sha256']))
        return plan, raw, result

    for name, tiles in (('runtime', 3), ('runtime', 7), ('constant', 3)):
        plan, raw, result = decode(a.math_root / name, 'sites.json',
                                   'allocation-' + str(tiles) + '.bin', [0, 3])
        if not result['complete']:
            raise RuntimeError('Actual math capture is not complete')
    for name in ('nonlinear', 'row_softmax'):
        plan, raw, result = decode(a.generic_root / name, 'manifest.json',
                                   'allocation.bin', [0, 1])
        if not result['complete']:
            raise RuntimeError('Actual generic capture is not complete')
    # Real over-capacity run, not synthetic success with a loss flag inserted.
    overflow_plan, overflow_raw, overflow = decode(a.overflow_root / 'runtime',
                                                   'sites.json',
                                                   'allocation-7.bin', [0, 3])
    if overflow['complete'] or not any(
            actor.get('overflow') for program in overflow['programs']
            for actor in program['observers']):
        raise RuntimeError('Actual capacity failure was not reported as loss')
    actors = plan['actors']
    words = list(struct.unpack('<' + str(len(raw) // 8) + 'Q', raw))

    def reject(name, mutate):
        changed = words.copy()
        mutate(changed)
        try:
            module.decode_late_raw(plan,
                                   struct.pack('<' + str(len(changed)) + 'Q',
                                               *changed),
                                   slots=[(0, 0), (1, 1)])
        except module.LateRawError as error:
            rejects.append(dict(case=name, reason=str(error)))
        else:
            raise RuntimeError('Damaged actual record accepted: ' + name)

    reject('mixed_actor', lambda w: w.__setitem__(5 * actors, 1))
    reject('mixed_program', lambda w: w.__setitem__(3 * actors, 1))
    reject('unknown_site', lambda w: w.__setitem__(6 * actors, 0xffffffff))
    reject('reversed_ticks',
           lambda w: w.__setitem__(8 * actors, w[7 * actors] - 1))
    reject('invalid_overflow_flag', lambda w: w.__setitem__(actors, 2))
    reject('unpublished_with_residue', lambda w: w.__setitem__(2 * actors, 0))
    reject('count_exceeds_capacity',
           lambda w: w.__setitem__(0, plan['capacity_per_program'] + 1))
    # Raw decode permits real control-flow outcomes. Modified bytes below are
    # decoder fixtures only; never exported as measured device captures.
    for outcome in ('arrived_empty', 'not_arrived', 'divergent'):
        changed = words.copy()
        count = changed[0]
        for row in range(6, 6 + 4 * plan['capacity_per_program']):
            if outcome != 'divergent' or row >= 6 + 4 * (count - 1):
                changed[row * actors] = 0
        changed[0] = count - 1 if outcome == 'divergent' else 0
        if outcome == 'not_arrived':
            for row in range(6):
                changed[row * actors] = 0
        decoded = module.decode_late_raw(plan,
                                         struct.pack(
                                             '<' + str(len(changed)) + 'Q',
                                             *changed),
                                         slots=[(0, 0), (1, 1)])
        if decoded['complete'] != (outcome != 'not_arrived'):
            raise RuntimeError('Control-flow outcome misreported: ' + outcome)
        if decoded['clock_comparison_qualified'] or decoded[
                'hardware_busy_qualified'] or decoded['source_cost_qualified']:
            raise RuntimeError('Raw decoder granted unproven semantics')
    for path, digest in inputs.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
            raise RuntimeError('Original capture was modified: ' + path)
    (a.output / 'result.json').write_text(
        json.dumps(dict(
            status='retained_actual_bytes_and_control_flow_contracts_passed',
            inputs=inputs,
            results=results,
            rejects=rejects,
            fixtures_only=['arrived_empty', 'not_arrived', 'divergent']),
                   indent=2))


if __name__ == '__main__':
    main()
