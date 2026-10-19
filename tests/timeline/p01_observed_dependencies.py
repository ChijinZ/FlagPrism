"""Exercise observed dependencies using retained real device records only."""
import copy
import importlib
from dataclasses import replace
import hashlib
import json
from pathlib import Path


def run(timeline, output, *, backend, common, exporter):
    output.mkdir(parents=True)
    original = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in timeline.rglob('*') if p.is_file()
    }
    rejected, reports = [], []
    control = importlib.import_module(backend.__package__ +
                                      '.timeline_nvidia_control')
    for predicate in ('UP1', '!UP1'):
        parsed = control._branch(
            dict(opcode='BRA.U', predicate=None,
                 operands=predicate + ',0x100'))
        if parsed != (predicate, 256):
            raise RuntimeError('Uniform branch target/polarity lost')
        for known in (True, False):
            expected = not known if predicate.startswith('!') else known
            if control._truth(predicate, {'UP1': known}) is not expected:
                raise RuntimeError(
                    'Uniform branch polarity changed control semantics')

    def reject(name, call):
        try:
            call()
        except (ValueError, TypeError, KeyError):
            rejected.append(name)
        else:
            raise RuntimeError('Invalid dependency accepted: ' + name)

    for operands in ('!!UP1,0x100', 'UP1', 'P1,0x100', '!UP1,missing'):
        reject(
            'invalid_uniform_branch_' + operands, lambda: control._branch(
                dict(opcode='BRA.U', predicate=None, operands=operands)))

    for item in json.loads((timeline / 'index.json').read_text())['captures']:
        from flagtree.profiler.timeline_capture_store import load_capture_file
        capture = load_capture_file(timeline / item['capture_file'])
        raw = (timeline / capture['raw_file']).read_bytes()
        canonical, proofs = backend.load_observed_dependency_inputs(
            timeline, capture, raw)
        reject(
            'different_raw', lambda: backend.load_observed_dependency_inputs(
                timeline, capture, raw + b'X'))
        for proof in proofs:
            view = common.derive_dependency_view(canonical, proof)
            common.validate_dependency_view(view, canonical, proof)
            trace = exporter.encode_dependency_trace(view,
                                                     canonical,
                                                     proof=proof)
            if not trace or not view['time_arrows_verified'] or view[
                    'hardware_busy_qualified']:
                raise RuntimeError('Observed dependency semantics differ')
            for field, value in [('origin_tick', view['origin_tick'] + 1),
                                 ('hardware_busy_qualified', True),
                                 ('nodes', [])]:
                wrong = copy.deepcopy(view)
                wrong[field] = value
                reject(
                    'changed_view_' + field,
                    lambda: common.validate_dependency_view(
                        wrong, canonical, proof))
            wrong = copy.deepcopy(canonical)
            wrong['identity']['invocation_id'] += '-other'
            reject('different_invocation',
                   lambda: common.derive_dependency_view(wrong, proof))
            first = proof.edges[0]
            for field, value in [('source', 'missing-raw-record'),
                                 ('target', first['source']),
                                 ('association_key', ''),
                                 ('display_label', ''), ('attributes', []),
                                 ('unknown_required_field', True)]:
                edge = dict(first, **{field: value})
                reject(
                    'bad_edge_' + field, lambda: common.derive_dependency_view(
                        canonical, replace(proof, edges=(edge, ))))
            reject(
                'duplicate_edge', lambda: common.derive_dependency_view(
                    canonical, replace(proof, edges=(first, first))))
            reject('missing_mechanism_evidence',
                   lambda: replace(proof, evidence_ids=()))
            nodes = {n['id']: n for n in view['nodes']}
            positive = next(e for e in proof.edges if nodes[e['source']]
                            ['time_ns'] < nodes[e['target']]['time_ns'])
            reversed_edge = dict(positive,
                                 source=positive['target'],
                                 target=positive['source'])
            reject(
                'reversed_observed_time',
                lambda: common.derive_dependency_view(
                    canonical, replace(proof, edges=(reversed_edge, ))))
            foreign = next((p for p in proofs
                            if p.clock.domain_id != proof.clock.domain_id),
                           None)
            if foreign is not None:
                reject(
                    'different_program_clock',
                    lambda: common.derive_dependency_view(
                        canonical, replace(proof, clock=foreign.clock)))
            reject(
                'trace_budget', lambda: exporter.encode_dependency_trace(
                    view, canonical, proof=proof, max_bytes=64))
            # Mapping order must never alter stable generation/edge identities.
            reordered = dict(
                canonical,
                identity=dict(reversed(list(canonical['identity'].items()))))
            if common.derive_dependency_view(reordered, proof) != view:
                raise RuntimeError(
                    'Identity mapping order changed dependency IDs')
            reports.append(
                dict(invocation_id=canonical['identity']['invocation_id'],
                     domain_id=view['domain_id'],
                     nodes=len(view['nodes']),
                     edges=len(view['edges']),
                     bytes=len(trace)))
    if original != {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in timeline.rglob('*') if p.is_file()
    }:
        raise RuntimeError('Dependency contract rewrote original bytes')
    result = dict(status='real_record_dependency_contract_passed',
                  reports=reports,
                  rejected=rejected,
                  originals_unchanged=len(original))
    (output / 'result.json').write_text(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--timeline', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    from flagtree.profiler import timeline_nvidia_dependencies, timeline_dependencies, timeline_dependency_perfetto
    run(args.timeline,
        args.output,
        backend=timeline_nvidia_dependencies,
        common=timeline_dependencies,
        exporter=timeline_dependency_perfetto)
