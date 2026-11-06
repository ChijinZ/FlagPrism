"""MetaX automatic native recorder with shared per-invocation ownership.

Records are local device counter observations. No NVIDIA timing, machine-map,
clock conversion or engine-busy qualification is reused by this backend.
"""
import functools
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from .timeline_late import LateTimelineHook
from .instrumentation import InstrumentationHook
from .timeline import TimelineAllocator, _persist
from ..timeline_metax_compile import MetaxLLVMTransform
from ..timeline_metax import MetaxTimelineTransport

class MetaxTimelineHook(LateTimelineHook):
    _function_metadata_paths = {}
    _function_observation_metadata = {}
    timeline_cache_options = ':metax_native_timeline=1'

    def __init__(self, mode_obj, *, observation_plan, staging_base):
        from ..mode import Default
        self._late_base = Path(staging_base)
        self._late_objects = self._late_base.with_suffix('.late-objects')
        self._late_objects.mkdir(parents=True, exist_ok=True)
        tool = Path(__file__).resolve().parents[1] / '_bin/metax-timeline'
        self._late_transform = MetaxLLVMTransform(tool, self._late_base.with_suffix('.late-compiles'), max_sites=observation_plan['max_sites'], capacity=observation_plan.get('record_capacity'))
        InstrumentationHook.__init__(self, Default(buffer_size=32768), observation_plan=observation_plan)

    def _init_timeline(self):
        capacity = self._late_transform.capacity or 4096
        budget = max(8 * 1024 * 1024,2 * 4 * (6 + 4 * capacity) * 8 + 128)
        self._init_timeline_state(MetaxTimelineTransport(), guard_bytes=128, max_pending_bytes=budget)
        self.allocator = TimelineAllocator(self)

    def _timeline_fingerprint(self):
        return hashlib.sha256(json.dumps(dict(tool=self._late_transform.cache_identity, hook=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()), sort_keys=True).encode()).hexdigest()

    def activate(self):
        from triton.backends.metax.compiler import MACABackend
        from triton.runtime.jit import JITFunction
        from triton.runtime import _allocation
        from ..flags import set_instrumentation_on
        if getattr(MACABackend,'optimized_llvm_transform_version',None)!=1:
            raise RuntimeError('MetaX requires the packaged optimized LLVM compiler/launch patch')
        if InstrumentationHook.active_count:
            raise RuntimeError('Another instrumentation backend is active')
        self._timeline_cache_key=self._timeline_fingerprint()
        self._previous_compiler=MACABackend.instrumentation
        self._previous_allocator=_allocation._profile_allocator.get()
        self._previous_run=JITFunction.run
        MACABackend.instrumentation=SimpleNamespace(transform_optimized_llvm=self._late_transform)
        _allocation.set_profile_allocator(self.allocator)
        activation={'enabled':True};self._run_activation=activation
        previous=self._previous_run
        @functools.wraps(previous)
        def wrapped(jit,*args,**kwargs):
            if not activation['enabled']:return previous(jit,*args,**kwargs)
            self.timeline_pool._check_thread()
            kwargs['instrumentation_mode']='flagprism_metax_timeline_v1:'+self._timeline_cache_key
            try:return previous(jit,*args,**kwargs)
            except BaseException as error:
                self._timeline_abort(error);raise
        self._installed_run=wrapped;JITFunction.run=wrapped
        self._activated=True;InstrumentationHook.active_count+=1;set_instrumentation_on()

    def deactivate(self):
        from triton.backends.metax.compiler import MACABackend
        from triton.runtime.jit import JITFunction
        from triton.runtime import _allocation
        from ..flags import set_instrumentation_off
        if self._run_activation is not None:self._run_activation['enabled']=False
        if not self._activated:return
        if JITFunction.run is self._installed_run:JITFunction.run=self._previous_run
        MACABackend.instrumentation=self._previous_compiler
        _allocation.set_profile_allocator(self._previous_allocator)
        self._activated=False;InstrumentationHook.active_count-=1;set_instrumentation_off()

    def _decode_timeline_original(self,identity,directory,deadline):
        from ..timeline_capture_store import load_capture
        from ..timeline_events_metax import canonicalize_metax_capture
        capture=load_capture(directory,self._timeline_pending[identity]);owner=capture['owner']
        raw=(directory/capture['raw_file']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=capture['raw_sha256']:raise RuntimeError('MetaX retained raw changed')
        if owner['submission_outcome']=='returned':
            canonical=canonicalize_metax_capture(raw,owner=owner,metadata=capture['metadata'])
            events_file=str((Path('captures')/identity).with_suffix('.events.json'))
            _persist(directory/events_file,json.dumps(canonical,separators=(',',':')).encode())
            from ..timeline_metax_perfetto import write_counter_tick_exports
            capture['counter_tick_exports']=write_counter_tick_exports(directory,Path('captures')/identity,canonical)
            capture.update(capture_status='raw_complete' if canonical['complete'] else 'incomplete',events_file=events_file,record_backend='metax-late-1',counter_ns_status={'status':'unavailable','reason':'MetaX counter period/alignment not qualified'})
        else:capture['capture_status']='aborted'
        prefix=Path('captures')/identity
        from ..timeline_capture_store import persist_capture
        # The original helper updates the common capture ledger and preserves its raw bindings.
        persist_capture(directory,str(prefix.with_suffix('.json')),capture)
        self._timeline_rows.append(dict(invocation_id=identity,capture_id=owner['capture_id'],binary_id=owner['binary_id'],capture_file=str(prefix.with_suffix('.json')),capture_status=capture['capture_status']))
        del self._timeline_pending[identity]
