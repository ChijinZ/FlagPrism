// Real EnflameProfiler linked against the installed TOPS headers. Only the SDK
// boundary is replaced. Each CTest case runs in a fresh process/singleton.
#include "Profiler/Profiler.h"
#include "Profiler/Vendor/EnflameProfiler.h"
#include <algorithm>
#include <functional>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <tops/tops_runtime.h>
#include <topspti_activity.h>
#include <topspti_callbacks.h>
#include <vector>
namespace {
std::set<Topspti_ActivityKind> activities;
std::set<Topspti_CallbackDomain> domains;
std::vector<std::string> calls;
bool subscribed = false;
bool externalErrorHandle = false;
int subscribes = 0, unsubscribes = 0, failUnsubscribe = 0;
int failDisable = 0, failEnable = 0, failRegister = 0;
void externalRequest(uint8_t **, size_t *, size_t *) {}
void externalComplete(uint8_t *, size_t, size_t) {}
Topspti_BuffersCallbackRequestFunc requestHandler = externalRequest;
Topspti_BuffersCallbackCompleteFunc completeHandler = externalComplete;
Topspti_ActivityKind failKind = TOPSPTI_ACTIVITY_KIND_KERNEL;
void require(bool condition, const char *message) {
  if (!condition)
    throw std::runtime_error(message);
}
std::string failure(const std::function<void()> &operation) {
  try {
    operation();
  } catch (const std::runtime_error &error) {
    return error.what();
  }
  throw std::runtime_error("Expected SDK failure was silently ignored");
}
} // namespace
extern "C" {
TopsptiResult topsptiSubscribe(Topspti_SubscriberHandle *out,
                               Topspti_CallbackFunc, void *) {
  ++subscribes;
  calls.push_back("subscribe");
  if (subscribed) {
    if (externalErrorHandle)
      *out = reinterpret_cast<Topspti_SubscriberHandle>(0x1234);
    return TOPSPTI_ERROR_MULTIPLE_SUBSCRIBERS_NOT_SUPPORTED;
  }
  subscribed = true;
  *out = reinterpret_cast<Topspti_SubscriberHandle>(0x1234);
  return TOPSPTI_SUCCESS;
}
TopsptiResult topsptiUnsubscribe(Topspti_SubscriberHandle handle) {
  ++unsubscribes;
  calls.push_back("unsubscribe");
  require(subscribed &&
              handle == reinterpret_cast<Topspti_SubscriberHandle>(0x1234),
          "Unknown subscriber handle");
  if (failUnsubscribe > 0) {
    --failUnsubscribe;
    return TOPSPTI_ERROR_INVALID_PARAMETER;
  }
  subscribed = false;
  domains.clear();
  return TOPSPTI_SUCCESS;
}
TopsptiResult topsptiEnableDomain(uint32_t enable, Topspti_SubscriberHandle,
                                  Topspti_CallbackDomain domain) {
  calls.push_back(enable ? "enable-domain" : "disable-domain");
  if (enable)
    domains.insert(domain);
  else
    domains.erase(domain);
  return TOPSPTI_SUCCESS;
}
TopsptiResult topsptiActivityEnable(Topspti_ActivityKind kind) {
  calls.push_back("enable:" + std::to_string(kind));
  if (failEnable > 0 && kind == failKind) {
    --failEnable;
    return TOPSPTI_ERROR_INVALID_PARAMETER;
  }
  activities.insert(kind);
  return TOPSPTI_SUCCESS;
}
TopsptiResult topsptiActivityDisable(Topspti_ActivityKind kind) {
  calls.push_back("disable:" + std::to_string(kind));
  if (failDisable > 0 && kind == failKind) {
    --failDisable;
    return TOPSPTI_ERROR_INVALID_PARAMETER;
  }
  activities.erase(kind);
  return TOPSPTI_SUCCESS;
}
TopsptiResult
topsptiActivityRegisterCallbacks(Topspti_BuffersCallbackRequestFunc request,
                                 Topspti_BuffersCallbackCompleteFunc complete) {
  calls.push_back("register-handlers");
  if (failRegister > 0) {
    --failRegister;
    return TOPSPTI_ERROR_INVALID_PARAMETER;
  }
  requestHandler = request;
  completeHandler = complete;
  return TOPSPTI_SUCCESS;
}
TopsptiResult topsptiActivityFlushAll(uint32_t) { return TOPSPTI_SUCCESS; }
TopsptiResult topsptiActivityGetNumDroppedRecords(size_t *dropped) {
  *dropped = 0;
  return TOPSPTI_SUCCESS;
}
TopsptiResult topsptiActivityGetNextRecord(uint8_t *, size_t,
                                           Topspti_Activity **) {
  return TOPSPTI_ERROR_MAX_LIMIT_REACHED;
}
topsError_t topsDeviceSynchronize() { return topsSuccess; }
}
int main(int argc, char **argv) {
  try {
    require(argc == 2, "One case name required");
    proton::EnflameAdapter adapter;
    auto *profiler = adapter.getRuntimeProfiler();
    std::string test = argv[1];
    if (test == "external" || test == "external-partial") {
      subscribed = true;
      externalErrorHandle = test == "external-partial";
      failure([&] { profiler->start(); });
      require(subscribed && unsubscribes == 0,
              "Failed acquisition destroyed an external subscriber");
      require(requestHandler == externalRequest &&
                  completeHandler == externalComplete &&
                  std::count(calls.begin(), calls.end(), "register-handlers") ==
                      0,
              "Failed acquisition replaced external activity handlers");
      if (externalErrorHandle) {
        auto error = failure([&] { profiler->start(); });
        require(
            error.find("ownership") != std::string::npos && subscribes == 1,
            "Unknown subscriber ownership did not refuse fresh acquisition");
        require(unsubscribes == 0,
                "Unknown subscriber ownership attempted teardown");
      }
      subscribed = false;
    } else if (test == "register") {
      failRegister = 1;
      auto error = failure([&] { profiler->start(); });
      require(error.find("register activity callbacks") != std::string::npos,
              "Registration failure lost original SDK error");
      require(!subscribed && unsubscribes == 1 && activities.empty() &&
                  domains.empty(),
              "Registration failure did not release the owned subscriber");
      require(requestHandler == externalRequest &&
                  completeHandler == externalComplete,
              "Failed registration changed handler pointers");
      profiler->start();
      require(subscribes == 2 && subscribed &&
                  requestHandler != externalRequest &&
                  completeHandler != externalComplete,
              "Registration failure did not recover on a fresh start");
      require(calls.size() >= 3 && calls[0] == "subscribe" &&
                  calls[1] == "register-handlers" && calls[2] == "unsubscribe",
              "Activity handlers were registered before subscriber ownership");
    } else if (test == "disable") {
      profiler->start();
      failDisable = 1;
      require(failure([&] {
                profiler->stop();
              }).find("disable detailed activity") != std::string::npos,
              "Original disable error lost");
      require(std::count_if(
                  calls.begin(), calls.end(),
                  [](const auto &s) { return s.find("disable:") == 0; }) == 5,
              "A disable error skipped another activity cleanup");
      require(unsubscribes == 1 && !subscribed,
              "Activity failure skipped unsubscribe");
      require(activities.size() == 1,
              "Fault model must retain failed activity");
      profiler->start();
      require(subscribes == 2,
              "Recovery did not restart after pending cleanup");
    } else if (test == "unsubscribe" || test == "repeat") {
      profiler->start();
      failUnsubscribe = test == "repeat" ? 2 : 1;
      require(failure([&] {
                profiler->stop();
              }).find("unsubscribe callbacks") != std::string::npos,
              "Unsubscribe error lost");
      require(subscribed && activities.empty(),
              "Failed handle was forgotten or activities not cleaned");
      if (test == "repeat") {
        failure([&] { profiler->start(); });
        require(subscribes == 1,
                "Repeated cleanup failure must reject fresh subscription");
      }
      profiler->start();
      require(subscribes == 2, "Pending subscriber did not recover");
    } else if (test == "partial") {
      failKind = TOPSPTI_ACTIVITY_KIND_MEMCPY;
      failEnable = 1;
      failUnsubscribe = 1;
      auto error = failure([&] { profiler->start(); });
      require(error.find("enable detailed activity") != std::string::npos,
              "Partial-start cleanup replaced original error");
      require(unsubscribes == 1 && subscribed && activities.empty(),
              "Partial start must retain failed unsubscribe but clean acquired "
              "activity");
      profiler->start();
      require(subscribes == 2,
              "Partial-start pending handle was not cleaned before restart");
    } else {
      throw std::runtime_error("Unknown case");
    }
    profiler->stop();
    require(!subscribed && activities.empty() && domains.empty(),
            "Final SDK resources remain owned");
    std::cout << "PASS " << test << " subscribes=" << subscribes
              << " unsubscribes=" << unsubscribes << '\n';
    return 0;
  } catch (const std::exception &error) {
    std::cerr << "FAIL " << (argc > 1 ? argv[1] : "unknown") << ": "
              << error.what() << '\n';
    for (const auto &call : calls)
      std::cerr << call << '\n';
    return 1;
  }
}
