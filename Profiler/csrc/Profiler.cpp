#include "Profiler.h"
#if defined(FLAGPRISM_BACKEND_ASCEND)
#include "Profiler/Vendor/CannLaunchReceipt.h"
#endif
#if FLAGTREE_PROFILER_GPU_RUNTIME
#include "Profiler/Cupti/CuptiPCSampling.h"
#include "Profiler/Instrumentation/InstrumentationProfiler.h"
#endif

#include <iostream>
#include <map>
#include <stdexcept>

#include "pybind11/pybind11.h"
#include "pybind11/stl.h"
#include "pybind11/stl_bind.h"

// Proton remains the internal C++ implementation namespace; the extension and
// all public Python APIs are exposed as FlagTree Profiler.
using namespace proton;

#ifdef FLAGTREE_PROFILER_COMPONENT_BUILD
void init_triton_proton(pybind11::module &&m);
#endif

static void initProfiler(pybind11::module &&m) {
  using ret = pybind11::return_value_policy;
  using namespace pybind11::literals;

  m.def(
      "start",
      [](const std::string &path, const std::string &contextSourceName,
         const std::string &dataName, const std::string &profilerName,
         const std::string &mode, const std::string &profilerPath,
         const std::string &hookName) {
        auto sessionId = SessionManager::instance().addSession(
            path, profilerName, profilerPath, contextSourceName, dataName, mode,
            hookName);
        try {
          SessionManager::instance().activateSession(sessionId);
        } catch (...) {
          // The Python caller has not received an id yet. Remove the native
          // session/path here and retain the original startup exception.
          try {
            SessionManager::instance().finalizeSession(sessionId, "");
          } catch (const std::exception &cleanup) {
            std::cerr << "FlagPrism native startup cleanup failed: "
                      << cleanup.what() << '\n';
          } catch (...) {
            std::cerr << "FlagPrism native startup cleanup failed\n";
          }
          throw;
        }
        return sessionId;
      },
      pybind11::arg("path"), pybind11::arg("contextSourceName"),
      pybind11::arg("dataName"), pybind11::arg("profilerName"),
      pybind11::arg("mode") = "", pybind11::arg("profilerPath") = "",
      pybind11::arg("hookName") = "");

  m.def("activate", [](size_t sessionId) {
    SessionManager::instance().activateSession(sessionId);
  });

  m.def("activate_all",
        []() { SessionManager::instance().activateAllSessions(); });

  m.def("deactivate", [](size_t sessionId) {
    SessionManager::instance().deactivateSession(sessionId);
  });

  m.def("deactivate_all",
        []() { SessionManager::instance().deactivateAllSessions(); });

  m.def("finalize", [](size_t sessionId, const std::string &outputFormat) {
    SessionManager::instance().finalizeSession(sessionId, outputFormat);
  });

  m.def("finalize_all", [](const std::string &outputFormat) {
    SessionManager::instance().finalizeAllSessions(outputFormat);
  });

  m.def("record_scope", []() { return Scope::getNewScopeId(); });

  m.def("supports_cann_launch_receipts", []() {
#if defined(FLAGPRISM_BACKEND_ASCEND)
    return true;
#else
    return false;
#endif
  });
#if defined(FLAGPRISM_BACKEND_ASCEND)
  m.def("cann_launch_receipts_active", [](uint64_t sessionId) {
    return SessionManager::instance().isActiveSessionForProfiler(sessionId,
                                                                 "cann") &&
           cannLaunchReceiptCaptureActive();
  });
  m.def("make_cann_launch_receipt", [](uint64_t scopeId, uint64_t sessionId) {
    if (!SessionManager::instance().isActiveSessionForProfiler(sessionId,
                                                               "cann"))
      throw pybind11::value_error(
          "launch receipt requires a live active CANN session");
    auto *sink = createCannLaunchReceiptSink(scopeId, sessionId);
    if (!sink)
      throw std::runtime_error(
          "CANN SDK launch receipt collector is inactive or full");
    if (sink->abiVersion != kCannLaunchReceiptAbiVersion ||
        sink->structSize != sizeof(CannLaunchReceiptSinkV1) || !sink->context ||
        !sink->retain || !sink->release || !sink->publish || !sink->cancel) {
      if (sink->context && sink->release)
        sink->release(sink->context);
      throw std::runtime_error("invalid CANN launch receipt sink ABI");
    }
    return pybind11::capsule(
        sink, kCannLaunchReceiptCapsuleName, [](void *pointer) {
          auto *owned = static_cast<CannLaunchReceiptSinkV1 *>(pointer);
          owned->release(owned->context);
        });
  });
  m.def("cancel_cann_launch_receipt", [](pybind11::capsule capsule,
                                         const std::string &reason) {
    auto *sink = static_cast<CannLaunchReceiptSinkV1 *>(
        PyCapsule_GetPointer(capsule.ptr(), kCannLaunchReceiptCapsuleName));
    if (!sink)
      throw pybind11::error_already_set();
    cancelCannLaunchReceiptSink(sink, reason);
  });
  m.def("drain_cann_launch_receipts", [](uint64_t sessionId) {
    pybind11::list result;
    for (const auto &receipt : drainCannLaunchReceipts(sessionId)) {
      pybind11::dict row;
      row["token_id"] = receipt.tokenId;
      row["scope_id"] = receipt.scopeId;
      row["session_id"] = receipt.sessionId;
      row["capture_epoch"] = receipt.captureEpoch;
      row["collector_output_path"] = receipt.collectorOutputPath;
      row["sdk_capture_path"] = receipt.sdkCapturePath;
      row["sdk_capture_binding_status"] = receipt.sdkCaptureBindingStatus;
      row["sdk_capture_binding_evidence"] = receipt.sdkCaptureBindingEvidence;
      row["publish_count"] = receipt.publishCount;
      row["late_callback"] = receipt.lateCallback;
      row["status"] = receipt.status;
      row["reason"] = receipt.reason;
      const auto &worker = receipt.worker;
      pybind11::dict record;
      record["abi_version"] = worker.abiVersion;
      record["struct_size"] = worker.structSize;
      record["process_id"] = worker.processId;
      record["thread_id"] = worker.threadId;
      record["stream_handle"] = worker.streamHandle;
      record["device_id"] = worker.deviceId;
      record["stream_id"] = worker.streamId;
      record["task_id"] = worker.taskId;
      record["launch_status"] = worker.launchStatus;
      record["device_query_status"] = worker.deviceQueryStatus;
      record["stream_query_status"] = worker.streamQueryStatus;
      record["task_query_status"] = worker.taskQueryStatus;
      row["worker"] = record;
      result.append(row);
    }
    return result;
  });
#endif

  m.def("enter_scope", [](size_t scopeId, const std::string &name) {
    SessionManager::instance().enterScope(Scope(scopeId, name));
  });

  m.def("exit_scope", [](size_t scopeId, const std::string &name) {
    SessionManager::instance().exitScope(Scope(scopeId, name));
  });

  m.def("enter_op", [](size_t scopeId, const std::string &name) {
    SessionManager::instance().enterOp(Scope(scopeId, name));
  });

  m.def("exit_op", [](size_t scopeId, const std::string &name) {
    SessionManager::instance().exitOp(Scope(scopeId, name));
  });

  m.def("init_function_metadata",
        [](uint64_t functionId, const std::string &functionName,
           const std::vector<std::pair<size_t, std::string>> &scopeIdNames,
           const std::vector<std::pair<size_t, size_t>> &scopeIdParents,
           const std::string &metadataPath) {
          SessionManager::instance().initFunctionMetadata(
              functionId, functionName, scopeIdNames, scopeIdParents,
              metadataPath);
        });

  m.def("enter_instrumented_op", [](uint64_t streamId, uint64_t functionId,
                                    uint64_t buffer, size_t size) {
    SessionManager::instance().enterInstrumentedOp(
        streamId, functionId, reinterpret_cast<uint8_t *>(buffer), size);
  });

  m.def("exit_instrumented_op", [](uint64_t streamId, uint64_t functionId,
                                   uint64_t buffer, size_t size) {
    SessionManager::instance().exitInstrumentedOp(
        streamId, functionId, reinterpret_cast<uint8_t *>(buffer), size);
  });

#if FLAGTREE_PROFILER_GPU_RUNTIME
  m.def(
      "validate_pc_sampling_support",
      [](const std::string &libPath) {
        if (!libPath.empty())
          cupti::setLibPath(libPath);
        CUcontext context = nullptr;
        cuda::ctxGetCurrent<false>(&context);
        CuptiPCSampling::instance().validateSupport(context);
      },
      pybind11::arg("lib_path") = "");
  m.def("set_observation_programs", [](const std::vector<uint32_t> &programs) {
    InstrumentationProfiler::instance().setObservationPrograms(programs);
  });
  m.def("set_raw_capture_enabled", [](bool enabled) {
    InstrumentationProfiler::instance().setRawCaptureEnabled(enabled);
  });
  m.def("get_raw_host_buffer", [](uint64_t functionId, uint64_t streamId) {
    auto bytes = InstrumentationProfiler::instance().takeRawHostBuffer(
        functionId, streamId);
    return pybind11::bytes(reinterpret_cast<const char *>(bytes.data()),
                           bytes.size());
  });
#endif

  m.def("enter_state", [](const std::string &state) {
    SessionManager::instance().setState(state);
  });

  m.def("exit_state",
        []() { SessionManager::instance().setState(std::nullopt); });

  m.def("add_metrics",
        [](size_t scopeId,
           const std::map<std::string, MetricValueType> &metrics) {
          SessionManager::instance().addMetrics(scopeId, metrics);
        });

  m.def("get_context_depth", [](size_t sessionId) {
    return SessionManager::instance().getContextDepth(sessionId);
  });

  pybind11::bind_map<std::map<std::string, MetricValueType>>(m, "MetricMap");
}

PYBIND11_MODULE(_native, m) {
  m.doc() = "Python bindings to the FlagTree Profiler API";
  initProfiler(std::move(m));
#ifdef FLAGTREE_PROFILER_COMPONENT_BUILD
  init_triton_proton(std::move(m.def_submodule("compiler")));
#endif
}
