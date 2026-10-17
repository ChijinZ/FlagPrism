"""CUDA allocation/completion transport for timeline_runtime owners."""


class CudaTimelineTransport:
    def __init__(self):
        import torch
        self.torch = torch

    def validate_target(self, *, device, stream):
        torch = self.torch
        if torch.cuda.current_device() != device:
            raise RuntimeError('Timeline launch device differs from the current CUDA device')
        actual = torch.cuda.ExternalStream(stream, device=device)
        with torch.cuda.stream(actual):
            if torch.cuda.is_current_stream_capturing():
                raise RuntimeError('Timeline CUDA graph capture is not supported')

    def plan_storage(self, plan, **kwargs):
        from .timeline_storage import plan_compact_storage
        return plan_compact_storage(plan, **kwargs)

    def allocate(self, owner):
        torch = self.torch
        device = owner['device']
        with torch.cuda.device(device):
            stream = torch.cuda.ExternalStream(owner['stream'], device=device)
            with torch.cuda.stream(stream):
                allocation = torch.empty(owner['physical_bytes'], dtype=torch.uint8,
                                         device=device)
            # Keep the allocating stream's memory ownership valid even if a
            # later external-stream operation fails. Pool also retains tensors.
            allocation.record_stream(stream)
            event = torch.cuda.Event(enable_timing=False)
        if allocation.data_ptr() % owner['layout']['alignment']:
            raise RuntimeError('CUDA allocator does not meet compiler scratch alignment')
        return {'allocation': allocation,
                'buffer': allocation[:owner['layout']['raw_bytes']],
                'stream': stream, 'event': event}

    def initialize(self, owner):
        resource = owner['resource']
        with self.torch.cuda.device(owner['device']), self.torch.cuda.stream(resource['stream']):
            resource['buffer'].zero_()
            if owner['guard_bytes']:
                resource['allocation'][owner['layout']['raw_bytes']:].fill_(165)

    def launch_buffer(self, owner):
        return owner['resource']['buffer']

    def record_completion(self, owner):
        with self.torch.cuda.device(owner['device']):
            owner['resource']['event'].record(owner['resource']['stream'])

    def completion_ready(self, owner):
        with self.torch.cuda.device(owner['device']):
            return owner['resource']['event'].query()

    def read_raw(self, owner):
        from .timeline_runtime import TimelineReadback
        resource = owner['resource']
        with self.torch.cuda.device(owner['device']), self.torch.cuda.stream(resource['stream']):
            result = resource['allocation'].cpu().numpy().tobytes()
        size = owner['layout']['raw_bytes']
        guard = result[size:]
        errors = (() if guard == bytes([165]) * owner['guard_bytes'] else
                  ('allocation_guard_changed',))
        return TimelineReadback(result[:size], guard, errors)

    def release(self, owner):
        owner['resource'] = None
