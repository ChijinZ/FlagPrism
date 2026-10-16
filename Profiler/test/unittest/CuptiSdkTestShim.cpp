// CPU-only SDK boundary. Production CuptiApi dispatch loads this test library.
#include "CuptiSdkTestShim.h"
#include <cstring>
#include <cuda.h>
#include <cupti.h>
#include <cupti_pcsampling.h>
#include <map>
#include <set>
#include <string>
namespace {
std::map<std::string, int> failures, counts;
std::set<CUpti_ActivityKind> activities;
std::set<std::pair<CUpti_CallbackDomain, CUpti_CallbackId>> callbacks;
bool subscriberLive = false, pcLive = false;
bool externalErrorHandle = false;
bool call(const char *operation) {
  ++counts[operation];
  auto &left = failures[operation];
  if (left > 0) {
    --left;
    return false;
  }
  return true;
}
} // namespace
extern "C" {
void r7Fail(const char *operation, int count) { failures[operation] = count; }
int r7Calls(const char *operation) { return counts[operation]; }
void r7ExternalSubscriber(int active) {
  subscriberLive = active != 0;
  externalErrorHandle = active == 2;
}
int r7LiveResources() {
  return static_cast<int>(activities.size() + callbacks.size()) +
         subscriberLive + pcLive;
}
CUptiResult cuptiSubscribe(CUpti_SubscriberHandle *handle, CUpti_CallbackFunc,
                           void *) {
  if (!call("subscribe"))
    return CUPTI_ERROR_INVALID_PARAMETER;
  if (subscriberLive) {
    if (externalErrorHandle)
      *handle = reinterpret_cast<CUpti_SubscriberHandle>(0x4567);
    return CUPTI_ERROR_INVALID_PARAMETER;
  }
  subscriberLive = true;
  *handle = reinterpret_cast<CUpti_SubscriberHandle>(0x4567);
  return CUPTI_SUCCESS;
}
CUptiResult cuptiUnsubscribe(CUpti_SubscriberHandle handle) {
  if (!call("unsubscribe"))
    return CUPTI_ERROR_UNKNOWN;
  if (!subscriberLive ||
      handle != reinterpret_cast<CUpti_SubscriberHandle>(0x4567))
    return CUPTI_ERROR_INVALID_PARAMETER;
  subscriberLive = false;
  callbacks.clear();
  return CUPTI_SUCCESS;
}
CUptiResult cuptiFinalize() {
  if (!call("finalize"))
    return CUPTI_ERROR_UNKNOWN;
  // V1 single-subscriber successful global-finalize lifecycle contract.
  subscriberLive = false;
  pcLive = false;
  activities.clear();
  callbacks.clear();
  return CUPTI_SUCCESS;
}
CUptiResult cuptiEnableCallback(uint32_t enable, CUpti_SubscriberHandle,
                                CUpti_CallbackDomain domain,
                                CUpti_CallbackId id) {
  if (!call(enable ? "callback-enable" : "callback-disable"))
    return CUPTI_ERROR_UNKNOWN;
  if (enable)
    callbacks.emplace(domain, id);
  else
    callbacks.erase({domain, id});
  return CUPTI_SUCCESS;
}
CUptiResult cuptiActivityEnable(CUpti_ActivityKind kind) {
  if (!call("activity-enable"))
    return CUPTI_ERROR_UNKNOWN;
  activities.insert(kind);
  return CUPTI_SUCCESS;
}
CUptiResult cuptiActivityDisable(CUpti_ActivityKind kind) {
  if (!call("activity-disable"))
    return CUPTI_ERROR_UNKNOWN;
  if (!activities.count(kind))
    return CUPTI_ERROR_INVALID_KIND;
  activities.erase(kind);
  return CUPTI_SUCCESS;
}
CUptiResult cuptiActivityRegisterCallbacks(CUpti_BuffersCallbackRequestFunc,
                                           CUpti_BuffersCallbackCompleteFunc) {
  return call("register-callbacks") ? CUPTI_SUCCESS : CUPTI_ERROR_UNKNOWN;
}
CUptiResult cuptiActivityFlushAll(uint32_t) { return CUPTI_SUCCESS; }
CUptiResult cuptiGetContextId(CUcontext, uint32_t *id) {
  *id = 9;
  return CUPTI_SUCCESS;
}
CUptiResult cuptiGetVersion(uint32_t *version) {
  *version = CUPTI_API_VERSION;
  return CUPTI_SUCCESS;
}
CUptiResult cuptiPCSamplingEnable(CUpti_PCSamplingEnableParams *) {
  pcLive = true;
  call("pc-enable");
  return CUPTI_SUCCESS;
}
CUptiResult cuptiPCSamplingDisable(CUpti_PCSamplingDisableParams *) {
  if (!call("pc-disable"))
    return CUPTI_ERROR_UNKNOWN;
  pcLive = false;
  return CUPTI_SUCCESS;
}
CUptiResult
cuptiPCSamplingGetNumStallReasons(CUpti_PCSamplingGetNumStallReasonsParams *p) {
  *p->numStallReasons = 1;
  return CUPTI_SUCCESS;
}
CUptiResult
cuptiPCSamplingGetStallReasons(CUpti_PCSamplingGetStallReasonsParams *p) {
  std::strcpy(p->stallReasons[0], "stalled_selected");
  p->stallReasonIndex[0] = 0;
  return CUPTI_SUCCESS;
}
CUptiResult cuptiPCSamplingSetConfigurationAttribute(
    CUpti_PCSamplingConfigurationInfoParams *) {
  return CUPTI_SUCCESS;
}
CUresult cuCtxGetCurrent(CUcontext *ctx) {
  *ctx = nullptr;
  call("ctx-current");
  return CUDA_SUCCESS;
}
CUresult cuInit(unsigned int) {
  call("unexpected-device-init");
  return CUDA_ERROR_NOT_INITIALIZED;
}
}
