"""Collective byte-dependency analysis over validated late raw events.

A valid raw capture can be ineligible for this particular collective model.
Such captures remain available; no missing participants or time arrows are
invented to make dependency analysis succeed.
"""
from .timeline_nvidia_late_model import analyze_probe, LateModelError


def derive_late_async(decoded, manifest, *, shared_bytes):
    limitations = dict(machine_site_binding_verified=False,
                       clock_comparison_qualified=False,
                       time_flows_qualified=False,
                       source_cost_qualified=False,
                       hardware_busy_qualified=False)

    def unavailable(reason):
        return dict(status='model_unavailable', reason=reason, **limitations)

    sites = {site['site_id']: site for site in manifest['sites']}
    if not any(site['kind'] == 'copy_submit_after' for site in sites.values()):
        return dict(status='no_modeled_native_async_copy', **limitations)
    if manifest.get('dependency_footprint_complete'
                    ) is not True or not decoded['complete']:
        return unavailable(
            'Collective model requires complete actual CTA participation')
    if any(site['kind'] == 'opaque_native_issue_bracket' for site in
           [*sites.values(), *manifest.get('unselected_sites', [])]):
        return unavailable(
            'Opaque native operations prevent complete shared-memory side-effect coverage'
        )
    for site in sites.values():
        if site['kind'] == 'shared_load_issue_bracket':
            allowed = {
                'llvm.nvvm.ldmatrix.sync.aligned.m8n8.x4.b16.p3',
                'llvm.nvvm.ldmatrix.sync.aligned.m8n8.x4.trans.b16.p3'
            }
            if not site.get('members') or any(
                    member.get('native_operation') not in allowed
                    for member in site['members']):
                return unavailable(
                    'Native shared-load operand geometry is not modeled')
    programs = []
    for program in decoded['programs']:
        observers = program['observers']
        if (len(observers) != manifest['actors']
                or any(not observer['arrived'] or not observer['complete']
                       for observer in observers)):
            return unavailable('Incomplete collective participant set')
        sequences = [observer['events'] for observer in observers]
        if not sequences or not sequences[0] or any(
            [row['site_id']
             for row in sequence] != [row['site_id'] for row in sequences[0]]
                for sequence in sequences[1:]):
            return unavailable(
                'Divergent collective sequence needs a richer participation model'
            )
        bases = {observer['shared_base'] for observer in observers}
        if len(bases) != 1:
            return unavailable(
                'Actual participants disagree on the shared-memory base')
        programs.append(
            dict(program=program['program_id'],
                 physical_slot=program['physical_slot'],
                 shared_base=bases.pop(),
                 actors=sequences))
    try:
        report = analyze_probe(
            dict(programs=programs,
                 sites=sites,
                 shared_bytes=shared_bytes,
                 raw_sha256=decoded['raw_sha256']))
    except LateModelError as error:
        return dict(status='model_inconsistent',
                    reason=str(error),
                    **limitations)
    report['status'] = 'dynamic_byte_model_consistent'
    return report


def lifecycle_roles(report):
    """Program-local native-ordinal associations, never temporal flow grants.

    Called only with a freshly derived collective model, not a cached report.
    The caller binds each role to this invocation/program's actual raw ordinal.
    Completion means a recorded return from a native wait/barrier, not the
    unknown physical completion instant of an asynchronous operation.
    """
    if report.get('status') != 'dynamic_byte_model_consistent':
        return {}
    if report.get('model') != 'nvidia.late.shared_byte_lifecycle.v2':
        raise ValueError('Unknown shared-byte lifecycle model')
    roles = {}
    for program in report['programs']:

        def add(sequence, role):
            if sequence is not None:
                roles.setdefault((program['program'], sequence),
                                 []).append(role)

        for generation in program['generations']:
            base = dict(generation_id=generation['identity'],
                        generation_kind=generation['kind'],
                        shared_base=program['shared_base'],
                        generation_shared_ranges=generation['shared_ranges'],
                        shared_range_encoding=report['shared_range_encoding'],
                        qualification='conditional_byte_model_not_time_flow')
            for submission in generation['submissions']:
                add(
                    submission['sequence'],
                    dict(base,
                         role='producer_submission',
                         bytes=submission['bytes'],
                         shared_ranges=submission['shared_ranges']))
            add(generation['commit_sequence'], dict(base, role='group_commit'))
            add(
                generation['completion_observed_sequence'],
                dict(base,
                     role='completion_observed',
                     observation=generation['completion_observation_kind']))
            add(generation['publication_barrier_sequence'],
                dict(base, role='publication_observed'))
        for edge in program['consumer_edges']:
            add(
                edge['consumer_sequence'],
                dict(role='shared_consumer',
                     generation_id=edge['producer'],
                     bytes=edge['bytes'],
                     shared_base=program['shared_base'],
                     shared_ranges=edge['shared_ranges'],
                     shared_range_encoding=report['shared_range_encoding'],
                     publication_barrier_sequence=edge['publication_barrier'],
                     qualification='conditional_byte_model_not_time_flow'))
        for edge in program['reuse']:
            add(
                edge['sequence'],
                dict(role='physical_bytes_reused',
                     previous_generation=edge['previous'],
                     next_generation=edge['next'],
                     bytes=edge['overlapping_bytes'],
                     shared_base=program['shared_base'],
                     shared_ranges=edge['overlapping_shared_ranges'],
                     shared_range_encoding=report['shared_range_encoding'],
                     barrier_sequence=edge['barrier_sequence'],
                     qualification='conditional_byte_model_not_time_flow'))
    return roles
