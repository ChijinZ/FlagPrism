import hashlib
from functools import wraps
from pathlib import Path

from contextvars import ContextVar
from typing import ClassVar

from triton.compiler import CompiledKernel, LazyDict

from ..native import runtime_binding
from ..state import enter_state, exit_state
from .hook import Hook, HookManager

profiler_native = runtime_binding()

COMPUTE_METADATA_SCOPE_NAME = "__flagtree_profiler_launch_metadata"

op_name = ContextVar("op_name", default=None)
id = ContextVar("id", default=None)


def _json_value(value):
    if value is None or type(value) in (bool, int, str):
        return value
    if isinstance(value, float):
        import math
        return value if math.isfinite(value) else str(value)
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return {"status": "unavailable", "type": type(value).__name__}


def _argument(value):
    # Describe tensors on the host. Never synchronize, copy, or retain their data.
    try:
        if all(
                hasattr(value, field)
                for field in ("shape", "dtype", "stride")):
            return {
                "kind": "tensor",
                "shape": list(value.shape),
                "dtype": str(value.dtype),
                "stride": list(value.stride()),
                "device": str(value.device)
            }
        return {"kind": "scalar_or_metadata", "value": _json_value(value)}
    except Exception:
        # Triton also accepts pointer wrappers with only data_ptr and dtype.
        # Optional descriptions must not prevent an otherwise valid launch.
        return {"status": "unavailable", "type": type(value).__name__}


class LaunchHook(Hook):
    # Highest priority
    priority = 100
    # This is a singleton class
    _instance = None
    flops_width: ClassVar[list[int]] = [8, 16, 32, 64]
    metrics: ClassVar[list[str]] = [f"flops{width}" for width in flops_width
                                    ] + ["bytes", "flops"]

    binaries: ClassVar[dict] = {}
    launches: ClassVar[list] = []
    _metadata_wrapper = None
    _metadata_previous = None
    _metadata_state = None

    def __init__(self):
        pass

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def reset_capture(cls):
        cls.binaries.clear()
        cls.launches.clear()

    @classmethod
    def snapshot(cls, session):
        launches = [{
            key: value
            for key, value in row.items() if key != "session_ids"
        } for row in cls.launches if session in row["session_ids"]]
        identities = {row["binary_id"] for row in launches}
        return {
            "binaries":
            [row for key, row in cls.binaries.items() if key in identities],
            "launches":
            launches
        }

    @classmethod
    def record_launch(cls, metadata, scope_id, bridge):
        if bridge is None:
            return  # No compatible launch metadata; never associate by name.
        kernel = bridge["kernel"]
        key = kernel.hash
        if key not in cls.binaries:
            fn = getattr(kernel.src, "fn", None)
            python_fn = getattr(fn, "fn", None)
            code = getattr(python_fn, "__code__", None)
            source = getattr(fn, "src", None)
            file_text = None
            if code:
                try:
                    file_text = Path(code.co_filename).read_text()
                except (OSError, UnicodeError):
                    pass
            compiler_metadata = kernel.metadata._asdict()
            target = compiler_metadata.pop("target", None)
            cls.binaries[key] = {
                "id":
                key,
                "name":
                kernel.name,
                "identity":
                "compiler_cache_hash",
                "binary_sha256":
                hashlib.sha256(kernel.kernel).hexdigest(),
                "source": {
                    "path":
                    code.co_filename if code else None,
                    "line":
                    code.co_firstlineno if code else None,
                    "text":
                    source,
                    "sha256":
                    hashlib.sha256(source.encode()).hexdigest()
                    if source else None,
                    "file_snapshot":
                    file_text,
                    "file_sha256":
                    hashlib.sha256(file_text.encode()).hexdigest()
                    if file_text else None,
                    "file_snapshot_semantics":
                    "Source file as read during capture; kernel text above comes from the JIT object. External dependencies may require their original repository."
                },
                "compiler_metadata":
                _json_value(compiler_metadata),
                "compiler_artifacts": {
                    stage: text
                    for stage, text in kernel.asm.items()
                    if stage in {"ttir", "ttgir", "gcuir", "llir", "ptx"}
                    and isinstance(text, str)
                },
                "target": {
                    name: _json_value(getattr(target, name, None))
                    for name in ("backend", "arch", "warp_size")
                },
                "metadata_semantics": {
                    "target":
                    "Compiler target descriptor; target warp_size is backend-defined and not the launch block size.",
                    "compiler_metadata":
                    "Effective backend compiler settings; warp_size may describe a compiler lowering mode and differ from target.warp_size. Do not infer physical threads or occupancy from these fields.",
                    "launch_geometry":
                    "Use the captured activity grid/block for actual launch geometry."
                },
                "resource_notes":
                "Only compiler metadata is recorded; loader register/spill placeholders are not measurements."
            }
            from ..execution import build_manifest
            try:
                cls.binaries[key]["execution_manifest"] = _json_value(
                    build_manifest(kernel.asm, compiler_metadata, target, key))
            except Exception as error:
                # Optional mapping extraction cannot invalidate a real launch.
                # The error is preserved rather than asserting complete coverage.
                cls.binaries[key]["execution_manifest"] = {
                    "schema_version": 1,
                    "binary_id": key,
                    "status": "failed",
                    "reason": f"{type(error).__name__}: {error}",
                }
        arguments = {
            name: _argument(value)
            for name, value in bridge["arguments"].items()
        }
        cls.launches.append({
            "id":
            f"launch-{scope_id}",
            "scope_id":
            scope_id,
            "session_ids": [
                session
                for session, hooks in HookManager.session_hooks.items()
                if hooks.get(cls(), False)
            ],
            "name":
            metadata["name"],
            "binary_id":
            key,
            "grid":
            list(bridge["grid"]),
            "arguments":
            arguments
        })

    def init_handle(self, module, function, name: str, metadata_group: dict,
                    hash: str) -> None:
        pass

    def activate(self):
        cls = type(self)
        if cls._metadata_wrapper is not None:
            return
        previous = CompiledKernel.launch_metadata
        state = {"enabled": True}

        @wraps(previous)
        def launch_metadata(kernel, grid, stream, *args, **kwargs):
            metadata = previous(kernel, grid, stream, *args, **kwargs)
            if state["enabled"] and isinstance(metadata, LazyDict):
                fn = getattr(kernel.src, "fn", None)
                # Keep this private: existing LazyDict keys and user callbacks
                # remain unchanged for other hooks. Prewarmed kernels take this
                # same per-launch path without recompilation or load hooks.
                metadata._flagprism_launch_context = {
                    "kernel": kernel,
                    "grid": grid,
                    "arguments": dict(zip(getattr(fn, "arg_names", ()), args))
                }
            return metadata

        cls._metadata_previous = previous
        cls._metadata_state = state
        cls._metadata_wrapper = launch_metadata
        CompiledKernel.launch_metadata = launch_metadata

    def deactivate(self):
        cls = type(self)
        if cls._metadata_wrapper is None:
            return
        # A later third-party wrapper may still hold ours. Disable that closure
        # but never overwrite the third party's method when releasing ownership.
        cls._metadata_state["enabled"] = False
        if CompiledKernel.launch_metadata is cls._metadata_wrapper:
            CompiledKernel.launch_metadata = cls._metadata_previous
        cls._metadata_wrapper = None
        cls._metadata_previous = None
        cls._metadata_state = None

    def enter(self, metadata: LazyDict) -> None:
        if not isinstance(metadata, LazyDict):
            return  # Keep native activity capture without an unsupported scope.
        # Consume the private context before invoking user callbacks, including
        # their failure path. Retained metadata must not retain our arguments.
        bridge = metadata.__dict__.pop("_flagprism_launch_context", None)
        enter_state(COMPUTE_METADATA_SCOPE_NAME)
        try:
            lazy_metadata = metadata.get()
        finally:
            exit_state()
        fn_metrics = {
            k: lazy_metadata[k]
            for k in LaunchHook.metrics if k in lazy_metadata
        }
        op_name.set(lazy_metadata["name"])
        id.set(profiler_native.record_scope())
        self.record_launch(lazy_metadata, id.get(), bridge)
        # The exact per-launch LazyDict also reaches the debugger prepare
        # finalizer. This is an identity bridge, never a name/order join.
        metadata._flagprism_invocation_identity = {
            "invocation_id":
            f"launch-{id.get()}",
            "scope_id":
            id.get(),
            "binary_id":
            getattr(bridge.get("kernel"), "hash", None) if bridge else None,
            "evidence":
            "same_launch_metadata_object",
            "session_ids": [
                session
                for session, hooks in HookManager.session_hooks.items()
                if hooks.get(self, False)
            ],
        }
        profiler_native.enter_op(id.get(), lazy_metadata["name"])
        profiler_native.add_metrics(id.get(), fn_metrics)
        if bridge and getattr(profiler_native, "supports_cann_launch_receipts",
                              lambda: False)():
            kernel = bridge["kernel"]
            target = getattr(kernel.metadata, "target", None)
            if str(getattr(target, "backend",
                           "")).lower() in {"ascend", "cann", "npu"}:
                identity = metadata._flagprism_invocation_identity
                active = [
                    sid for sid in identity["session_ids"]
                    if profiler_native.cann_launch_receipts_active(sid)
                ]
                if len(active) > 1:
                    raise RuntimeError(
                        "CANN launch receipt requires one SDK collector owner")
                if active:
                    metadata._flagprism_cann_launch_receipt_v1 = (
                        profiler_native.make_cann_launch_receipt(
                            id.get(), active[0]))
                    identity[
                        "native_receipt_status"] = "queued_worker_receipt_pending"
                else:
                    identity[
                        "native_receipt_status"] = "native_sdk_collector_inactive"

    def exit(self, metadata: LazyDict) -> None:
        if not isinstance(metadata, LazyDict):
            return
        profiler_native.exit_op(id.get(), op_name.get())

    def abort_enter(self, metadata: LazyDict, error: BaseException) -> None:
        receipt = getattr(metadata, "_flagprism_cann_launch_receipt_v1", None)
        if receipt is not None:
            profiler_native.cancel_cann_launch_receipt(
                receipt, f"rejected_before_launch:{type(error).__name__}")
        identity = getattr(metadata, "_flagprism_invocation_identity", None)
        if identity:
            identity["status"] = "rejected_before_launch"
            for row in self.launches:
                if row["scope_id"] == identity["scope_id"]:
                    row["status"] = "rejected_before_launch"
                    row["error_type"] = type(error).__name__
                    break
        self.exit(metadata)
