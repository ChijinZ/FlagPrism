"""Native late-record layout admission using common compact program arithmetic."""
from .timeline_storage import plan_selected_program_storage
from .timeline_cuda_runtime import CudaTimelineTransport


def _integer(value, label, lower, upper):
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError('Invalid late ' + label)
    return value


def plan_late_storage(plan,
                      *,
                      grid,
                      scratch_size,
                      alignment,
                      num_ctas,
                      max_raw_bytes=8 * 1024 * 1024):
    if (not isinstance(plan, dict)
            or type(plan.get('schema_version')) is not int
            or type(plan.get('profile_argument_abi')) is not int
            or type(plan.get('record_layout_version')) is not int
            or plan.get('schema_version') != 1
            or plan.get('profile_argument_abi') != 1
            or plan.get('record_layout_version') != 1
            or plan.get('word_layout') != 'program/logical_word/actor'
            or plan.get('compact_programs') is not True
            or 'timeline_fixed_programs' in plan):
        raise ValueError('Missing binary-bound late record layout/selection')
    actors = _integer(plan.get('actors'), 'actors', 1, 1024)
    capacity = _integer(plan.get('capacity_per_program'), 'capacity', 1, 4096)
    if plan.get('header_words') != 6:
        raise ValueError('Unknown late record header')
    dims = plan.get('block_dimensions')
    if type(dims) is not list or len(dims) != 3:
        raise ValueError('Missing actual late block dimensions')
    product = 1
    for value in dims:
        product *= _integer(value, 'block dimension', 1, 1024)
    if product > 1024 or actors > product:
        raise ValueError('Late observers differ from actual block geometry')
    if (type(plan.get('dependency_footprint_complete')) is not bool
            or plan['dependency_footprint_complete'] != (actors == product)):
        raise ValueError(
            'Late footprint selection differs from actual geometry')
    stride = (6 + 4 * capacity) * actors * 8
    if (type(scratch_size) is not int or scratch_size != stride
            or plan.get('segment_words') != stride // 8 or alignment != 8):
        raise ValueError(
            'Launch stride/alignment differs from native late layout')
    return plan_selected_program_storage(plan,
                                         grid=grid,
                                         scratch_size=stride,
                                         alignment=alignment,
                                         num_ctas=num_ctas,
                                         max_raw_bytes=max_raw_bytes,
                                         storage_version='nvidia-late-1')


class LateCudaTimelineTransport(CudaTimelineTransport):
    """Reuse actual CUDA streams/events/guard readback; replace only layout."""

    def plan_storage(self, plan, **kwargs):
        return plan_late_storage(plan, **kwargs)
