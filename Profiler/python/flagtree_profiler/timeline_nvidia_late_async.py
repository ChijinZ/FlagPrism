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
