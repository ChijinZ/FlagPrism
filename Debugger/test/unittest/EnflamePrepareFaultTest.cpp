// CPU-only SDK ABI fault injection. Never links or invokes the real runtime.
#include "Debugger/Common/Protocol.h"
#include "Debugger/Frontend/Bridge.h"
#include "tops/tops_runtime.h"
#include <cassert>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>

using namespace mlir::flagtree::debugger;
namespace {
std::string fault;
int deviceAttempts = 0, hostAttempts = 0;
int deviceAlloc = 0, hostAlloc = 0, deviceFree = 0, hostFree = 0;
int queries = 0, memsets = 0, copies = 0;
uint64_t memsetStream = 0, headerCopyStream = 0;
constexpr uint64_t actualStream = 0x123456;
topsError_t code(int value) { return static_cast<topsError_t>(value); }
bool cleanupFails() { return fault.find("and-free") != std::string::npos; }
} // namespace

extern "C" {
const char *topsGetErrorString(topsError_t) {
  return "controlled CPU TOPS fault";
}
topsError_t topsGetDeviceCount(int *count) {
  *count = 1;
  return topsSuccess;
}
topsError_t topsSetDevice(int) { return topsSuccess; }
topsError_t topsStreamIsCapturing(topsStream_t stream,
                                  topsStreamCaptureStatus *status) {
  ++queries;
  assert(reinterpret_cast<uint64_t>(stream) == actualStream);
  *status = fault == "active"        ? topsStreamCaptureStatusActive
            : fault == "invalidated" ? topsStreamCaptureStatusInvalidated
                                     : topsStreamCaptureStatusNone;
  return fault == "query" ? topsErrorStreamCaptureImplicit : topsSuccess;
}
topsError_t topsMalloc(void **ptr, size_t bytes) {
  ++deviceAttempts;
  if (fault == "malloc")
    return topsErrorStreamCaptureUnsupported;
  *ptr = std::malloc(bytes);
  assert(*ptr);
  ++deviceAlloc;
  return topsSuccess;
}
topsError_t topsHostMalloc(void **ptr, size_t bytes, unsigned int) {
  ++hostAttempts;
  if (fault == "host" || fault == "host-and-free")
    return code(901);
  *ptr = std::malloc(bytes);
  assert(*ptr);
  ++hostAlloc;
  return topsSuccess;
}
topsError_t topsFree(void *ptr) {
  ++deviceFree;
  if (fault == "release-device-before")
    return code(905);
  std::free(ptr);
  if (fault == "release-device-after")
    return code(905);
  return cleanupFails() ? code(905) : topsSuccess;
}
topsError_t topsHostFree(void *ptr) {
  ++hostFree;
  if (fault == "release-host-before")
    return code(904);
  std::free(ptr);
  if (fault == "release-host-after")
    return code(904);
  return cleanupFails() ? code(904) : topsSuccess;
}
topsError_t topsMemset(void *ptr, int value, size_t bytes) {
  ++memsets;
  if (fault == "memset" || fault == "memset-and-free")
    return code(902);
  std::memset(ptr, value, bytes);
  return topsSuccess;
}
topsError_t topsMemsetAsync(void *ptr, int value, size_t bytes,
                            topsStream_t stream) {
  memsetStream = reinterpret_cast<uint64_t>(stream);
  return topsMemset(ptr, value, bytes);
}
topsError_t topsMemcpy(void *dst, const void *src, size_t bytes,
                       topsMemcpyKind) {
  ++copies;
  if (fault == "copy" || fault == "copy-and-free")
    return code(903);
  std::memcpy(dst, src, bytes);
  return topsSuccess;
}
topsError_t topsMemcpyAsync(void *dst, const void *src, size_t bytes,
                            topsMemcpyKind kind, topsStream_t stream) {
  if (kind == topsMemcpyHostToDevice)
    headerCopyStream = reinterpret_cast<uint64_t>(stream);
  return topsMemcpy(dst, src, bytes, kind);
}
topsError_t topsStreamSynchronize(topsStream_t) { return topsSuccess; }
}

int main(int argc, char **argv) {
  assert(argc == 2);
  const std::string scenario = fault = argv[1];
  DebugKernelArtifacts artifacts;
  artifacts.hiddenArgEnabled = true;
  artifacts.bufferPlan.recordCapacity = 4;
  BufferMeta meta{};
  meta.backendKind =
      scenario == "cann-unavailable" ? BackendKind::CANN : BackendKind::ENFLAME;
  DebugRuntimeMetadata runtime{};
  const bool timelineStream = scenario == "stream-v2" ||
                              scenario == "stream-v3" ||
                              scenario.find("guard-") == 0;
  if (timelineStream) {
    runtime.recordLayout = scenario == "stream-v2"
                               ? "gcu_first_last_timeline_v2"
                               : "gcu_execution_timeline_v3";
    runtime.hasLaunchGrid = true;
    runtime.gridX = 3;
    runtime.gridY = runtime.gridZ = 1;
    artifacts.bufferPlan.recordSize = scenario == "stream-v2" ? 64 : 128;
  }
  auto bridge = createFrontendBridge();
  auto eager = [&] {
    auto prepared =
        bridge->prepareOwnedLaunch(artifacts, meta, runtime, actualStream);
    if (timelineStream &&
        (memsetStream != actualStream || headerCopyStream != actualStream))
      throw std::logic_error(
          "timeline initialization escaped the launch stream");
    assert(prepared.request.hiddenArgValue != 0);
    auto &context = prepared.request.launchContext;
    auto *device = static_cast<uint8_t *>(context.deviceCtrlPtr);
    if (timelineStream) {
      for (size_t i = 0; i != 64; ++i) {
        assert(device[-64 + static_cast<ptrdiff_t>(i)] == 165);
        assert(device[context.bufferSize + i] == 165);
      }
      if (scenario == "guard-prefix")
        device[-1] = 164;
      if (scenario == "guard-suffix")
        device[context.bufferSize] = 164;
    }
    auto exported =
        prepared.transferEngine->syncExport(prepared.request.launchContext);
    assert(exported.rawBuffer.size() >= sizeof(RingBufferHeader));
    RingBufferHeader header{};
    std::memcpy(&header, exported.rawBuffer.data(), sizeof(header));
    assert(header.capacity == 4 && header.writeIdx == 0);
    if (timelineStream) {
      const auto *host = static_cast<const uint8_t *>(context.hostBufferPtr);
      for (size_t i = 0; i != 64; ++i) {
        assert(host[-64 + static_cast<ptrdiff_t>(i)] ==
               (scenario == "guard-prefix" && i == 63 ? 164 : 165));
        assert(host[context.bufferSize + i] ==
               (scenario == "guard-suffix" && i == 0 ? 164 : 165));
      }
    }
    if (scenario.find("release-") == 0) {
      void *hostIdentity = context.hostBufferPtr;
      void *deviceIdentity = context.deviceCtrlPtr;
      for (int attempt = 0; attempt != 2; ++attempt) {
        bool rejected = false;
        try {
          prepared.transferEngine->release(context);
        } catch (const std::runtime_error &error) {
          rejected = std::string(error.what()).find("quarantined") !=
                     std::string::npos;
        }
        assert(rejected && context.deviceCtrlPtr == deviceIdentity);
        assert(hostFree == 1 && deviceFree == 1);
      }
      bool accessRejected = false;
      try {
        prepared.transferEngine->syncExport(context);
      } catch (const std::runtime_error &error) {
        accessRejected =
            std::string(error.what()).find("quarantined") != std::string::npos;
      }
      assert(accessRejected);
      // Only the fixture knows whether its failing SDK call had a side effect.
      // The production runtime must never make this inference or retry free.
      if (scenario == "release-host-before")
        std::free(hostIdentity);
      if (scenario == "release-device-before")
        std::free(deviceIdentity);
      return;
    }
    prepared.transferEngine->release(prepared.request.launchContext);
    assert(prepared.request.launchContext.deviceCtrlPtr == nullptr);
  };
  std::string original;
  try {
    eager();
    if (scenario.find("release-") == 0) {
      std::cout << "CPU_FAULT_PASS " << scenario << '\n';
      return 0;
    }
    if (scenario != "eager" && !timelineStream)
      throw std::logic_error("fault did not reject");
  } catch (const std::runtime_error &error) {
    original = error.what();
  }
  if (scenario == "active" || scenario == "invalidated" ||
      scenario == "query") {
    assert(queries == 1 && deviceAttempts == 0 && hostAttempts == 0 &&
           memsets == 0 && copies == 0);
    if (scenario == "query") {
      assert(original.find("topsStreamIsCapturing") != std::string::npos &&
             original.find("906") != std::string::npos);
    } else {
      assert(original.find("graph capture") != std::string::npos);
    }
  } else if (scenario == "malloc") {
    assert(original.find("topsMalloc") != std::string::npos &&
           original.find("900") != std::string::npos);
    assert(deviceAttempts == 1 && deviceAlloc == 0 && hostAttempts == 0 &&
           deviceFree == 0);
  } else if (scenario == "host" || scenario == "host-and-free") {
    assert(original.find("topsHostMalloc") != std::string::npos &&
           original.find("901") != std::string::npos);
    assert(deviceAlloc == 1 && deviceFree == 1 && hostAttempts == 1 &&
           hostAlloc == 0 && hostFree == 0);
  } else if (scenario == "memset" || scenario == "memset-and-free" ||
             scenario == "copy" || scenario == "copy-and-free") {
    const bool copy = scenario.find("copy") == 0;
    assert(original.find(copy ? "topsMemcpy" : "topsMemset") !=
           std::string::npos);
    assert(original.find(copy ? "903" : "902") != std::string::npos);
    assert(deviceAlloc == 1 && hostAlloc == 1 && deviceFree == 1 &&
           hostFree == 1);
    assert(memsets == 1 && copies == (copy ? 1 : 0));
  } else if (scenario == "unavailable" || scenario == "cann-unavailable") {
    assert(original.find("unavailable") != std::string::npos);
    assert(original.find(scenario == "unavailable" ? "Enflame" : "CANN") !=
           std::string::npos);
    assert(queries == 0 && deviceAttempts == 0 && hostAttempts == 0);
  } else {
    assert((scenario == "eager" || timelineStream) && original.empty());
    assert(queries == 1 && deviceAlloc == 1 && hostAlloc == 1 &&
           deviceFree == 1 && hostFree == 1);
  }
  // Recovering from an early query or SDK allocation/header error leaves Python
  // alive; exercise a fresh native eager handle in the same CPU test process.
  if (scenario != "unavailable" && scenario != "cann-unavailable" &&
      scenario != "eager" && !timelineStream) {
    fault = "eager";
    eager();
    assert(deviceAlloc == deviceFree && hostAlloc == hostFree);
  }
  std::cout << "CPU_FAULT_PASS " << scenario << " queries=" << queries
            << " device_alloc=" << deviceAlloc << " host_alloc=" << hostAlloc
            << " device_free=" << deviceFree << " host_free=" << hostFree
            << " original=" << original << '\n';
}
