#include "Profiler/Cupti/CuptiProfiler.h"
#include "Context/Context.h"
#include "Data/Metric.h"
#include "Device.h"
#include "Driver/GPU/CudaApi.h"
#include "Driver/GPU/CuptiApi.h"
#include "Profiler/Cupti/CuptiPCSampling.h"
#include "Profiler/SdkCleanup.h"
#include "Utility/Map.h"

#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <optional>
#include <stdexcept>
#include <unistd.h>

namespace proton {

void CuptiProfiler::beginActivityCapture() {
  std::lock_guard<std::mutex> lock(activityMutex);
  ++activityEpoch;
}

void CuptiProfiler::registerActivityLaunch(uint32_t correlationId,
                                           size_t scopeId,
                                           const std::set<Data *> &dataSet,
                                           bool graphInstanceCountUnknown) {
  std::lock_guard<std::mutex> lock(activityMutex);
  auto &launch = activityLaunches[correlationId];
  launch.scopeId = scopeId;
  launch.epoch = activityEpoch;
  launch.graphInstanceCountUnknown = graphInstanceCountUnknown;
  for (auto *data : dataSet)
    launch.sessions.insert(data->getPath());
}

void CuptiProfiler::recordActivityKernel(const void *activity) {
  auto *kernel = static_cast<const CUpti_ActivityKernel5 *>(activity);
  VendorMetricAssociation association;
  auto &event = association.runtimeEvent;
  event.opName = kernel->name ? kernel->name : "";
  event.correlationId = kernel->correlationId;
  event.deviceId = kernel->deviceId;
  event.streamId = kernel->streamId;
  event.startTimeNs = kernel->start;
  event.endTimeNs = kernel->end;
  association.source = "cupti_activity";
  association.state = VendorMetricState::Collected;
  association.metrics = {
      {"activity.kind", std::string("kernel")},
      {"activity.process_id", uint64_t(getpid())},
      {"activity.context_id", uint64_t(kernel->contextId)},
      {"activity.correlation_domain", std::string("cupti")},
      {"activity.clock_domain", std::string("cupti_timestamp_ns")},
      {"activity.time_semantics", std::string("device_kernel_execution")},
      {"activity.grid_x", uint64_t(kernel->gridX)},
      {"activity.grid_y", uint64_t(kernel->gridY)},
      {"activity.grid_z", uint64_t(kernel->gridZ)},
      {"activity.block_x", uint64_t(kernel->blockX)},
      {"activity.block_y", uint64_t(kernel->blockY)},
      {"activity.block_z", uint64_t(kernel->blockZ)},
      {"activity.graph_id", uint64_t(kernel->graphId)},
      {"activity.unknown_fields", std::string("thread_id,task_id")}};
  std::lock_guard<std::mutex> lock(activityMutex);
  auto launch = activityLaunches.find(kernel->correlationId);
  if (launch != activityLaunches.end()) {
    event.scopeId = launch->second.scopeId;
    if (launch->second.graphInstanceCountUnknown)
      association.metrics["activity.graph_instance_count_status"] =
          std::string("unknown_graph_created_before_capture");
    association.metrics["activity.capture_epoch"] = launch->second.epoch;
    association.metrics["activity.correlation_domain"] =
        std::string("cupti-capture-") + std::to_string(launch->second.epoch);
  } else
    association.metrics["activity.unknown_fields"] =
        std::string("thread_id,task_id,scope_id");
  activityEvents.push_back(
      {std::move(association), launch == activityLaunches.end()
                                   ? std::set<std::string>{}
                                   : launch->second.sessions});
}

void CuptiProfiler::recordActivityDropped(size_t count) {
  std::lock_guard<std::mutex> lock(activityMutex);
  activityDropped += count;
}

VendorProfileArtifact
CuptiProfiler::collectActivityArtifact(const std::string &sessionPath) {
  VendorProfileArtifact artifact;
  artifact.backend = "cuda";
  artifact.importer = "cupti_activity";
  std::lock_guard<std::mutex> lock(activityMutex);
  if (activityDropped)
    artifact.degradeReasons.push_back(
        "CUPTI profiler lifetime has cumulatively dropped " +
        std::to_string(activityDropped) +
        " records; loss cannot be attributed to one session or native "
        "activity");
  for (auto it = activityEvents.begin(); it != activityEvents.end();) {
    if (it->sessions.erase(sessionPath)) {
      if (it->association.metrics.count(
              "activity.graph_instance_count_status") &&
          std::find(artifact.degradeReasons.begin(),
                    artifact.degradeReasons.end(),
                    "Graph created before CUPTI capture: per-replay instance "
                    "count unavailable; correlation cache retained until "
                    "capture epoch ends") == artifact.degradeReasons.end())
        artifact.degradeReasons.push_back(
            "Graph created before CUPTI capture: per-replay instance count "
            "unavailable; correlation cache retained until capture epoch ends");
      artifact.associations.push_back(it->association);
    }
    if (it->sessions.empty())
      it = activityEvents.erase(it);
    else
      ++it;
  }
  for (auto it = activityLaunches.begin(); it != activityLaunches.end();) {
    it->second.sessions.erase(sessionPath);
    if (it->second.sessions.empty())
      it = activityLaunches.erase(it);
    else
      ++it;
  }
  return artifact;
}

template <>
thread_local GPUProfiler<CuptiProfiler>::ThreadState
    GPUProfiler<CuptiProfiler>::threadState(CuptiProfiler::instance());

template <>
thread_local std::deque<size_t>
    GPUProfiler<CuptiProfiler>::Correlation::externIdQueue{};

namespace {

std::shared_ptr<Metric> convertActivityToMetric(CUpti_Activity *activity) {
  std::shared_ptr<Metric> metric;
  switch (activity->kind) {
  case CUPTI_ACTIVITY_KIND_KERNEL:
  case CUPTI_ACTIVITY_KIND_CONCURRENT_KERNEL: {
    auto *kernel = reinterpret_cast<CUpti_ActivityKernel5 *>(activity);
    if (kernel->start < kernel->end) {
      metric = std::make_shared<KernelMetric>(
          static_cast<uint64_t>(kernel->start),
          static_cast<uint64_t>(kernel->end), 1,
          static_cast<uint64_t>(kernel->deviceId),
          static_cast<uint64_t>(DeviceType::CUDA),
          static_cast<uint64_t>(kernel->streamId));
    } // else: not a valid kernel activity
    break;
  }
  default:
    break;
  }
  return metric;
}

uint32_t
processActivityKernel(CuptiProfiler::CorrIdToExternIdMap &corrIdToExternId,
                      CuptiProfiler::ApiExternIdSet &apiExternIds,
                      std::set<Data *> &dataSet, CUpti_Activity *activity) {
  // Support CUDA >= 11.0
  auto *kernel = reinterpret_cast<CUpti_ActivityKernel5 *>(activity);
  auto correlationId = kernel->correlationId;
  if (/*Not a valid context*/ !corrIdToExternId.contain(correlationId))
    return correlationId;
  auto [parentId, numInstances] = corrIdToExternId.at(correlationId);
  if (kernel->graphId == 0) {
    // Non-graph kernels
    for (auto *data : dataSet) {
      auto scopeId = parentId;
      if (apiExternIds.contain(scopeId)) {
        // It's triggered by a CUDA op but not triton op
        scopeId = data->addOp(parentId, kernel->name);
      }
      data->addMetric(scopeId, convertActivityToMetric(activity));
    }
  } else {
    // Graph kernels
    // A single graph launch can trigger multiple kernels.
    // Our solution is to construct the following maps:
    // --- Application threads ---
    // 1. graphId -> numKernels
    // 2. graphExecId -> graphId
    // --- CUPTI thread ---
    // 3. corrId -> numKernels
    for (auto *data : dataSet) {
      auto externId = data->addOp(parentId, kernel->name);
      data->addMetric(externId, convertActivityToMetric(activity));
    }
  }
  apiExternIds.erase(parentId);
  --numInstances;
  if (numInstances == 0) {
    corrIdToExternId.erase(correlationId);
  } else {
    corrIdToExternId[correlationId].second = numInstances;
  }
  return correlationId;
}

uint32_t processActivity(CuptiProfiler::CorrIdToExternIdMap &corrIdToExternId,
                         CuptiProfiler::ApiExternIdSet &apiExternIds,
                         std::set<Data *> &dataSet, CUpti_Activity *activity) {
  auto correlationId = 0;
  switch (activity->kind) {
  case CUPTI_ACTIVITY_KIND_KERNEL:
  case CUPTI_ACTIVITY_KIND_CONCURRENT_KERNEL: {
    correlationId = processActivityKernel(corrIdToExternId, apiExternIds,
                                          dataSet, activity);
    break;
  }
  default:
    break;
  }
  return correlationId;
}

template <typename Configure> void setRuntimeCallbacks(Configure &&configure) {
#define CALLBACK_ENABLE(id) configure(CUPTI_CB_DOMAIN_RUNTIME_API, id)

  CALLBACK_ENABLE(CUPTI_RUNTIME_TRACE_CBID_cudaLaunch_v3020);
  CALLBACK_ENABLE(CUPTI_RUNTIME_TRACE_CBID_cudaLaunchKernel_v7000);
  CALLBACK_ENABLE(CUPTI_RUNTIME_TRACE_CBID_cudaLaunch_ptsz_v7000);
  CALLBACK_ENABLE(CUPTI_RUNTIME_TRACE_CBID_cudaLaunchKernel_ptsz_v7000);
  CALLBACK_ENABLE(CUPTI_RUNTIME_TRACE_CBID_cudaLaunchKernelExC_v11060);
  CALLBACK_ENABLE(CUPTI_RUNTIME_TRACE_CBID_cudaLaunchKernelExC_ptsz_v11060);
  CALLBACK_ENABLE(CUPTI_RUNTIME_TRACE_CBID_cudaLaunchCooperativeKernel_v9000);
  CALLBACK_ENABLE(
      CUPTI_RUNTIME_TRACE_CBID_cudaLaunchCooperativeKernel_ptsz_v9000);
  CALLBACK_ENABLE(
      CUPTI_RUNTIME_TRACE_CBID_cudaLaunchCooperativeKernelMultiDevice_v9000);
  CALLBACK_ENABLE(CUPTI_RUNTIME_TRACE_CBID_cudaGraphLaunch_v10000);
  CALLBACK_ENABLE(CUPTI_RUNTIME_TRACE_CBID_cudaGraphLaunch_ptsz_v10000);

#undef CALLBACK_ENABLE
}

template <typename Configure> void setDriverCallbacks(Configure &&configure) {
#define CALLBACK_ENABLE(id) configure(CUPTI_CB_DOMAIN_DRIVER_API, id)

  CALLBACK_ENABLE(CUPTI_DRIVER_TRACE_CBID_cuLaunch);
  CALLBACK_ENABLE(CUPTI_DRIVER_TRACE_CBID_cuLaunchGrid);
  CALLBACK_ENABLE(CUPTI_DRIVER_TRACE_CBID_cuLaunchGridAsync);
  CALLBACK_ENABLE(CUPTI_DRIVER_TRACE_CBID_cuLaunchKernel);
  CALLBACK_ENABLE(CUPTI_DRIVER_TRACE_CBID_cuLaunchKernel_ptsz);
  CALLBACK_ENABLE(CUPTI_DRIVER_TRACE_CBID_cuLaunchKernelEx);
  CALLBACK_ENABLE(CUPTI_DRIVER_TRACE_CBID_cuLaunchKernelEx_ptsz);
  CALLBACK_ENABLE(CUPTI_DRIVER_TRACE_CBID_cuLaunchCooperativeKernel);
  CALLBACK_ENABLE(CUPTI_DRIVER_TRACE_CBID_cuLaunchCooperativeKernel_ptsz);
  CALLBACK_ENABLE(CUPTI_DRIVER_TRACE_CBID_cuLaunchCooperativeKernelMultiDevice);
  CALLBACK_ENABLE(CUPTI_DRIVER_TRACE_CBID_cuGraphLaunch);
  CALLBACK_ENABLE(CUPTI_DRIVER_TRACE_CBID_cuGraphLaunch_ptsz);
#undef CALLBACK_ENABLE
}

template <typename Configure> void setGraphCallbacks(Configure &&configure) {

#define CALLBACK_ENABLE(id) configure(CUPTI_CB_DOMAIN_RESOURCE, id)

  CALLBACK_ENABLE(CUPTI_CBID_RESOURCE_GRAPHNODE_CREATED);
  CALLBACK_ENABLE(CUPTI_CBID_RESOURCE_GRAPHNODE_CLONED);
  CALLBACK_ENABLE(CUPTI_CBID_RESOURCE_GRAPHNODE_DESTROY_STARTING);
  CALLBACK_ENABLE(CUPTI_CBID_RESOURCE_GRAPHEXEC_CREATED);
  CALLBACK_ENABLE(CUPTI_CBID_RESOURCE_GRAPHEXEC_DESTROY_STARTING);
  CALLBACK_ENABLE(CUPTI_CBID_RESOURCE_GRAPH_DESTROY_STARTING);
#undef CALLBACK_ENABLE
}

template <typename Configure> void setResourceCallbacks(Configure &&configure) {
#define CALLBACK_ENABLE(id) configure(CUPTI_CB_DOMAIN_RESOURCE, id)

  CALLBACK_ENABLE(CUPTI_CBID_RESOURCE_MODULE_LOADED);
  CALLBACK_ENABLE(CUPTI_CBID_RESOURCE_MODULE_UNLOAD_STARTING);
  CALLBACK_ENABLE(CUPTI_CBID_RESOURCE_CONTEXT_CREATED);
  CALLBACK_ENABLE(CUPTI_CBID_RESOURCE_CONTEXT_DESTROY_STARTING);
#undef CALLBACK_ENABLE
}

bool isDriverAPILaunch(CUpti_CallbackId cbId) {
  return cbId == CUPTI_DRIVER_TRACE_CBID_cuLaunch ||
         cbId == CUPTI_DRIVER_TRACE_CBID_cuLaunchGrid ||
         cbId == CUPTI_DRIVER_TRACE_CBID_cuLaunchGridAsync ||
         cbId == CUPTI_DRIVER_TRACE_CBID_cuLaunchKernel ||
         cbId == CUPTI_DRIVER_TRACE_CBID_cuLaunchKernel_ptsz ||
         cbId == CUPTI_DRIVER_TRACE_CBID_cuLaunchKernelEx ||
         cbId == CUPTI_DRIVER_TRACE_CBID_cuLaunchKernelEx_ptsz ||
         cbId == CUPTI_DRIVER_TRACE_CBID_cuLaunchCooperativeKernel ||
         cbId == CUPTI_DRIVER_TRACE_CBID_cuLaunchCooperativeKernel_ptsz ||
         cbId == CUPTI_DRIVER_TRACE_CBID_cuLaunchCooperativeKernelMultiDevice ||
         cbId == CUPTI_DRIVER_TRACE_CBID_cuGraphLaunch ||
         cbId == CUPTI_DRIVER_TRACE_CBID_cuGraphLaunch_ptsz;
}

} // namespace

struct CuptiProfiler::CuptiProfilerPimpl
    : public GPUProfiler<CuptiProfiler>::GPUProfilerPimplInterface {
  CuptiProfilerPimpl(CuptiProfiler &profiler)
      : GPUProfiler<CuptiProfiler>::GPUProfilerPimplInterface(profiler) {}
  virtual ~CuptiProfilerPimpl() = default;

  void prepareConfiguration() override {
    if (finalizationPending || subscriber || enabledActivity ||
        !enabledCallbacks.empty())
      doStop();
  }
  void setLibPath(const std::string &libPath) override {
    cupti::setLibPath(libPath);
  }
  void doStart() override;
  void doFlush() override;
  void doStop() override;

  static void allocBuffer(uint8_t **buffer, size_t *bufferSize,
                          size_t *maxNumRecords);
  static void completeBuffer(CUcontext context, uint32_t streamId,
                             uint8_t *buffer, size_t size, size_t validSize);
  static void callbackFn(void *userData, CUpti_CallbackDomain domain,
                         CUpti_CallbackId cbId, const void *cbData);

  static constexpr size_t AlignSize = 8;
  static constexpr size_t BufferSize = 64 * 1024 * 1024;
  static constexpr size_t AttributeSize = sizeof(size_t);

  CUpti_SubscriberHandle subscriber{};
  std::vector<std::pair<CUpti_CallbackDomain, CUpti_CallbackId>>
      enabledCallbacks;
  std::optional<CUpti_ActivityKind> enabledActivity;
  bool finalizationPending{false};
  bool subscriptionOwnershipUnknown{false};
  bool pcSamplingNeedsCleanup{false};
  CuptiPCSampling pcSampling;

  ThreadSafeMap<uint32_t, size_t, std::unordered_map<uint32_t, size_t>>
      graphIdToNumInstances;
  ThreadSafeMap<uint32_t, uint32_t, std::unordered_map<uint32_t, uint32_t>>
      graphExecIdToGraphId;
};

void CuptiProfiler::CuptiProfilerPimpl::allocBuffer(uint8_t **buffer,
                                                    size_t *bufferSize,
                                                    size_t *maxNumRecords) {
  *buffer = static_cast<uint8_t *>(aligned_alloc(AlignSize, BufferSize));
  if (*buffer == nullptr) {
    throw std::runtime_error("[PROTON] aligned_alloc failed");
  }
  *bufferSize = BufferSize;
  *maxNumRecords = 0;
}

void CuptiProfiler::CuptiProfilerPimpl::completeBuffer(CUcontext ctx,
                                                       uint32_t streamId,
                                                       uint8_t *buffer,
                                                       size_t size,
                                                       size_t validSize) {
  CuptiProfiler &profiler = threadState.profiler;
  auto dataSet = profiler.getDataSet();
  uint32_t maxCorrelationId = 0;
  CUptiResult status;
  CUpti_Activity *activity = nullptr;
  do {
    status = cupti::activityGetNextRecord<false>(buffer, validSize, &activity);
    if (status == CUPTI_SUCCESS) {
      if (activity->kind == CUPTI_ACTIVITY_KIND_KERNEL ||
          activity->kind == CUPTI_ACTIVITY_KIND_CONCURRENT_KERNEL)
        profiler.recordActivityKernel(activity);
      auto correlationId =
          processActivity(profiler.correlation.corrIdToExternId,
                          profiler.correlation.apiExternIds, dataSet, activity);
      maxCorrelationId = std::max(maxCorrelationId, correlationId);
    } else if (status == CUPTI_ERROR_MAX_LIMIT_REACHED) {
      break;
    } else {
      throw std::runtime_error("[PROTON] cupti::activityGetNextRecord failed");
    }
  } while (true);

  size_t dropped = 0;
  cupti::activityGetNumDroppedRecords<true>(ctx, streamId, &dropped);
  profiler.recordActivityDropped(dropped);
  std::free(buffer);

  profiler.correlation.complete(maxCorrelationId);
}

void CuptiProfiler::CuptiProfilerPimpl::callbackFn(void *userData,
                                                   CUpti_CallbackDomain domain,
                                                   CUpti_CallbackId cbId,
                                                   const void *cbData) {
  CuptiProfiler &profiler = threadState.profiler;
  if (domain == CUPTI_CB_DOMAIN_RESOURCE) {
    auto *resourceData =
        static_cast<CUpti_ResourceData *>(const_cast<void *>(cbData));
    auto *pImpl = dynamic_cast<CuptiProfilerPimpl *>(profiler.pImpl.get());
    if (cbId == CUPTI_CBID_RESOURCE_MODULE_LOADED) {
      auto *moduleResource = static_cast<CUpti_ModuleResourceData *>(
          resourceData->resourceDescriptor);
      if (profiler.isPCSamplingEnabled()) {
        pImpl->pcSampling.loadModule(moduleResource->pCubin,
                                     moduleResource->cubinSize);
      }
    } else if (cbId == CUPTI_CBID_RESOURCE_MODULE_UNLOAD_STARTING) {
      auto *moduleResource = static_cast<CUpti_ModuleResourceData *>(
          resourceData->resourceDescriptor);
      if (profiler.isPCSamplingEnabled()) {
        pImpl->pcSampling.unloadModule(moduleResource->pCubin,
                                       moduleResource->cubinSize);
      }
    } else if (cbId == CUPTI_CBID_RESOURCE_CONTEXT_CREATED) {
      if (profiler.isPCSamplingEnabled()) {
        pImpl->pcSampling.initialize(resourceData->context);
      }
    } else if (cbId == CUPTI_CBID_RESOURCE_CONTEXT_DESTROY_STARTING) {
      if (profiler.isPCSamplingEnabled()) {
        pImpl->pcSampling.finalize(resourceData->context);
      }
    } else {
      auto *graphData =
          static_cast<CUpti_GraphData *>(resourceData->resourceDescriptor);
      uint32_t graphId = 0;
      uint32_t graphExecId = 0;
      if (graphData->graph)
        cupti::getGraphId<true>(graphData->graph, &graphId);
      if (graphData->graphExec)
        cupti::getGraphExecId<true>(graphData->graphExec, &graphExecId);
      if (cbId == CUPTI_CBID_RESOURCE_GRAPHNODE_CREATED ||
          cbId == CUPTI_CBID_RESOURCE_GRAPHNODE_CLONED) {
        if (!pImpl->graphIdToNumInstances.contain(graphId))
          pImpl->graphIdToNumInstances[graphId] = 1;
        else
          pImpl->graphIdToNumInstances[graphId]++;
      } else if (cbId == CUPTI_CBID_RESOURCE_GRAPHNODE_DESTROY_STARTING) {
        pImpl->graphIdToNumInstances[graphId]--;
      } else if (cbId == CUPTI_CBID_RESOURCE_GRAPHEXEC_CREATED) {
        pImpl->graphExecIdToGraphId[graphExecId] = graphId;
      } else if (cbId == CUPTI_CBID_RESOURCE_GRAPHEXEC_DESTROY_STARTING) {
        pImpl->graphExecIdToGraphId.erase(graphExecId);
      } else if (cbId == CUPTI_CBID_RESOURCE_GRAPH_DESTROY_STARTING) {
        pImpl->graphIdToNumInstances.erase(graphId);
      }
    }
  } else {
    const CUpti_CallbackData *callbackData =
        static_cast<const CUpti_CallbackData *>(cbData);
    auto *pImpl = dynamic_cast<CuptiProfilerPimpl *>(profiler.pImpl.get());
    if (callbackData->callbackSite == CUPTI_API_ENTER) {
      threadState.enterOp();
      size_t numInstances = 1;
      bool graphInstanceCountUnknown = false;
      if (cbId == CUPTI_DRIVER_TRACE_CBID_cuGraphLaunch ||
          cbId == CUPTI_DRIVER_TRACE_CBID_cuGraphLaunch_ptsz) {
        auto graphExec = static_cast<const cuGraphLaunch_params *>(
                             callbackData->functionParams)
                             ->hGraph;
        uint32_t graphExecId = 0;
        cupti::getGraphExecId<true>(graphExec, &graphExecId);
        numInstances = std::numeric_limits<size_t>::max();
        auto findGraph = false;
        if (pImpl->graphExecIdToGraphId.contain(graphExecId)) {
          auto graphId = pImpl->graphExecIdToGraphId[graphExecId];
          if (pImpl->graphIdToNumInstances.contain(graphId)) {
            numInstances = pImpl->graphIdToNumInstances[graphId];
            findGraph = true;
          }
        }
        if (!findGraph) {
          graphInstanceCountUnknown = true;
          std::cerr << "[PROTON] Cannot find graph for graphExecId: "
                    << graphExecId
                    << ", and t may cause memory leak. To avoid this problem, "
                       "please start profiling before the graph is created."
                    << std::endl;
        }
      }
      profiler.correlation.correlate(callbackData->correlationId, numInstances);
      if (!profiler.correlation.externIdQueue.empty())
        profiler.registerActivityLaunch(
            callbackData->correlationId,
            profiler.correlation.externIdQueue.back(), profiler.getDataSet(),
            graphInstanceCountUnknown);
      if (profiler.isPCSamplingEnabled() && isDriverAPILaunch(cbId)) {
        pImpl->pcSampling.start(callbackData->context);
      }
    } else if (callbackData->callbackSite == CUPTI_API_EXIT) {
      if (profiler.isPCSamplingEnabled() && isDriverAPILaunch(cbId)) {
        // XXX: Conservatively stop every GPU kernel for now
        auto scopeId = profiler.correlation.externIdQueue.back();
        pImpl->pcSampling.stop(
            callbackData->context, scopeId,
            profiler.correlation.apiExternIds.contain(scopeId));
      }
      threadState.exitOp();
      profiler.correlation.submit(callbackData->correlationId);
    }
  }
}

void CuptiProfiler::CuptiProfilerPimpl::doStart() {
  // Public started=false does not certify release of a failed SDK resource.
  // Retry unresolved cleanup before replacing its handles or configuration.
  if (finalizationPending || subscriber || enabledActivity ||
      !enabledCallbacks.empty())
    doStop();
  std::vector<std::pair<CUpti_CallbackDomain, CUpti_CallbackId>> requested;
  auto append = [&](CUpti_CallbackDomain domain, CUpti_CallbackId id) {
    requested.emplace_back(domain, id);
  };
  if (profiler.isPCSamplingEnabled())
    setResourceCallbacks(append);
  const auto resourceCallbackCount = requested.size();
  setGraphCallbacks(append);
  setRuntimeCallbacks(append);
  setDriverCallbacks(append);
  // All potentially allocating bookkeeping is prepared before acquisition.
  enabledCallbacks.reserve(requested.size());
  profiler.beginActivityCapture();
  profiler.correlation.maxSubmittedCorrelationId.store(0);
  profiler.correlation.maxCompletedCorrelationId.store(0);
  profiler.correlation.corrIdToExternId.clear();
  try {
    cupti::subscribe<true>(&subscriber, callbackFn, nullptr);
    finalizationPending = true;
    pcSamplingNeedsCleanup = profiler.isPCSamplingEnabled();
    auto enable = [&](const auto &callback) {
      cupti::enableCallback<true>(1, subscriber, callback.first,
                                  callback.second);
      enabledCallbacks.push_back(callback);
    };
    for (size_t i = 0; i < resourceCallbackCount; ++i)
      enable(requested[i]);
    const auto kind = profiler.isPCSamplingEnabled()
                          ? CUPTI_ACTIVITY_KIND_KERNEL
                          : CUPTI_ACTIVITY_KIND_CONCURRENT_KERNEL;
    cupti::activityEnable<true>(kind);
    enabledActivity = kind;
    cupti::activityRegisterCallbacks<true>(allocBuffer, completeBuffer);
    for (size_t i = resourceCallbackCount; i < requested.size(); ++i)
      enable(requested[i]);
  } catch (...) {
    // A non-null error output does not prove ownership: it may refer to an
    // external subscriber. Retain it and fail closed without global teardown.
    if (subscriber && !finalizationPending)
      subscriptionOwnershipUnknown = true;
    SdkCleanup cleanup(std::current_exception());
    cleanup.attempt([&] { doStop(); });
    cleanup.rethrow();
  }
}

void CuptiProfiler::CuptiProfilerPimpl::doFlush() {
  // cuptiActivityFlushAll returns the activity records associated with all
  // contexts/streams.
  // This is a blocking call but it doesn’t issue any CUDA synchronization calls
  // implicitly thus it’s not guaranteed that all activities are completed on
  // the underlying devices.
  // We do an "opportunistic" synchronization here to try to ensure that all
  // activities are completed on the current context.
  // If the current context is not set, we don't do any synchronization.
  CUcontext cuContext = nullptr;
  cuda::ctxGetCurrent<false>(&cuContext);
  if (cuContext) {
    cuda::ctxSynchronize<true>();
  }
  profiler.correlation.flush(
      /*maxRetries=*/100, /*sleepMs=*/10,
      /*flush=*/[]() {
        cupti::activityFlushAll<true>(
            /*flag=*/0);
      });
  // CUPTI_ACTIVITY_FLAG_FLUSH_FORCED is used to ensure that even incomplete
  // activities are flushed so that the next profiling session can start with
  // new activities.
  cupti::activityFlushAll<true>(/*flag=*/CUPTI_ACTIVITY_FLAG_FLUSH_FORCED);
}

void CuptiProfiler::CuptiProfilerPimpl::doStop() {
  if (subscriptionOwnershipUnknown)
    throw std::runtime_error(
        "CUPTI subscribe failed with an unverified handle; subscription "
        "ownership is unknown. Refusing cleanup or a new capture; use a fresh "
        "process after resolving the external collector.");
  SdkCleanup cleanup;
  if (pcSamplingNeedsCleanup) {
    cleanup.attempt([&] {
      CUcontext cuContext = nullptr;
      cuda::ctxGetCurrent<true>(&cuContext);
      if (cuContext)
        pcSampling.finalize(cuContext);
    });
  }
  if (enabledActivity &&
      cleanup.attempt([&] { cupti::activityDisable<true>(*enabledActivity); }))
    enabledActivity.reset();
  for (auto it = enabledCallbacks.begin(); it != enabledCallbacks.end();) {
    if (cleanup.attempt([&] {
          cupti::enableCallback<true>(0, subscriber, it->first, it->second);
        }))
      it = enabledCallbacks.erase(it);
    else
      ++it;
  }
  if (subscriber &&
      cleanup.attempt([&] { cupti::unsubscribe<true>(subscriber); })) {
    subscriber = nullptr;
    enabledCallbacks.clear();
  }
  if (finalizationPending &&
      cleanup.attempt([&] { cupti::finalize<true>(); })) {
    // This collector uses the V1 single-subscriber API. Its successful global
    // finalize destroys all CUPTI resources, including a failed unsubscribe.
    // https://docs.nvidia.com/cuda/archive/11.0_GA/cupti/Cupti/r_main.html
    // Never infer this transition from started=false or from a failed finalize.
    subscriber = nullptr;
    enabledCallbacks.clear();
    enabledActivity.reset();
    finalizationPending = false;
    pcSamplingNeedsCleanup = false;
    pcSampling.releaseAfterRuntimeFinalize();
  }
  cleanup.rethrow();
}

CuptiProfiler::CuptiProfiler() {
  pImpl = std::make_unique<CuptiProfilerPimpl>(*this);
}

CuptiProfiler::~CuptiProfiler() = default;

} // namespace proton
