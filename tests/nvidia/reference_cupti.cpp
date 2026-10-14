// Independent measurement collector: no FlagPrism runtime or launch hooks.
#include <atomic>
#include <cstdlib>
#include <cupti.h>
#include <dlfcn.h>
#include <mutex>
#include <nlohmann/json.hpp>
#include <string>
#include <unistd.h>
#include <unordered_map>
#include <vector>

namespace {
std::mutex mutex;
std::vector<nlohmann::json> records;
std::unordered_map<uint32_t, uint64_t> externalIds;
size_t dropped = 0;
int callbackError = 0;
std::string output;
std::atomic<bool> monitoring{false};
bool standalone = false;
CUpti_BuffersCallbackCompleteFunc primaryComplete = nullptr;
thread_local bool inFanout = false;
thread_local CUcontext fanoutContext = nullptr;
thread_local uint32_t fanoutStream = 0;
thread_local size_t fanoutLoss = 0;
template <typename T> T sdkSymbol(const char *name) {
  return reinterpret_cast<T>(dlsym(RTLD_NEXT, name));
}
void request(uint8_t **buffer, size_t *size, size_t *maxRecords) {
  *size = 1024 * 1024;
  *buffer = static_cast<uint8_t *>(std::aligned_alloc(8, *size));
  *maxRecords = 0;
}
void collect(CUcontext context, uint32_t stream, uint8_t *buffer, size_t size,
             size_t valid) {
  CUpti_Activity *activity = nullptr;
  std::lock_guard<std::mutex> lock(mutex);
  CUptiResult status;
  while ((status = cuptiActivityGetNextRecord(buffer, valid, &activity)) ==
         CUPTI_SUCCESS) {
    if (activity->kind == CUPTI_ACTIVITY_KIND_EXTERNAL_CORRELATION) {
      auto *external =
          reinterpret_cast<CUpti_ActivityExternalCorrelation *>(activity);
      if (external->externalKind == CUPTI_EXTERNAL_CORRELATION_KIND_CUSTOM0)
        externalIds[external->correlationId] = external->externalId;
      continue;
    }
    if (activity->kind != CUPTI_ACTIVITY_KIND_CONCURRENT_KERNEL)
      continue;
    auto *kernel = reinterpret_cast<CUpti_ActivityKernel5 *>(activity);
    records.push_back({{"start_ns", uint64_t(kernel->start)},
                       {"end_ns", uint64_t(kernel->end)},
                       {"device_id", uint64_t(kernel->deviceId)},
                       {"context_id", uint64_t(kernel->contextId)},
                       {"stream_id", uint64_t(kernel->streamId)},
                       {"correlation_id", uint64_t(kernel->correlationId)},
                       {"name", kernel->name ? kernel->name : ""}});
  }
  if (status != CUPTI_ERROR_MAX_LIMIT_REACHED)
    callbackError = static_cast<int>(status);
  size_t loss = 0;
  auto getDrops = sdkSymbol<decltype(&cuptiActivityGetNumDroppedRecords)>(
      "cuptiActivityGetNumDroppedRecords");
  status = getDrops(context, stream, &loss);
  if (status != CUPTI_SUCCESS)
    callbackError = static_cast<int>(status);
  dropped += loss;
  fanoutLoss = loss;
}
void freeOnly(CUcontext, uint32_t, uint8_t *buffer, size_t, size_t) {
  std::free(buffer);
}
void fanoutComplete(CUcontext context, uint32_t stream, uint8_t *buffer,
                    size_t size, size_t valid) {
  inFanout = false;
  if (monitoring.load()) {
    collect(context, stream, buffer, size, valid);
    fanoutContext = context;
    fanoutStream = stream;
    inFanout = true;
  }
  if (primaryComplete)
    primaryComplete(context, stream, buffer, size, valid);
  inFanout = false;
}
} // namespace
extern "C" int reference_start() {
  {
    std::lock_guard<std::mutex> lock(mutex);
    records.clear();
    externalIds.clear();
    dropped = 0;
    callbackError = 0;
  }
  standalone = true;
  monitoring.store(true);
  auto status = cuptiActivityRegisterCallbacks(request, freeOnly);
  if (status != CUPTI_SUCCESS)
    return static_cast<int>(status);
  for (auto kind :
       {CUPTI_ACTIVITY_KIND_EXTERNAL_CORRELATION, CUPTI_ACTIVITY_KIND_DRIVER,
        CUPTI_ACTIVITY_KIND_CONCURRENT_KERNEL}) {
    status = cuptiActivityEnable(kind);
    if (status != CUPTI_SUCCESS)
      return static_cast<int>(status);
  }
  return 0;
}
extern "C" int reference_stop() {
  // The measurement driver synchronizes the application stream before this.
  auto status = cuptiActivityFlushAll(CUPTI_ACTIVITY_FLAG_FLUSH_FORCED);
  if (status != CUPTI_SUCCESS)
    return static_cast<int>(status);
  monitoring.store(false);
  for (auto kind :
       {CUPTI_ACTIVITY_KIND_DRIVER, CUPTI_ACTIVITY_KIND_EXTERNAL_CORRELATION}) {
    status = cuptiActivityDisable(kind);
    if (status != CUPTI_SUCCESS)
      return static_cast<int>(status);
  }
  if (standalone) {
    status = cuptiActivityDisable(CUPTI_ACTIVITY_KIND_CONCURRENT_KERNEL);
    if (status == CUPTI_SUCCESS)
      status = cuptiFinalize();
  }
  return status != CUPTI_SUCCESS ? static_cast<int>(status) : callbackError;
}
extern "C" const char *reference_json() {
  std::lock_guard<std::mutex> lock(mutex);
  uint32_t version = 0;
  cuptiGetVersion(&version);
  for (auto &record : records) {
    auto found = externalIds.find(record["correlation_id"].get<uint32_t>());
    record["external_id"] = found == externalIds.end()
                                ? nlohmann::json(nullptr)
                                : nlohmann::json(found->second);
  }
  output = nlohmann::json({{"source", "independent_cupti_activity_collector"},
                           {"cupti_version", version},
                           {"process_id", getpid()},
                           {"dropped_records", dropped},
                           {"records", records}})
               .dump();
  return output.c_str();
}

extern "C" int reference_push(uint64_t external) {
  return static_cast<int>(cuptiActivityPushExternalCorrelationId(
      CUPTI_EXTERNAL_CORRELATION_KIND_CUSTOM0, external));
}
extern "C" int reference_pop() {
  uint64_t external = 0;
  return static_cast<int>(cuptiActivityPopExternalCorrelationId(
      CUPTI_EXTERNAL_CORRELATION_KIND_CUSTOM0, &external));
}

// SDK callback fanout: the independent parser sees the exact SDK byte buffer
// before the registered collector frees it. It never calls FlagPrism APIs.
extern "C" CUptiResult CUPTIAPI cuptiActivityRegisterCallbacks(
    CUpti_BuffersCallbackRequestFunc requestCallback,
    CUpti_BuffersCallbackCompleteFunc completeCallback) {
  primaryComplete = completeCallback;
  auto registerCallbacks = sdkSymbol<decltype(&cuptiActivityRegisterCallbacks)>(
      "cuptiActivityRegisterCallbacks");
  return registerCallbacks(requestCallback, fanoutComplete);
}
extern "C" CUptiResult CUPTIAPI cuptiActivityGetNumDroppedRecords(
    CUcontext context, uint32_t stream, size_t *loss) {
  if (inFanout && context == fanoutContext && stream == fanoutStream) {
    *loss = fanoutLoss;
    return CUPTI_SUCCESS;
  }
  auto getDrops = sdkSymbol<decltype(&cuptiActivityGetNumDroppedRecords)>(
      "cuptiActivityGetNumDroppedRecords");
  return getDrops(context, stream, loss);
}
extern "C" int reference_begin_native() {
  {
    std::lock_guard<std::mutex> lock(mutex);
    records.clear();
    externalIds.clear();
    dropped = 0;
    callbackError = 0;
  }
  standalone = false;
  monitoring.store(true);
  for (auto kind :
       {CUPTI_ACTIVITY_KIND_EXTERNAL_CORRELATION, CUPTI_ACTIVITY_KIND_DRIVER}) {
    auto status = cuptiActivityEnable(kind);
    if (status != CUPTI_SUCCESS)
      return static_cast<int>(status);
  }
  return 0;
}
