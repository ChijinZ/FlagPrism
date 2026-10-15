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
  std::free(ptr);
  return cleanupFails() ? code(905) : topsSuccess;
}
topsError_t topsHostFree(void *ptr) {
  ++hostFree;
  std::free(ptr);
  return cleanupFails() ? code(904) : topsSuccess;
}
topsError_t topsMemset(void *ptr, int value, size_t bytes) {
  ++memsets;
  if (fault == "memset" || fault == "memset-and-free")
    return code(902);
  std::memset(ptr, value, bytes);
  return topsSuccess;
}
topsError_t topsMemsetAsync(void *ptr, int value, size_t bytes, topsStream_t) {
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
                            topsMemcpyKind kind, topsStream_t) {
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
  auto bridge = createFrontendBridge();
  auto eager = [&] {
    auto prepared =
        bridge->prepareOwnedLaunch(artifacts, meta, runtime, actualStream);
    assert(prepared.request.hiddenArgValue != 0);
    auto exported =
        prepared.transferEngine->syncExport(prepared.request.launchContext);
    assert(exported.rawBuffer.size() >= sizeof(RingBufferHeader));
    RingBufferHeader header{};
    std::memcpy(&header, exported.rawBuffer.data(), sizeof(header));
    assert(header.capacity == 4 && header.writeIdx == 0);
    prepared.transferEngine->release(prepared.request.launchContext);
    assert(prepared.request.launchContext.deviceCtrlPtr == nullptr);
  };
  std::string original;
  try {
    eager();
    if (scenario != "eager")
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
    assert(scenario == "eager" && original.empty());
    assert(queries == 1 && deviceAlloc == 1 && hostAlloc == 1 &&
           deviceFree == 1 && hostFree == 1);
  }
  // Recovering from an early query or SDK allocation/header error leaves Python
  // alive; exercise a fresh native eager handle in the same CPU test process.
  if (scenario != "unavailable" && scenario != "cann-unavailable" &&
      scenario != "eager") {
    fault = "eager";
    eager();
    assert(deviceAlloc == deviceFree && hostAlloc == hostFree);
  }
  std::cout << "CPU_FAULT_PASS " << scenario << " queries=" << queries
            << " device_alloc=" << deviceAlloc << " host_alloc=" << hostAlloc
            << " device_free=" << deviceFree << " host_free=" << hostFree
            << " original=" << original << '\n';
}
