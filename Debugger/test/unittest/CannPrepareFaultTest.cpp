// CPU-only SDK fault injection against the actual transfer/bridge sources.
#include "Debugger/Frontend/Bridge.h"
#include "acl/acl.h"
#include "acl/acl_rt.h"
#include <cassert>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
using namespace mlir::flagtree::debugger;
static std::string fault;
static int deviceAlloc = 0, hostAlloc = 0, deviceFree = 0, hostFree = 0;
extern "C" {
aclError aclrtGetCurrentContext(aclrtContext *context) {
  *context = reinterpret_cast<void *>(1);
  return ACL_SUCCESS;
}
const char *aclGetRecentErrMsg() { return "controlled CPU SDK fault"; }
aclError aclmdlRICaptureGetInfo(aclrtStream, aclmdlRICaptureStatus *status,
                                aclmdlRI *model) {
  *model = nullptr;
  *status = fault == "active"        ? ACL_MODEL_RI_CAPTURE_STATUS_ACTIVE
            : fault == "invalidated" ? ACL_MODEL_RI_CAPTURE_STATUS_INVALIDATED
                                     : ACL_MODEL_RI_CAPTURE_STATUS_NONE;
  return fault == "query" ? 107001 : ACL_SUCCESS;
}
aclError aclrtMalloc(void **p, size_t n, aclrtMemMallocPolicy) {
  ++deviceAlloc;
  *p = std::malloc(n);
  return ACL_SUCCESS;
}
aclError aclrtMallocHost(void **p, size_t n) {
  if (fault == "host" || fault == "host-and-free")
    return 107002;
  ++hostAlloc;
  *p = std::malloc(n);
  return ACL_SUCCESS;
}
aclError aclrtFree(void *p) {
  ++deviceFree;
  std::free(p);
  return fault == "host-and-free" ? 107003 : ACL_SUCCESS;
}
aclError aclrtFreeHost(void *p) {
  ++hostFree;
  std::free(p);
  return fault == "memset-and-free" ? 107004 : ACL_SUCCESS;
}
aclError aclrtMemset(void *p, size_t, int value, size_t n) {
  if (fault == "memset" || fault == "memset-and-free")
    return 107030;
  std::memset(p, value, n);
  return ACL_SUCCESS;
}
aclError aclrtMemsetAsync(void *p, size_t m, int v, size_t n, aclrtStream) {
  return aclrtMemset(p, m, v, n);
}
aclError aclrtMemcpy(void *p, size_t, const void *q, size_t n,
                     aclrtMemcpyKind) {
  std::memcpy(p, q, n);
  return ACL_SUCCESS;
}
aclError aclrtMemcpyAsync(void *p, size_t m, const void *q, size_t n,
                          aclrtMemcpyKind k, aclrtStream) {
  return aclrtMemcpy(p, m, q, n, k);
}
aclError aclrtSynchronizeStream(aclrtStream) { return ACL_SUCCESS; }
}
int main(int argc, char **argv) {
  assert(argc == 2);
  fault = argv[1];
  DebugKernelArtifacts artifacts;
  artifacts.hiddenArgEnabled = true;
  artifacts.bufferPlan.recordCapacity = 4;
  BufferMeta meta{};
  meta.backendKind = BackendKind::CANN;
  DebugRuntimeMetadata runtime{};
  if (fault == "invalid-backend") {
    auto engine =
        createTransferEngine(makeTransferEngineOptions(BackendKind::CANN, 123));
    meta.backendKind = BackendKind::CUDA;
    engine->prepare(meta, artifacts.bufferPlan, runtime);
    return 99;
  }
  auto bridge = createFrontendBridge();
  std::string original;
  try {
    auto prepared = bridge->prepareOwnedLaunch(artifacts, meta, runtime, 123);
    if (fault != "eager")
      throw std::logic_error("fault did not reject");
    auto exported =
        prepared.transferEngine->syncExport(prepared.request.launchContext);
    assert(!exported.rawBuffer.empty());
    prepared.transferEngine->release(prepared.request.launchContext);
  } catch (const std::runtime_error &error) {
    original = error.what();
  }
  if (fault == "unavailable") {
    assert(original.find("CANN debugger runtime is unavailable") !=
           std::string::npos);
    assert(deviceAlloc == 0 && hostAlloc == 0);
  } else if (fault == "active" || fault == "invalidated") {
    assert(original.find("eager launches only") != std::string::npos);
    assert(deviceAlloc == 0 && hostAlloc == 0);
  } else if (fault == "query") {
    assert(original.find("aclmdlRICaptureGetInfo") != std::string::npos &&
           original.find("107001") != std::string::npos);
    assert(deviceAlloc == 0 && hostAlloc == 0);
  } else if (fault == "host" || fault == "host-and-free") {
    assert(original.find("aclrtMallocHost") != std::string::npos &&
           original.find("107002") != std::string::npos);
    assert(deviceAlloc == 1 && deviceFree == 1 && hostAlloc == 0);
  } else if (fault == "memset" || fault == "memset-and-free") {
    assert(original.find("aclrtMemset") != std::string::npos &&
           original.find("107030") != std::string::npos);
    assert(deviceAlloc == 1 && deviceFree == 1 && hostAlloc == 1 &&
           hostFree == 1);
  } else {
    assert(fault == "eager" && original.empty());
    assert(deviceAlloc == 1 && deviceFree == 1 && hostAlloc == 1 &&
           hostFree == 1);
  }
  std::cout << "CPU_FAULT_PASS " << fault << " device_alloc=" << deviceAlloc
            << " host_alloc=" << hostAlloc << " device_free=" << deviceFree
            << " host_free=" << hostFree << " original=" << original << '\n';
}
