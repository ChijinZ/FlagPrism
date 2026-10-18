"""NVIDIA default late recorder with common per-invocation owner lifecycle.

Raw observer issue/checkpoint events are distinct from final-machine timing,
clock comparability, engine busy and source-region cost qualifications.
"""
import base64
import copy
import hashlib
import importlib
import json
from pathlib import Path
import time
import zlib

from .instrumentation import InstrumentationHook
from .timeline import TimelineAllocator, _persist
from ..timeline_nvidia_late_compile import LateLLVMTransform
from ..timeline_nvidia_late_storage import LateCudaTimelineTransport


class LateTimelineHook(InstrumentationHook):
    profile_buffer_alignment = 8
    timeline_cache_options = ':timeline_stage=optimized_llvm:late_record=1:late_layout=1:late_transform=2'
    _function_metadata_paths = {}
    _function_observation_metadata = {}

    def __init__(self, mode_obj, *, observation_plan, staging_base):
        if observation_plan['output_selection']['programs'] is not None:
            raise ValueError(
                'Automatic late timeline selects runtime first/last programs')
        self._late_base = Path(staging_base)
        self._late_objects = self._late_base.with_suffix('.late-objects')
        self._late_objects.mkdir(parents=True, exist_ok=True)
        tool = Path(__file__).resolve().parents[1] / '_bin/late-timeline'
        self._late_transform = LateLLVMTransform(
            tool,
            self._late_base.with_suffix('.late-compiles'),
            max_sites=observation_plan['max_sites'])
        super().__init__(mode_obj, observation_plan=observation_plan)

    def _init_timeline(self):
        self._init_timeline_state(LateCudaTimelineTransport(),
                                  guard_bytes=128,
                                  max_cumulative_raw_bytes=8 * 1024 * 1024)
        self.allocator = TimelineAllocator(self)

    def _timeline_fingerprint(self):
        from triton.backends.nvidia.compiler import CUDABackend
        if getattr(CUDABackend, 'optimized_llvm_transform_version', None) != 1:
            raise RuntimeError(
                'Install optimized-llvm.patch and the matching packaged late recorder'
            )
        inherited = super()._timeline_fingerprint()
        from .. import timeline_nvidia_late_compile, timeline_nvidia_late_raw
        from .. import timeline_nvidia_late_storage, timeline_storage
        from .. import timeline_nvidia_late_async, timeline_nvidia_late_model
        modules = [
            importlib.import_module(CUDABackend.__module__),
            timeline_nvidia_late_compile, timeline_nvidia_late_raw,
            timeline_nvidia_late_storage, timeline_storage,
            timeline_nvidia_late_async, timeline_nvidia_late_model
        ]
        hashes = [
            hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()
            for m in modules
        ]
        return hashlib.sha256(
            json.dumps(dict(inherited=inherited,
                            hook_sha256=hashlib.sha256(
                                Path(__file__).read_bytes()).hexdigest(),
                            modules=hashes,
                            transform=self._late_transform.cache_identity),
                       sort_keys=True).encode()).hexdigest()

    def activate(self):
        super().activate()
        from triton.backends import backends
        # Parent early hooks still exist for legacy/census clients. This capture
        # registers no early scopes or conversion passes, only the O3 callback.
        backends['nvidia'].compiler.instrumentation.manager = {
            'optimized_llvm': self._late_transform
        }

    def init_handle(self, module, function, name, metadata_group, hash):
        if not function:
            return
        metadata_path = next(
            (path
             for key, path in metadata_group.items() if key.endswith('json')),
            None)
        if metadata_path is None:
            raise RuntimeError(
                'Late timeline requires actual compiled metadata')
        compiler = json.loads(Path(metadata_path).read_text())
        plan = copy.deepcopy(compiler.get('flagprism_late_manifest'))
        if not isinstance(plan, dict):
            raise RuntimeError(
                'Loaded binary lacks its late recording manifest')
        binding = plan.get('compiler_binding') or {}
        if binding.get('tool_sha256') != self._late_transform.tool_sha256:
            raise RuntimeError(
                'Loaded late executable binding differs from this capture')
        llvm_path = next(
            (path
             for key, path in metadata_group.items() if key.endswith('llir')),
            None)
        if llvm_path is None or hashlib.sha256(Path(llvm_path).read_bytes(
        )).hexdigest() != binding.get('output_sha256'):
            raise RuntimeError(
                'Loaded optimized LLVM differs from its late manifest')
        # Original optimized IR travels in the compiler cache as compressed data,
        # so a warm binary does not depend on an earlier session's staging dir.
        encoded = compiler.pop('flagprism_late_ordinary_llvm_zlib_b64', None)
        if not isinstance(encoded, str):
            raise RuntimeError(
                'Loaded late metadata lacks retained ordinary LLVM')
        compressed = base64.b64decode(encoded, validate=True)
        inflater = zlib.decompressobj()
        original = inflater.decompress(compressed, 16 * 1024 * 1024 + 1)
        if (len(original) > 16 * 1024 * 1024 or not inflater.eof
                or inflater.unused_data or inflater.unconsumed_tail
                or hashlib.sha256(original).hexdigest()
                != binding.get('input_sha256')):
            raise RuntimeError('Retained ordinary LLVM provenance is invalid')
        # Cached JSON alone cannot authorize a smaller allocation than the
        # native producer. Reconstruct it with this capture's executable/options.
        verified = {}
        reconstructed = self._late_transform(original.decode('utf-8'),
                                             verified)
        expected_plan = verified['flagprism_late_manifest']
        supplied = {
            key: value
            for key, value in plan.items() if key != 'compiler_binding'
        }
        expected = {
            key: value
            for key, value in expected_plan.items()
            if key != 'compiler_binding'
        }
        actual_llvm = Path(llvm_path).read_text()
        if (supplied != expected
                or not actual_llvm.startswith("; ModuleID = '")
                or not reconstructed.startswith("; ModuleID = '")
                or actual_llvm.split('\n', 1)[1] != reconstructed.split(
                    '\n', 1)[1]):
            raise RuntimeError(
                'Cached late layout/LLVM does not match actual native producer reconstruction'
            )
        object_root = self._late_objects / hashlib.sha256(
            hash.encode()).hexdigest()
        original_path = object_root / 'ordinary.ll'
        _persist(original_path, original)
        plan['binary_id'] = hash
        from ..timeline_nvidia_late_storage import plan_late_storage
        plan_late_storage(plan,
                          grid=(1, 1, 1),
                          scratch_size=compiler['profile_scratch_size'],
                          alignment=compiler['profile_scratch_align'],
                          num_ctas=compiler['num_ctas'])
        prefix = 'binaries/' + hashlib.sha256(hash.encode()).hexdigest()
        artifacts = []
        source_paths = set()
        for site in plan['sites']:
            for member in site.get('members', []):
                file = member.get('file')
                if isinstance(file, str) and file:
                    path = Path(member.get('directory') or '') / file
                    if path.is_file():
                        source_paths.add(path)
        paths = [Path(p) for p in metadata_group.values()
                 ] + [original_path] + sorted(source_paths)
        for index, path in enumerate(paths):
            if path.is_file():
                artifacts.append(
                    dict(path=str(path),
                         sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                         retained_file=prefix + '/' + str(index) +
                         path.suffix))
        self.metadata_path[function] = metadata_path
        self.observation_metadata[function] = dict(
            binary_id=hash,
            automatic_plan=plan,
            compiler_metadata=compiler,
            timeline_artifacts=artifacts,
            late_metadata_group=dict(metadata_group),
            late_name=name,
            late_binding_capture_id=self.timeline_pool.capture_id,
            scope_id_names=[],
            scope_id_parents=[],
            scope_id_origins={},
            scope_origin_sources={},
            compiler_ir_sha256=binding['output_sha256'])

    def _before_timeline_admission(self, function):
        metadata = self.observation_metadata.get(function)
        if metadata is not None and metadata.get(
                'late_binding_capture_id') != self.timeline_pool.capture_id:
            self.init_handle(None, function, metadata['late_name'],
                             metadata['late_metadata_group'],
                             metadata['binary_id'])
        directory = self._late_base.with_suffix('.timeline').resolve()
        deadline = time.monotonic() + 60
        for identity in tuple(self.timeline_pool.invocation_ids):
            if self.timeline_pool.completion_ready_now(identity):
                self._retain_timeline_original(identity, directory, deadline)

    def _decode_timeline_original(self, identity, directory, deadline):
        from ..timeline_nvidia_late_raw import decode_late_raw
        capture = json.loads(
            (directory / self._timeline_pending[identity]).read_text())
        owner = capture['owner']
        raw = (directory / capture['raw_file']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != capture['raw_sha256']:
            raise RuntimeError('Retained late timeline raw changed')
        guard = capture.get('readback_guard')
        if guard is not None:
            data = (directory / guard['file']).read_bytes()
            if len(data) != guard['bytes'] or hashlib.sha256(
                    data).hexdigest() != guard['sha256']:
                raise RuntimeError('Retained late guard changed')
        if owner.get('readback_integrity', {}).get('status') == 'invalid':
            raise ValueError('Late timeline readback integrity failed: ' +
                             repr(owner['readback_integrity']))
        prefix = Path('captures') / identity
        capture['capture_status'] = 'aborted'
        if owner['submission_outcome'] == 'returned':
            decoded = decode_late_raw(owner['plan'],
                                      raw,
                                      slots=owner['layout']['slots'])
            capture['capture_status'] = 'raw_complete' if decoded[
                'complete'] else 'incomplete'
            capture['decoded_file'] = str(
                prefix.with_suffix('.late-decoded.json'))
            _persist(directory / capture['decoded_file'],
                     json.dumps(decoded, separators=(',', ':')).encode())
            from ..timeline_nvidia_late_async import derive_late_async
            facts = derive_late_async(decoded,
                                      owner['plan'],
                                      shared_bytes=capture['metadata']
                                      ['compiler_metadata']['shared'])
            capture['async_file'] = str(prefix.with_suffix('.late-async.json'))
            _persist(directory / capture['async_file'],
                     json.dumps(facts, separators=(',', ':')).encode())
        capture['record_backend'] = 'nvidia-late-1'
        capture['counter_ns_status'] = dict(
            status='unavailable',
            reason=
            'Final-machine timestamp binding for late recorder is not yet qualified'
        )
        _persist(directory / prefix.with_suffix('.json'),
                 (json.dumps(capture, indent=2) + '\n').encode())
        self._timeline_rows.append(
            dict(invocation_id=identity,
                 capture_id=owner['capture_id'],
                 binary_id=owner['binary_id'],
                 capture_file=str(prefix.with_suffix('.json')),
                 capture_status=capture['capture_status']))
        del self._timeline_pending[identity]
