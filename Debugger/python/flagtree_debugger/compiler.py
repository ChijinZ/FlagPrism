"""FlagPrism debugger: TTIR pass orchestration and compile-time metadata keys."""
from __future__ import annotations

import json
import os

from triton._C.libtriton import ir, passes

from .native import compiler_binding

_instrumentation_mode = ""
# Compiler lowering changes must invalidate both automatic and advanced caches.
GCU_DYNAMIC_LOWERING_REVISION = 2
_DISABLED_BUILD_MESSAGE = (
    "FlagPrism debugger compiler support is unavailable. Reinstall FlagTree "
    "with `TRITON_BUILD_FLAGPRISM=ON`.")


def set_instrumentation_mode(mode: str) -> None:
    global _instrumentation_mode
    _instrumentation_mode = str(mode or "")


def get_instrumentation_mode() -> str:
    return _instrumentation_mode


def _instrumentation_kind(mode: str | None = None) -> str:
    value = get_instrumentation_mode() if mode is None else str(mode)
    return value.split("|", 1)[0]


def _gcu_publication_config(config):
    result = dict(config)
    request = result.get("debug_observation_request")
    if isinstance(request, dict) and request.get("semantics") == [
            "source_control_interval"
    ]:
        mode = os.environ.get(
            "FLAGPRISM_GCU_DYNAMIC_PUBLISHER", "vector16_per_work_item"
            if request.get("automatic") else "scalar16")
        if mode not in {"scalar16", "vector16_per_work_item"}:
            raise ValueError("Unknown GCU dynamic publisher mode")
        result["debug_dynamic_publication_mode"] = mode
        result[
            "debug_dynamic_lowering_revision"] = GCU_DYNAMIC_LOWERING_REVISION
        if request.get("automatic"):
            from .automatic_plan import (AUTOMATIC_PLAN_VERSION,
                                         CONTROL_FLOW_METADATA_VERSION)
            result["debug_automatic_plan_version"] = AUTOMATIC_PLAN_VERSION
            result[
                "debug_control_flow_metadata_version"] = CONTROL_FLOW_METADATA_VERSION
    return result


def _frozen_gcu_publication_mode(metadata):
    mode = str(metadata.get("instrumentation_mode", ""))
    if "|config=" not in mode:
        raise ValueError(
            "GCU publication requires frozen compiler option identity")
    config = json.loads(mode.split("|config=", 1)[1])
    publisher = config.get("debug_dynamic_publication_mode")
    if publisher not in {"scalar16", "vector16_per_work_item"}:
        raise ValueError(
            "GCU publication mode missing from compiler option identity")
    return publisher


def apply_compile_options(options: dict) -> None:
    provided = options.get("instrumentation_mode")
    if provided:
        from .api import current_compile_config
        request = current_compile_config().get("debug_observation_request")
        if not (_instrumentation_kind(str(provided)).startswith("debugger")
                and isinstance(request, dict)
                and request.get("semantics") == ["source_control_interval"]):
            return
    mode = str(provided) if provided else get_instrumentation_mode()
    if not mode:
        try:
            from .api import is_active

            mode = "debugger" if is_active() else ""
        except Exception:
            mode = ""
    if not mode:
        return
    from . import __version__
    from .api import current_compile_config

    config = json.dumps(_gcu_publication_config(current_compile_config()),
                        sort_keys=True,
                        separators=(",", ":"))
    options["instrumentation_mode"] = (
        f"{_instrumentation_kind(mode)}|flagtree-debugger={__version__}|config={config}"
    )


def _get_debug_passes():
    return compiler_binding()


def load_dialects(context) -> None:
    binding = _get_debug_passes()
    callback = getattr(binding, "load_dialects",
                       None) if binding is not None else None
    if not callable(callback):
        raise RuntimeError(_DISABLED_BUILD_MESSAGE)
    callback(context)


def _run_pass_manager(pm, mod, description: str) -> None:
    try:
        pm.run(mod, description)
    except TypeError:
        pm.run(mod)


def _target_backend(metadata: dict) -> str:
    target = metadata.get("target")
    if isinstance(target, dict):
        backend = target.get("backend")
    else:
        backend = getattr(target, "backend", None)
    return str(backend or "").lower()


def _debug_launch_hidden_arg_enabled(metadata: dict) -> bool:
    if _target_backend(metadata) not in {
            "ascend",
            "cann",
            "npu",
            "tianshu",
            "corex",
            "iluvatar",
            "mthreads",
            "musa",
            "gcu",
            "enflame",
    }:
        return False
    # Keep the environment variable as a compatibility hook for subprocesses
    # and older scripts, but make the Python debugger API the normal path.
    if os.environ.get("TRITON_FLAGTREE_DEBUG_LAUNCH_PTR", "") == "1":
        return True
    try:
        from . import api as debugger

        return debugger.is_active()
    except Exception:
        return False


def _kernel_internal_timeline_supported() -> bool:
    try:
        import triton

        backend = str(
            triton.runtime.driver.active.get_current_target().backend).lower()
    except Exception:
        return False
    # Tianshu/CoreX and MThreads/MUSA do not expose the Ascend SYS_CNT
    # instruction used by the current device-cycle timeline implementation.
    return backend in {"ascend", "npu", "cann", "gcu", "enflame"}


def _finish_metadata_only_tensor_pointer_debug(fd, mod,
                                               metadata: dict) -> bool:
    # GCU's source-control interval observer only reads the device clock and
    # publishes its own buffer.  It never materializes a block-pointer value or
    # computes an address summary, so block pointers can use the normal path.
    if (_target_backend(metadata) in {"gcu", "enflame"}
            and metadata.get("debug_dynamic_index_bits") == 32):
        return False
    has_tensor_pointer = getattr(fd, "has_triton_tensor_pointer_types", None)
    if has_tensor_pointer is None or not has_tensor_pointer(mod):
        return False

    if not fd.assign_debug_collect_scope_ids_without_erase(mod):
        raise RuntimeError("failed to resolve debug collect scopes")
    assign_metadata = getattr(
        fd, "assign_debug_op_ids_and_metadata_without_pass_manager", None)
    erase_markers = getattr(fd, "erase_debug_collect_markers", None)
    if assign_metadata is None or erase_markers is None:
        raise RuntimeError(
            "debug tensor-pointer metadata fallback is unavailable")
    if not assign_metadata(mod):
        raise RuntimeError("failed to assign debug op ids")
    erase_markers(mod)

    tracked_table_json = fd.get_debug_tracked_op_table_json(mod)
    kernel_metadata_json = fd.get_debug_kernel_metadata_json(mod)
    metadata["debug_kernel_id"] = fd.get_debug_kernel_id(mod)
    metadata["debug_metadata_json"] = kernel_metadata_json
    metadata["debug_tracked_table"] = json.loads(tracked_table_json)
    metadata["debug_records_per_instance"] = 0
    metadata["debug_record_size"] = 64
    metadata["debug_record_layout"] = ""
    metadata["debug_record_plan"] = []
    metadata["debug_launch_hidden_arg"] = False
    metadata["debug_metadata_only_reason"] = "triton_tensor_pointer"
    return True


def run_ttir_debug_passes_if_needed(mod, metadata: dict) -> None:
    """If the module contains debug collect markers, run debug passes and set metadata."""
    fd = _get_debug_passes()
    if fd is None:
        if _instrumentation_kind().startswith("debugger"):
            raise RuntimeError(_DISABLED_BUILD_MESSAGE)
        return
    has_markers = fd.has_debug_collect_markers(mod)
    auto_collect = _instrumentation_kind() in {
        "debugger_auto", "debugger_auto_numeric"
    }

    if auto_collect:
        if _target_backend(metadata) in {"gcu", "enflame"}:
            from .automatic_plan import CONTROL_FLOW_METADATA_VERSION
            if getattr(fd, "CONTROL_FLOW_METADATA_VERSION",
                       0) != CONTROL_FLOW_METADATA_VERSION:
                raise RuntimeError(
                    "Automatic GCU profiling requires matching compiler control-flow and entry-context metadata; rebuild and install FlagTree/FlagPrism together"
                )
        if not has_markers and _target_backend(metadata) in {"gcu", "enflame"}:
            # Discover operations in ordinary JIT helpers before assigning
            # entry-function scope/site IDs. Inlining after metadata loses
            # helper operations because the metadata pass excludes callees.
            inline_pm = ir.pass_manager(mod.context)
            passes.common.add_inliner(inline_pm)
            passes.common.add_symbol_dce(inline_pm)
            _run_pass_manager(inline_pm, mod, "flagtree_debug_auto_inline")
        try:
            from . import api as debugger

            debug_config = debugger.current_compile_config()
        except Exception:
            debug_config = {}
        level = int(debug_config.get("debug_record_level", 1))
        addr_level = int(debug_config.get("debug_addr_level", 0))
        has_markers = bool(
            fd.insert_default_debug_collect_markers(mod, level, addr_level))

    if not has_markers:
        metadata["debug_enabled"] = False
        metadata["debug_launch_hidden_arg"] = False
        return
    try:
        from . import api as debugger

        debug_config = debugger.current_compile_config()
    except Exception:
        debug_config = {}

    metadata["debug_enabled"] = True
    request = debug_config.get("debug_observation_request")
    if request is not None and _target_backend(metadata) in {
            "ascend", "cann", "npu"
    }:
        programs = request.get("programs")
        if not isinstance(programs, list) or len(programs) != 1:
            raise ValueError(
                "Ascend actor trace requires exactly one logical program")
        if request.get("sites") is not None or request.get(
                "sample_every") != 1:
            raise ValueError(
                "Ascend late trace currently requires all sites and sample_every=1"
            )
        if not set(request.get("semantics", [])) <= {
                "issue", "wait_bracket", "control_checkpoint",
                "operation_checkpoint"
        }:
            raise ValueError(
                "Ascend late trace provides issue, wait_bracket, control_checkpoint and operation_checkpoint"
            )
        # Resolve source metadata before erasing markers; late recording itself
        # observes actual post-lowering native sites, whose source relation may
        # remain partial after the vendor compiler.
        metadata_pm = ir.pass_manager(mod.context)
        fd.add_resolve_debug_scope(metadata_pm)
        fd.add_assign_debug_op_id(metadata_pm)
        passes.common.add_inliner(metadata_pm)
        passes.common.add_symbol_dce(metadata_pm)
        _run_pass_manager(metadata_pm, mod,
                          "flagtree_late_observation_metadata")
        metadata["debug_metadata_json"] = fd.get_debug_kernel_metadata_json(
            mod)
        metadata["debug_tracked_table"] = json.loads(
            fd.get_debug_tracked_op_table_json(mod))
        metadata["debug_kernel_id"] = fd.get_debug_kernel_id(mod)
        index = fd.prepare_late_observation_abi(mod)
        capacity = request["max_events_per_instance"]
        if capacity > (2**32 - 2) // 3:
            raise ValueError(
                "Ascend actor trace allocation exceeds protocol capacity")
        metadata.update({
            "debug_launch_hidden_arg":
            True,
            "debug_protocol_version":
            2,
            "debug_record_level":
            1,
            "debug_record_size":
            64,
            "debug_record_layout":
            "ascend_actor_dynamic_v1",
            "debug_records_per_instance":
            0,
            "debug_record_capacity":
            3 * capacity + 1,
            "debug_export_mode":
            "POST_KERNEL_EXPORT",
            "debug_record_plan": [],
            "flagprism_ascend_trace_source_argument_index":
            int(index),
            "flagprism_ascend_trace_capacity":
            capacity,
            "flagprism_ascend_trace_program":
            programs[0],
            "flagprism_ascend_observation_request":
            request,
        })
        if request.get("automatic"):
            metadata["flagprism_ascend_trace_max_sites"] = request["max_sites"]
        return
    if _target_backend(metadata) in {"gcu", "enflame"}:
        # Selects the read-only SDK helper during the actual backend lowering.
        # Frequency is unknown: raw ticks must not be converted to time.
        metadata["debug_clock_domain"] = "enflame.sdk.global_timer"
        metadata["debug_clock_bits"] = 46
        metadata["debug_clock_unit"] = "tick"
    metadata["debug_protocol_version"] = 2
    metadata["debug_record_level"] = int(
        debug_config.get("debug_record_level", 1))
    metadata["debug_addr_level"] = int(debug_config.get("debug_addr_level", 0))
    metadata["debug_export_mode"] = debug_config.get("debug_export_mode",
                                                     "POST_KERNEL_EXPORT")
    if "debug_record_capacity" in debug_config:
        metadata["debug_record_capacity"] = int(
            debug_config["debug_record_capacity"])
    metadata["debug_launch_hidden_arg"] = _debug_launch_hidden_arg_enabled(
        metadata)
    fd.set_debug_kernel_id_seed(mod, str(metadata.get("hash") or ""))
    fd.set_debug_hidden_arg_abi_enabled(
        mod, bool(metadata["debug_launch_hidden_arg"]))
    fd.set_debug_addr_level(mod, int(metadata["debug_addr_level"]))
    timeline_supported = (_instrumentation_kind() == "debugger_auto"
                          and _kernel_internal_timeline_supported())
    fd.set_debug_timeline_enabled(mod, bool(auto_collect
                                            and timeline_supported))
    fd.set_debug_timeline_only(mod, bool(auto_collect and timeline_supported))
    request = debug_config.get("debug_observation_request")
    if request is not None:
        if _target_backend(metadata) not in {"gcu", "enflame"}:
            raise ValueError(
                "Dynamic Debugger observation requests currently require the GCU backend"
            )
        programs = request.get("programs")
        if not isinstance(programs, list) or len(programs) != 1:
            raise ValueError(
                "GCU selected trace requires exactly one logical program")
        if request.get("semantics") != ["source_control_interval"]:
            raise ValueError(
                "GCU IR trace provides source_control_interval only")
        if type(programs[0]) is not int or not 0 <= programs[0] <= 0x7fffffff:
            raise ValueError(
                "GCU selected program must fit validated signed 32-bit indexing"
            )
        metadata["debug_dynamic_index_bits"] = 32
        metadata["debug_clock_carrier"] = "llvm_i64_words"
        fd.set_debug_dynamic_timeline_options(mod, programs[0], 0,
                                              request["sample_every"])
        if request.get("sites") is not None:
            fd.set_debug_dynamic_timeline_sites(mod, request["sites"])
        publisher = _frozen_gcu_publication_mode(metadata)
        source_work_items = metadata.get("num_warps")
        if publisher == "vector16_per_work_item":
            if type(source_work_items) is not int or source_work_items <= 0:
                raise ValueError(
                    "GCU vector publication requires actual compiler work-item configuration"
                )
            fd.set_debug_dynamic_publication_work_items(mod, source_work_items)
            metadata["debug_dynamic_publication"] = "per_work_item_vector16_v1"
            metadata[
                "debug_dynamic_publication_work_items"] = source_work_items
        elif publisher == "scalar16":
            metadata["debug_dynamic_publication"] = "scalar16_v1"
            metadata[
                "debug_dynamic_publication_work_items"] = source_work_items
        else:
            raise ValueError("Unknown GCU dynamic publisher mode")
        metadata[
            "debug_dynamic_publication_config_basis"] = "GCU compiler configuration num_warps denotes work-items"
        metadata["debug_dynamic_selected_sites"] = request.get("sites")
        metadata["debug_dynamic_clock_sampling"] = "region_free_sites_only"
        metadata["debug_dynamic_selected_program"] = programs[0]
        metadata["debug_dynamic_selected_actor"] = 0
        metadata["debug_dynamic_sample_every"] = request["sample_every"]
        metadata["debug_dynamic_attempted_total_offset"] = 24

    if _finish_metadata_only_tensor_pointer_debug(fd, mod, metadata):
        return

    metadata_pm = ir.pass_manager(mod.context)
    metadata_pm.enable_debug()
    fd.add_resolve_debug_scope(metadata_pm)
    fd.add_assign_debug_op_id(metadata_pm)
    # Debug collect markers in called helper functions are ignored by the
    # metadata pass to avoid call-graph id propagation.  After those markers are
    # erased, run the regular inliner so helper calls such as FlagGems
    # triton_lang_extension.program_id return to the call-free TTIR shape that
    # Ascend's ttadapter path expects.
    passes.common.add_inliner(metadata_pm)
    passes.common.add_symbol_dce(metadata_pm)
    _run_pass_manager(metadata_pm, mod, "flagtree_debug_collect_metadata")

    tracked_table_json = fd.get_debug_tracked_op_table_json(mod)
    kernel_metadata_json = fd.get_debug_kernel_metadata_json(mod)
    metadata["debug_kernel_id"] = fd.get_debug_kernel_id(mod)
    metadata["debug_metadata_json"] = kernel_metadata_json
    metadata["debug_tracked_table"] = json.loads(tracked_table_json)
    if request is not None and request.get("automatic"):
        from .automatic_plan import plan_operations
        plan = plan_operations(metadata["debug_tracked_table"],
                               request["max_sites"])
        fd.set_debug_dynamic_timeline_sites(mod, plan["selected_sites"])
        metadata["debug_dynamic_selected_sites"] = plan["selected_sites"]
        metadata["debug_automatic_plan"] = plan

    instrumentation_pm = ir.pass_manager(mod.context)
    instrumentation_pm.enable_debug()
    fd.add_insert_instrumentation(instrumentation_pm)
    passes.common.add_cse(instrumentation_pm)
    passes.common.add_canonicalizer(instrumentation_pm)
    try:
        _run_pass_manager(instrumentation_pm, mod, "flagtree_debug_collect")
    except RuntimeError as error:
        if request is not None and request.get("sites") is not None:
            diagnostic = fd.get_debug_dynamic_timeline_site_error(mod)
            if diagnostic:
                raise ValueError(diagnostic) from error
        raise
    metadata["debug_records_per_instance"] = int(
        fd.get_debug_records_per_instance(mod))
    metadata["debug_record_size"] = int(fd.get_debug_record_size(mod))
    metadata["debug_record_layout"] = fd.get_debug_record_layout(mod)
    metadata["debug_record_plan"] = json.loads(
        fd.get_debug_record_plan_json(mod))
    metadata["debug_full_dump_payload_bytes_per_instance"] = int(
        fd.get_debug_full_dump_payload_bytes_per_instance(mod))
    metadata["debug_full_dump_plan"] = json.loads(
        fd.get_debug_full_dump_plan_json(mod))
    metadata["debug_host_summary_bundles"] = (
        _target_backend(metadata) in {"gcu", "enflame"}
        and metadata["debug_full_dump_payload_bytes_per_instance"] > 0)
    if (metadata["debug_records_per_instance"] <= 0 and
            metadata["debug_record_layout"] != "selected_dynamic_timeline_v1"):
        # The user may request dynamic debugger collection, but the IR pass is
        # the source of truth for whether a hidden-arg ABI was actually added.
        # Metadata-only regions must not make the launcher append
        # __debug_ctrl_ptr, otherwise Ascend kernel arguments become misaligned.
        metadata["debug_launch_hidden_arg"] = False


def run_ttadapter_debug_passes_if_needed(mod, metadata: dict) -> None:
    """Simplify debugger-only TTAdapter writes after hidden arg becomes memref."""
    if not metadata.get("debug_enabled", False):
        return
    if not metadata.get("debug_launch_hidden_arg", False):
        return
    if int(metadata.get("debug_records_per_instance", 0)) <= 0:
        return

    fd = _get_debug_passes()
    if fd is None:
        raise RuntimeError(_DISABLED_BUILD_MESSAGE)

    pm = ir.pass_manager(mod.context)
    pm.enable_debug()
    fd.add_simplify_record_memref_writes(pm)
    _run_pass_manager(pm, mod, "flagtree_debug_ttadapter")


def run_compiler_event(event) -> None:
    metadata = event.metadata
    set_instrumentation_mode(str(metadata.get("instrumentation_mode", "")))
    if event.phase == "post_override" and event.ir_kind == "ttir":
        run_ttir_debug_passes_if_needed(event.module, metadata)
        update_compile_metadata(metadata)
    elif (event.phase == "pre_backend_serialize"
          and event.ir_kind == "ttadapter"):
        run_ttadapter_debug_passes_if_needed(event.module, metadata)


def update_compile_metadata(metadata: dict) -> None:
    if not _instrumentation_kind(metadata.get("instrumentation_mode",
                                              "")).startswith("debugger"):
        return
    from .api import current_compile_config

    # This runs after TTIR lowering. Request defaults must not overwrite the
    # resolved ABI (for example, three Ascend actor regions require a larger
    # allocation than the requested per-actor event capacity).
    for key, value in current_compile_config().items():
        metadata.setdefault(key, value)
    metadata.setdefault("debug_enabled", True)
