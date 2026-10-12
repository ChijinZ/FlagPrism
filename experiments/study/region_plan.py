"""Executable measurement contracts for the Study's shared logical request.
This is a research adapter, not a claim of a complete general-purpose IR system.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class CapturePlan:
    backend: str
    request_id: str
    captures: tuple
    association: str
    unsupported: tuple
    clock_unit: str

def plan(backend, *, joint_invocation=False, clock_provider=None):
    if backend == 'cuda':
        return CapturePlan(backend, 'logical-region-intervals-v1', ('nested',),
                           'same capture and launch; explicit Triton program coordinates', (), 'globaltimer_ns')
    if backend == 'enflame':
        if clock_provider == 'validated-sdk-global-timer':
            return CapturePlan(backend, 'logical-region-intervals-v1', ('nested-global-timer',),
                               'same capture and launch; explicit program coordinates; research-only late-LLVM clock adapter',
                               ('nanosecond conversion until timer frequency verified',), 'SDK_global_timer_ticks')
        if joint_invocation:
            return CapturePlan(backend, 'logical-region-intervals-v1', (),
                               'no observation returned', ('joint nested body/output with current begin/end primitive',),
                               'SDK_counter_units_unverified')
        return CapturePlan(backend, 'logical-region-intervals-v1', ('body', 'output'),
                           'deterministic replay: same logical program/input, different physical launches',
                           ('joint body/output timeline',), 'SDK_counter_units_unverified')
    if backend == 'cann':
        return CapturePlan(backend, 'logical-region-intervals-v1', ('actor-local-late-llvm',),
                           'compiler actor projection; explicit block/subblock/launch slots',
                           ('overall cross-actor body until clock relation validated',), 'SYS_CNT_ticks')
    raise ValueError(f'Unknown backend: {backend}')
