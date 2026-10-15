"""Reject unsupported detailed graph instrumentation before runtime side effects."""
from __future__ import annotations

import importlib

_BACKENDS = {
    **dict.fromkeys(('ascend', 'cann', 'npu'), ('torch_npu', 'npu', 'Ascend', 'NPU')),
    **dict.fromkeys(('enflame', 'gcu', 'tops'), ('torch_gcu', 'gcu', 'Enflame', 'GCU')),
}


def require_eager(backend, *, stream=None):
    """Query the actual launch stream using the backend's public capture API.

    Missing/failed/indeterminate queries are unsafe to treat as eager. Other
    backends never import these provider extensions. No query result is cached across launches.
    """
    adapter = _BACKENDS.get(str(backend or '').lower())
    if adapter is None:
        return
    extension, runtime_name, vendor, device_name = adapter
    try:
        import torch
        importlib.import_module(extension)
        runtime = getattr(torch, runtime_name)
        query = runtime.is_current_stream_capturing
        if stream is None:
            capturing = query()
        else:
            # launch_context supplies the actual SDK handle, which need not be
            # the thread's current stream. The context restores it on failure.
            current_stream = getattr(runtime, 'current_stream', None)
            current = current_stream() if current_stream is not None else None
            handle_name = 'npu_stream' if runtime_name == 'npu' else 'gcu_stream'
            current_handle = getattr(current, handle_name, None)
            if current_handle is not None and int(current_handle) == int(
                    stream):
                capturing = query()
            else:
                external_stream = getattr(runtime, 'ExternalStream', None)
                if external_stream is None:
                    raise AttributeError(
                        f'{device_name} provider cannot wrap a non-current launch '
                        'stream; make that stream current before detailed profiling'
                    )
                with runtime.stream(external_stream(int(stream))):
                    capturing = query()
    except Exception as error:
        raise RuntimeError(
            f'FlagPrism {vendor} detailed profiling cannot verify {device_name} stream '
            'capture state; refusing instrumentation before buffer preparation'
        ) from error
    if type(capturing) is not bool:
        raise RuntimeError(
            f'FlagPrism {vendor} detailed profiling received an indeterminate '
            f'{device_name} stream capture state; refusing instrumentation')
    if capturing:
        raise RuntimeError(
            f'FlagPrism {vendor} detailed profiling supports eager launches only; '
            f'{device_name} graph capture is unsupported. Exit graph capture before '
            'starting or running a detailed profiling session.')
