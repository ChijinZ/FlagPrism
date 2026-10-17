"""Admission for the NVIDIA compact timeline storage ABI.

This validates compiler-plan facts, not device clock or compiler provenance.
The caller must bind the plan to its actual loaded binary before allocating.
No device allocation or synchronization occurs in this module.
"""
from collections.abc import Mapping


def _integer(value, name, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f'{name} must be an integer in [{minimum}, {maximum}]')
    return value


def plan_compact_storage(plan, *, grid, scratch_size, alignment, num_ctas,
                         max_raw_bytes=8 * 1024 * 1024):
    """Return the bounded slot map for one admitted noncluster launch.

    Grid and stride are the actual driver's values, never cached grid metadata.
    A zero-volume launch has no record slots. Fixed IDs come only from the
    compiled plan; supplying a new list to this allocator cannot change a binary.
    """
    if not isinstance(plan, Mapping):
        raise ValueError('A binary-bound compiler plan is required')
    for key, expected in (('timeline_storage_version', 1),
                          ('timeline_record_version', 2)):
        if type(plan.get(key)) is not int or plan[key] != expected:
            raise ValueError(f'Unsupported or missing {key}')
    if plan.get('timeline_storage_policy') != 'compact_selected_programs':
        raise ValueError('Unsupported timeline storage policy')
    if plan.get('timeline_default_program_selection') != 'runtime_first_last':
        raise ValueError('Unsupported default timeline selection')
    _integer(num_ctas, 'num_ctas', 1, 1)
    if type(grid) not in (tuple, list) or len(grid) != 3:
        raise ValueError('Actual grid must have three integer dimensions')
    dimensions = tuple(_integer(v, 'grid dimension', 0, 0xffffffff) for v in grid)
    volume = dimensions[0] * dimensions[1] * dimensions[2]
    if volume > 0xffffffff:
        raise ValueError('Grid exceeds the compact program identity range')
    stride = _integer(scratch_size, 'scratch_size', 16, 0x7fffffff)
    align = _integer(alignment, 'alignment', 1, 1 << 20)
    if align & (align - 1):
        raise ValueError('Scratch alignment must be a power of two')
    budget = _integer(max_raw_bytes, 'max_raw_bytes', 1, 0x7fffffff)
    fixed = plan.get('timeline_fixed_programs')
    if 'timeline_fixed_programs' in plan:
        if type(fixed) not in (tuple, list) or not fixed:
            raise ValueError('Fixed timeline program selection cannot be empty')
        programs = tuple(_integer(v, 'fixed program', 0, 0x7fffffff) for v in fixed)
        if len(set(programs)) != len(programs):
            raise ValueError('Fixed program identities must be unique')
        if volume and any(v >= volume for v in programs):
            raise ValueError('A fixed program is outside the actual launch grid')
        if not volume:
            programs = ()
    else:
        programs = () if not volume else (0,) if volume == 1 else (0, volume - 1)
    raw_bytes = len(programs) * stride
    if raw_bytes > budget:
        raise ValueError('Compact scratch exceeds the admitted raw budget')
    return {'storage_version': 1, 'grid': dimensions, 'num_ctas': 1,
            'slots': tuple(enumerate(programs)), 'scratch_size': stride,
            'alignment': align, 'logical_request_bytes': volume * stride,
            'raw_bytes': raw_bytes, 'programs': programs}
