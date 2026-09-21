#include "Profiler/Vendor/EnflameProfiler.h"
#include "Context/Context.h"
#include "Profiler/Profiler.h"
#include <cstdlib>
#include <generated_tops_runtime_api_meta.h>
#include <mutex>
#include <set>
#include <stdexcept>
#include <tops/tops_runtime.h>
#include <topspti_activity.h>
#include <topspti_callbacks.h>
#include <unordered_map>

namespace proton {
namespace {
void check(TopsptiResult result, const char *operation) {
  if (result != TOPSPTI_SUCCESS)
    throw std::runtime_error(std::string(operation) +
                             " failed: TOPSPTI status " +
                             std::to_string(static_cast<int>(result)));
}
thread_local std::vector<RuntimeTraceEventKey> activeScopes;
thread_local bool internalFlush = false;
class EnflameProfiler final : public Profiler,
                              public OpInterface,
                              public Singleton<EnflameProfiler> {
public:
  VendorProfileArtifact collect(const SessionProfileMetadata &metadata,
                                const VendorProfilePlan &plan) {
    std::lock_guard<std::mutex> lock(eventsMutex);
    VendorProfileArtifact artifact;
    artifact.backend = metadata.backend;
    artifact.importer = "topspti_activity";
    artifact.requestedMetrics = plan.requested.vendorMetrics;
    for (auto association : events) {
      auto &event = association.runtimeEvent;
      auto it = launches.find(event.correlationId);
      // Activity buffers arrive asynchronously. Attribute each launch to the
      // sessions active at API entry, not at buffer completion/import time.
      if (it == launches.end() ||
          !it->second.sessions.count(metadata.sessionName))
        continue;
      if (it->second.scope.scopeId) {
        event.scopeId = it->second.scope.scopeId;
        association.metrics["enflame.scope_name"] = it->second.scope.opName;
      }
      if (association.source == "topspti_runtime" ||
          association.source == "topspti_driver") {
        event.opName = it->second.name;
        association.metrics.insert(it->second.metrics.begin(),
                                   it->second.metrics.end());
      }
      artifact.associations.push_back(std::move(association));
    }
    // Retain events across pause/resume; the next start begins a fresh capture.
    return artifact;
  }

private:
  std::mutex eventsMutex;
  std::vector<VendorMetricAssociation> events;
  const std::vector<Topspti_ActivityKind> kinds = {
      TOPSPTI_ACTIVITY_KIND_KERNEL, TOPSPTI_ACTIVITY_KIND_MEMCPY,
      TOPSPTI_ACTIVITY_KIND_MEMSET, TOPSPTI_ACTIVITY_KIND_RUNTIME,
      TOPSPTI_ACTIVITY_KIND_DRIVER};
  std::vector<Topspti_ActivityKind> enabledKinds;
  struct Launch {
    RuntimeTraceEventKey scope;
    std::string name;
    std::map<std::string, MetricValueType> metrics;
    std::set<std::string> sessions;
  };
  std::unordered_map<uint32_t, Launch> launches;
  Topspti_SubscriberHandle subscriber = nullptr;
  bool enabled = false;
  std::string callbackError;
  void startOp(const Scope &scope) override {
    RuntimeTraceEventKey event;
    event.scopeId = scope.scopeId;
    event.opName = scope.name;
    activeScopes.push_back(std::move(event));
  }
  void stopOp(const Scope &) override {
    if (!activeScopes.empty())
      activeScopes.pop_back();
  }
  static void callback(void *, Topspti_CallbackDomain, Topspti_CallbackId,
                       const void *raw) {
    if (!raw || internalFlush)
      return;
    auto *data = static_cast<const Topspti_CallbackData *>(raw);
    auto &self = instance();
    if (data->callbackSite != TOPSPTI_API_ENTER) {
      // Copy output parameters while the SDK callback owns their lifetime.
      if (!data->functionReturnValue ||
          *static_cast<const topsError_t *>(data->functionReturnValue) !=
              topsSuccess ||
          !data->functionParams)
        return;
      std::lock_guard<std::mutex> lock(self.eventsMutex);
      auto it = self.launches.find(data->correlationId);
      if (it == self.launches.end())
        return;
      auto &m = it->second.metrics;
      auto name = it->second.name;
      if (name == "topsMalloc") {
        auto *p = static_cast<const topsMalloc_params *>(data->functionParams);
        if (p->ptr) {
          m["enflame.memory_action"] = std::string("allocate");
          m["enflame.memory_space"] = std::string("device");
          m["enflame.address"] = uint64_t(reinterpret_cast<uintptr_t>(*p->ptr));
          m["enflame.allocation_bytes"] = uint64_t(p->size);
        }
      } else if (name == "topsFree") {
        auto *p = static_cast<const topsFree_params *>(data->functionParams);
        m["enflame.memory_action"] = std::string("free");
        m["enflame.memory_space"] = std::string("device");
        m["enflame.address"] = uint64_t(reinterpret_cast<uintptr_t>(p->ptr));
      } else if (name == "topsHostMalloc") {
        auto *p =
            static_cast<const topsHostMalloc_params *>(data->functionParams);
        if (p->ptr) {
          m["enflame.memory_action"] = std::string("allocate");
          m["enflame.memory_space"] = std::string("host");
          m["enflame.address"] = uint64_t(reinterpret_cast<uintptr_t>(*p->ptr));
          m["enflame.allocation_bytes"] = uint64_t(p->size);
        }
      } else if (name == "topsHostFree") {
        auto *p =
            static_cast<const topsHostFree_params *>(data->functionParams);
        m["enflame.memory_action"] = std::string("free");
        m["enflame.memory_space"] = std::string("host");
        m["enflame.address"] = uint64_t(reinterpret_cast<uintptr_t>(p->ptr));
      }
      return;
    }
    Launch launch;
    launch.name = data->functionName ? data->functionName : "unknown_api";
    launch.metrics["enflame.context_id"] = uint64_t(data->contextUid);
    if (!activeScopes.empty())
      launch.scope = activeScopes.back();
    {
      // Keep Data alive while copying its identity: unregisterData takes the
      // exclusive lock before a finalized session can destroy these objects.
      std::shared_lock<std::shared_mutex> lock(self.mutex);
      for (auto *data : self.dataSet)
        launch.sessions.insert(data->getPath());
    }
    std::lock_guard<std::mutex> lock(self.eventsMutex);
    self.launches[data->correlationId] = std::move(launch);
  }
  static void request(uint8_t **buffer, size_t *size, size_t *maxRecords) {
    *size = 8 * 1024 * 1024;
    *maxRecords = 0;
    *buffer = static_cast<uint8_t *>(std::malloc(*size));
    if (!*buffer)
      *size = 0;
  }
  static void complete(uint8_t *buffer, size_t, size_t valid) {
    if (!valid) {
      std::free(buffer);
      return;
    }
    auto &self = instance();
    std::lock_guard<std::mutex> lock(self.eventsMutex);
    Topspti_Activity *record = nullptr;
    TopsptiResult result;
    while ((result = topsptiActivityGetNextRecord(buffer, valid, &record)) ==
           TOPSPTI_SUCCESS) {
      VendorMetricAssociation association;
      auto &event = association.runtimeEvent;
      auto &m = association.metrics;
      association.state = VendorMetricState::Collected;
      if (record->kind == TOPSPTI_ACTIVITY_KIND_KERNEL) {
        auto *r = reinterpret_cast<Topspti_ActivityKernel *>(record);
        association.source = "topspti_activity";
        event.opName = r->name ? r->name : "enflame_kernel";
        event.startTimeNs = r->start;
        event.endTimeNs = r->end;
        event.deviceId = r->deviceId;
        event.streamId = r->streamId;
        event.correlationId = r->correlationId;
        event.taskId = r->gridId;
        m["enflame.kind"] = std::string("kernel");
        m["enflame.completed_ns"] = uint64_t(r->completed);
        m["enflame.context_id"] = uint64_t(r->contextId);
        m["enflame.grid_x"] = int64_t(r->gridX);
        m["enflame.grid_y"] = int64_t(r->gridY);
        m["enflame.grid_z"] = int64_t(r->gridZ);
        m["enflame.block_x"] = int64_t(r->blockX);
        m["enflame.block_y"] = int64_t(r->blockY);
        m["enflame.block_z"] = int64_t(r->blockZ);
      } else if (record->kind == TOPSPTI_ACTIVITY_KIND_MEMCPY) {
        auto *r = reinterpret_cast<Topspti_ActivityMemcpy *>(record);
        association.source = "topspti_memcpy";
        event.opName = "memcpy";
        event.startTimeNs = r->start;
        event.endTimeNs = r->end;
        event.deviceId = r->deviceId;
        event.streamId = r->streamId;
        event.correlationId = r->correlationId;
        m["enflame.kind"] = std::string("memcpy");
        m["enflame.bytes"] = uint64_t(r->bytes);
        m["enflame.copy_kind"] = uint64_t(r->copyKind);
        m["enflame.src_kind"] = uint64_t(r->srcKind);
        m["enflame.dst_kind"] = uint64_t(r->dstKind);
        m["enflame.flags"] = uint64_t(r->flags);
        m["enflame.context_id"] = uint64_t(r->contextId);
      } else if (record->kind == TOPSPTI_ACTIVITY_KIND_MEMSET) {
        auto *r = reinterpret_cast<Topspti_ActivityMemset *>(record);
        association.source = "topspti_memset";
        event.opName = "memset";
        event.startTimeNs = r->start;
        event.endTimeNs = r->end;
        event.deviceId = r->deviceId;
        event.streamId = r->streamId;
        event.correlationId = r->correlationId;
        m["enflame.kind"] = std::string("memset");
        m["enflame.bytes"] = uint64_t(r->bytes);
        m["enflame.value"] = uint64_t(r->value);
        m["enflame.memory_kind"] = uint64_t(r->memoryKind);
        m["enflame.flags"] = uint64_t(r->flags);
        m["enflame.context_id"] = uint64_t(r->contextId);
      } else if (record->kind == TOPSPTI_ACTIVITY_KIND_RUNTIME ||
                 record->kind == TOPSPTI_ACTIVITY_KIND_DRIVER) {
        auto *r = reinterpret_cast<Topspti_ActivityAPI *>(record);
        const bool runtime = record->kind == TOPSPTI_ACTIVITY_KIND_RUNTIME;
        association.source = runtime ? "topspti_runtime" : "topspti_driver";
        event.startTimeNs = r->start;
        event.endTimeNs = r->end;
        event.correlationId = r->correlationId;
        m["enflame.kind"] = std::string(runtime ? "runtime" : "driver");
        m["enflame.process_id"] = uint64_t(r->processId);
        m["enflame.thread_id"] = uint64_t(r->threadId);
        m["enflame.callback_id"] = uint64_t(r->cbid);
        m["enflame.return_value"] = uint64_t(r->returnValue);
      } else {
        continue;
      }
      if (!event.startTimeNs || event.endTimeNs < event.startTimeNs) {
        association.state = VendorMetricState::Unavailable;
        association.note = "TOPSPTI activity has unknown or invalid timestamps";
      }
      self.events.push_back(std::move(association));
    }
    if (result != TOPSPTI_ERROR_MAX_LIMIT_REACHED)
      self.callbackError =
          "TOPSPTI could not decode activity buffer: " + std::to_string(result);
    std::free(buffer);
  }
  void doStart() override {
    {
      std::lock_guard<std::mutex> lock(eventsMutex);
      events.clear();
      launches.clear();
      callbackError.clear();
    }
    check(topsptiActivityRegisterCallbacks(request, complete),
          "register activity callbacks");
    check(topsptiSubscribe(&subscriber, callback, nullptr),
          "subscribe callbacks");
    try {
      check(topsptiEnableDomain(1, subscriber, TOPSPTI_CB_DOMAIN_RUNTIME_API),
            "enable runtime callbacks");
      check(topsptiEnableDomain(1, subscriber, TOPSPTI_CB_DOMAIN_DRIVER_API),
            "enable driver callbacks");
      for (auto kind : kinds) {
        check(topsptiActivityEnable(kind), "enable detailed activity");
        enabledKinds.push_back(kind);
      }
      enabled = true;
    } catch (...) {
      for (auto kind : enabledKinds)
        topsptiActivityDisable(kind);
      enabledKinds.clear();
      topsptiUnsubscribe(subscriber);
      subscriber = nullptr;
      throw;
    }
  }
  void doFlush() override {
    if (!enabled)
      return;
    // Do not attribute profiler-induced synchronization to user code.
    struct FlushGuard {
      FlushGuard() { internalFlush = true; }
      ~FlushGuard() { internalFlush = false; }
    } guard;
    if (topsDeviceSynchronize() != topsSuccess)
      throw std::runtime_error(
          "topsDeviceSynchronize failed during TOPSPTI flush");
    check(topsptiActivityFlushAll(TOPSPTI_ACTIVITY_FLAG_FLUSH_FORCED),
          "flush activities");
    size_t dropped = 0;
    check(topsptiActivityGetNumDroppedRecords(&dropped),
          "get dropped activities");
    std::lock_guard<std::mutex> lock(eventsMutex);
    if (dropped)
      throw std::runtime_error("TOPSPTI dropped " + std::to_string(dropped) +
                               " records");
    if (!callbackError.empty())
      throw std::runtime_error(callbackError);
  }
  void doStop() override {
    if (enabled) {
      for (auto kind : enabledKinds)
        check(topsptiActivityDisable(kind), "disable detailed activity");
      enabledKinds.clear();
      enabled = false;
    }
    if (subscriber) {
      check(topsptiUnsubscribe(subscriber), "unsubscribe callbacks");
      subscriber = nullptr;
    }
  }
};
class EnflameImporter final : public VendorMetricsImporter {
public:
  std::string getName() const override { return "topspti_activity"; }
  VendorProfileArtifact import(const SessionProfileMetadata &metadata,
                               const VendorProfilePlan &plan) const override {
    return EnflameProfiler::instance().collect(metadata, plan);
  }
};
} // namespace
VendorProfilePlan
EnflameAdapter::makePlan(const VendorProfileOptions &options) const {
  VendorProfilePlan plan;
  plan.requested = options;
  plan.runtimeBaseEnabled = options.runtimeBaseEnabled;
  for (const auto &metric : options.vendorMetrics) {
    if (metric.required)
      throw std::runtime_error(
          "Enflame TOPSPTI hardware counter unsupported: " + metric.name);
    plan.disabledVendorMetrics.push_back(metric.name);
    plan.degradeReasons.push_back("unsupported hardware counter: " +
                                  metric.name);
  }
  return plan;
}
Profiler *EnflameAdapter::getRuntimeProfiler() const {
  return &EnflameProfiler::instance();
}
std::unique_ptr<VendorMetricsImporter> EnflameAdapter::createImporter() const {
  return std::make_unique<EnflameImporter>();
}
} // namespace proton
