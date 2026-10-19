"""Join actual late native/storage/byte/clock facts into observed dependencies.

All CTA participants feed the byte model. Displayed edges name actual selected
threads and raw clock records; no selected thread replaces collective coverage.
"""
import hashlib
from pathlib import Path

from .timeline_events import stable_id
from .timeline_views import document_sha256
from .timeline_dependencies import ObservedDependencyProof


def _warp_scope_evidence(directory, capture, decoded, machine, native):
    """Bind full-block warp publication to actual PTX and stored mask words.

    This does not require a physical WARPSYNC opcode: ptxas can elide a
    redundant warp fence. The interval remains an observed source bracket,
    never an engine activity interval or evidence of a hardware busy duration.
    """
    import re
    from .timeline_nvidia_control import _need
    from .timeline_nvidia_machine import _lex
    from .timeline_nvidia_late_boundaries import _ptx_operation
    from .timeline_store import read_artifact
    plan = capture['owner']['plan']
    sites = [
        s for s in plan['sites'] if s['kind'] == 'warp_sync_issue_bracket'
    ]
    if not sites:
        return []
    ptx = next(a for a in capture['metadata']['timeline_artifacts']
               if a['retained_file'].endswith('.ptx'))
    lines, markers = _lex(
        read_artifact(directory, ptx['retained_file']).decode('utf-8'),
        'late-v1')
    markers = {(site, phase): line for line, site, phase in markers}
    readers = {(r['site_id'], r['phase']): r for r in machine['counter_pcs']}
    fields = {
        r['site_id']: r
        for r in native['relative_record_fields']['sites']
    }
    result = []
    for site in sites:
        _need(
            len(site['members']) == 1
            and site['members'][0]['native_operation']
            == 'llvm.nvvm.bar.warp.sync',
            'Warp synchronization source intrinsic differs')
        line, token = _ptx_operation(lines, markers, site, readers)
        _need(
            re.fullmatch(r'bar\.warp\.sync(?:-1|0xffffffff|4294967295);',
                         token) is not None,
            'Full-block publication needs the actual full-mask PTX warp fence')
        field = fields[site['site_id']]
        _need(
            field['status'] == 'native_record_fields_checked'
            and field['literal_payload'] == 0xffffffff,
            'Warp participation mask lacks native stored-value provenance')
        count = 0
        for program in decoded['programs']:
            for actor in program['observers']:
                for event in actor['events']:
                    if event['site_id'] == site['site_id']:
                        _need(event['payload'] == field['literal_payload'],
                              'Actual recorded warp mask differs')
                        count += 1
        _need(count > 0, 'Warp synchronization has no actual observations')
        result.append(
            dict(site_id=site['site_id'],
                 ptx_line=line,
                 mask=0xffffffff,
                 occurrences=count,
                 full_block_scope=plan['actors'] <= 32,
                 scope='actual single warp only',
                 physical_opcode_required=False))
    return result


def load_observed_dependency_inputs(directory, capture, raw):
    from .timeline_nvidia_shared import load_shared_counter_inputs
    from .timeline_unit_nvidia_late import load_late_machine_map
    from .timeline_nvidia_late_boundaries import load_native_boundary_report
    from .timeline_nvidia_late_origins import load_native_header_origins
    from .timeline_nvidia_late_addresses import load_record_ordinal_bindings
    from .timeline_nvidia_late_records import load_control_payload_agreement
    from .timeline_nvidia_late_payloads import load_shared_payload_bindings
    from .timeline_nvidia_late_raw import decode_late_raw
    from .timeline_nvidia_late_async import derive_late_async
    from .timeline_nvidia_late_control import derive_late_wait_control
    from .timeline_store import read_artifact
    from .timeline_nvidia_control import _need

    owner, metadata = capture['owner'], capture['metadata']
    _need(
        hashlib.sha256(raw).hexdigest() == capture['raw_sha256'],
        'Dependency raw changed')
    decoded = decode_late_raw(owner['plan'],
                              raw,
                              slots=owner['layout']['slots'])
    model = derive_late_async(
        decoded,
        owner['plan'],
        shared_bytes=metadata['compiler_metadata']['shared'])
    _need(
        model['status'] == 'dynamic_byte_model_consistent',
        'Observed dependencies need a complete collective byte model: ' +
        model['status'])
    canonical, clocks = load_shared_counter_inputs(directory, capture, raw)
    machine = load_late_machine_map(directory, capture)
    native = load_native_boundary_report(directory, capture, machine)
    for name, expected in [('sites', 'native_boundary_control_order_checked')]:
        _need(
            native[name]
            and all(r['status'] == expected for r in native[name]),
            'Native dependency boundaries incomplete')
    for name, expected in [
        ('timer_store_values', 'timer_to_native_store_values_checked'),
        ('relative_record_fields', 'native_record_fields_checked'),
        ('shared_payload_values', 'native_shared_payload_words_checked')
    ]:
        _need(
            native[name]['sites']
            and all(r['status'] == expected for r in native[name]['sites']),
            'Native dependency value evidence incomplete: ' + name)
    base = 'machine/' + owner['binary_id']
    waits = derive_late_wait_control(
        machine_map=machine,
        sass_lines=read_artifact(directory, base + '/lines.stdout'),
        sass_json=read_artifact(directory, base + '/json.stdout'),
        plan=owner['plan'])
    _need(
        waits['sites'] and all(r['status'] == 'late_wait_control_order_checked'
                               for r in waits['sites']),
        'Native wait controls incomplete')
    origins = load_native_header_origins(directory, capture, machine)
    ordinals = load_record_ordinal_bindings(
        directory, capture, native['record_address_arithmetic'])
    controls = load_control_payload_agreement(directory, capture,
                                              native['relative_record_fields'])
    payloads = load_shared_payload_bindings(directory, capture,
                                            native['shared_payload_values'])
    for fact in (origins, ordinals, controls, payloads):
        _need(
            fact['raw_sha256'] == decoded['raw_sha256']
            and fact['identity'] == canonical['identity'],
            'Joined dependency evidence crosses invocation/raw identity')
    _need(
        origins['header_allocation_origin_verified']
        and origins['shared_symbol_header_value_origin_verified']
        and ordinals['relative_record_ordinal_binding_verified'],
        'Native storage origin/ordinal facts incomplete')
    warp_scopes = _warp_scope_evidence(directory, capture, decoded, machine,
                                       native)
    evidence = dict(warp_scopes=warp_scopes,
                    native=native,
                    waits=waits,
                    origins=origins,
                    ordinals=ordinals,
                    controls=controls,
                    payloads=payloads,
                    byte_model=model)
    evidence_ids = tuple(name + '_sha256:' + document_sha256(value)
                         for name, value in evidence.items())
    from . import timeline_nvidia_late_async, timeline_nvidia_late_model, timeline_nvidia_shared, timeline_dependencies
    implementation = document_sha256(
        dict(semantic_rules={
            Path(module.__file__).name:
            hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
            for module in (timeline_nvidia_late_async,
                           timeline_nvidia_late_model, timeline_nvidia_shared,
                           timeline_dependencies)
        },
             mapper=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             primitive_rules={
                 key:
                 value.get('implementation_sha256')
                 if isinstance(value, dict) else None
                 for key, value in evidence.items()
             }))
    observers = {r['id']: r for r in canonical['observers']}
    events = {
        (observers[e['observer_id']]['attributes']['nvidia.logical_program'], observers[e['observer_id']]['attributes']['nvidia.thread_flat_index'], e['coverage']['nvidia.raw_ordinal']):
        e
        for e in canonical['events']
    }
    # Source subrecords of a coalesced native load share its actual first
    # observation witness; the later empty source bracket is never a second op.
    native_first = {(r[0], r[1], r[2]): r[7] for r in payloads['rows']}
    models = {p['program']: p for p in model['programs']}
    proofs = []
    for clock in clocks:
        chosen = sorted(
            (observers[key] for key in clock.observer_ids),
            key=lambda r: r['attributes']['nvidia.thread_flat_index'])
        program = chosen[0]['attributes']['nvidia.logical_program']
        actors = [r['attributes']['nvidia.thread_flat_index'] for r in chosen]
        generations = {
            g['identity']: g
            for g in models[program]['generations']
        }
        merged = {}

        def endpoint(actor, sequence, *, consumer=False):
            if sequence is None:
                return None
            if consumer:
                sequence = native_first.get((program, actor, sequence),
                                            sequence)
            event = events[program, actor, sequence]
            # The exit sample is an observation after native issue/wait, never
            # an inferred engine completion. Checkpoints have one record.
            return event['record_ids'][-1]

        def add(source,
                target,
                relation,
                generation,
                *,
                component=None,
                **attributes):
            if source is None or target is None or source == target:
                return
            association = stable_id(
                tuple(canonical['identity'][k]
                      for k in ('capture_id', 'invocation_id', 'binary_id')),
                'generation', program, generation)
            key = source, target, relation, association
            if key not in merged:
                merged[key] = dict(
                    source=source,
                    target=target,
                    relation=relation,
                    display_label='collective generation ' + generation,
                    association_key=association,
                    attributes=dict(
                        generation=generation,
                        program=program,
                        coverage_actors=owner['plan']['actors'],
                        shared_range_encoding=model['shared_range_encoding'],
                        **attributes))
            if component is not None:
                values = merged[key]['attributes'].setdefault(
                    'model_components', [])
                if component not in values:
                    values.append(component)

        for generation in generations.values():
            name = generation['identity']
            completion, publication = generation[
                'completion_observed_sequence'], generation[
                    'publication_barrier_sequence']
            for actor in actors:
                commit = endpoint(actor, generation['commit_sequence'])
                done, published = endpoint(actor, completion), endpoint(
                    actor, publication)
                for submit in generation['submissions']:
                    add(endpoint(actor, submit['sequence']),
                        commit or published,
                        'submission_observed_to_commit_or_barrier_observed',
                        name,
                        component=dict(sequence=submit['sequence'],
                                       bytes=submit['bytes'],
                                       range_sha256=document_sha256(
                                           submit['shared_ranges'])))
                add(commit, done, 'commit_observed_to_wait_return_observed',
                    name)
                add(done, published,
                    'wait_return_observed_to_barrier_instruction_observed',
                    name)
        for index, consumer in enumerate(models[program]['consumer_edges']):
            name = consumer['producer']
            generation = generations[name]
            witness = generation['completion_observed_sequence'] if generation[
                'kind'] == 'async' else generation['submissions'][0]['sequence']
            for actor in actors:
                target = endpoint(actor,
                                  consumer['consumer_sequence'],
                                  consumer=True)
                attributes = dict(
                    bytes=consumer['bytes'],
                    range_sha256=document_sha256(consumer['shared_ranges']),
                    model_consumer_edge=index,
                    source_sequence=consumer['consumer_sequence'])
                add(endpoint(actor, consumer['publication_barrier']),
                    target,
                    'barrier_instruction_observed_to_consumer_issue_observed',
                    name,
                    component=attributes)
                # One actual producer witness, not a synthetic collective-ready
                # timestamp. The complete byte/participation model remains in
                # evidence, independently of this display choice.
                add(endpoint(actors[0], witness),
                    target,
                    'producer_witness_to_consumer_issue_observed',
                    name,
                    component=attributes,
                    witness_actor=actors[0],
                    witness_only=True)
        for reuse in models[program]['reuse']:
            previous = generations[reuse['previous']]
            name = reuse['previous'] + ' -> ' + reuse['next']
            for actor in actors:
                fence = endpoint(actor, reuse['barrier_sequence'])
                for sequence in previous['consumer_sequences']:
                    add(endpoint(actor, sequence, consumer=True),
                        fence,
                        'consumer_issue_observed_to_reuse_barrier_observed',
                        name,
                        component=dict(sequence=sequence),
                        overlapping_bytes=reuse['overlapping_bytes'])
                add(fence,
                    endpoint(actor, reuse['sequence']),
                    'reuse_barrier_observed_to_next_submission_observed',
                    name,
                    overlapping_bytes=reuse['overlapping_bytes'])
        proofs.append(
            ObservedDependencyProof(
                clock=clock,
                provider='nvidia.late.collective_byte_observed_dependencies.v1',
                implementation_sha256=implementation,
                evidence_ids=evidence_ids,
                edges=tuple(merged[key] for key in sorted(merged))))
    return canonical, proofs
