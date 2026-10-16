"""Layout contract for the compiler's single-writer all-grid source census.

Counts mean reaching a source position in the declared default warp or logical
partition observer, including fully masked operations. Partition IDs do not name
physical warps. They are neither completed memory transactions nor timing.
"""
import math


def census_descriptor(metadata, launch, allocation_bytes, selection):
    compiler = metadata.get('compiler_metadata') or {}
    if compiler.get('num_ctas', 1) != 1:
        raise RuntimeError(
            'NVIDIA source census requires num_ctas=1; CTA clusters are unsupported'
        )
    grid = launch.get('grid')
    if (not isinstance(grid, (list, tuple)) or not 1 <= len(grid) <= 3
            or any(type(v) is not int or v < 0 for v in grid)):
        raise RuntimeError(
            'NVIDIA source census requires actual associated launch geometry')
    grid = list(grid) + [1] * (3 - len(grid))
    names = sorted(metadata.get('scope_id_names', []))
    if not names or [site for site, _ in names] != list(range(len(names))):
        raise RuntimeError(
            'NVIDIA source census requires dense actual compiler site IDs')
    sites = []
    for site, name in names:
        origin = metadata.get('scope_id_origins', {}).get(str(site), {})
        role = origin.get('census_role')
        if role not in ('primary', 'context') or not origin.get('automatic'):
            raise RuntimeError(
                'NVIDIA source census site lacks actual compiler role/source metadata'
            )
        sites.append(dict(site=site, name=name, role=role, origin=origin))
    actor_map = {
        0:
        dict(kind='logical_warp',
             id=0,
             writer='physical_thread_zero',
             mask_activity='unobserved')
    }
    for site in sites:
        origin = site['origin']
        actor = origin.get('census_actor', 0)
        threads = origin.get('census_observer_threads', 0)
        if type(actor) is not int or actor < 0 or type(
                threads) is not int or threads < 0:
            raise RuntimeError(
                'NVIDIA census has invalid compiler observer identity')
        if actor:
            if threads < 32 or threads % 32 or type(
                    origin.get('census_partition_region')) is not int:
                raise RuntimeError(
                    'NVIDIA census partition observer lacks compiler geometry')
            value = dict(
                kind='logical_program_observer',
                id=actor,
                compiler_partition_region=origin['census_partition_region'],
                partition_threads=threads,
                writer='physical_thread_id_mod_partition_threads_zero',
                mask_activity='unobserved')
            if actor in actor_map and actor_map[actor] != value:
                raise RuntimeError(
                    'NVIDIA census has inconsistent partition observer geometry'
                )
            actor_map[actor] = value
    if sorted(actor_map) != list(range(len(actor_map))):
        raise RuntimeError(
            'NVIDIA census compiler observer identities are not dense')
    actors = [actor_map[index] for index in range(len(actor_map))]
    stride = (len(sites) * len(actors) * 8 + 127) // 128 * 128
    if compiler.get('profile_scratch_size') != stride:
        raise RuntimeError(
            'NVIDIA source census compiler scratch layout mismatch')
    programs = math.prod(grid)
    if programs * len(sites) * len(actors) > selection['max_census_cells']:
        raise RuntimeError(
            'NVIDIA source census cell budget exceeded before launch')
    if programs * stride > selection['max_census_bytes']:
        raise RuntimeError(
            'NVIDIA source census byte budget exceeded before launch')
    if allocation_bytes != programs * stride:
        raise RuntimeError(
            'NVIDIA source census actual allocation does not match launch geometry'
        )
    return dict(schema='flagprism.source-census',
                version=1,
                cell_size=8,
                byte_order='little',
                grid=grid,
                program_count=programs,
                sites=sites,
                actors=actors,
                cells_offset=0,
                program_stride=stride,
                actor_stride=len(sites) * 8,
                site_stride=8,
                binary_id=metadata.get('binary_id'),
                invocation_id=launch.get('invocation_id'),
                compiler_ir_sha256=metadata.get('compiler_ir_sha256'),
                semantics='source_region_reached')
