#ifndef PROTON_PROFILER_CANN_LAUNCH_RECEIPT_H_
#define PROTON_PROFILER_CANN_LAUNCH_RECEIPT_H_

#include <cstdint>
#include <string>
#include <vector>

namespace proton {

inline constexpr uint32_t kCannLaunchReceiptAbiVersion = 1;
inline constexpr const char *kCannLaunchReceiptCapsuleName =
    "flagprism.cann.launch_receipt.v1";

// Values are queried on the actual SDK launch worker, immediately following the
// original launch. Task zero is a valid value; query status establishes
// validity.
struct CannLaunchWorkerRecordV1 {
  uint32_t abiVersion{1};
  uint32_t structSize{64};
  uint64_t processId{0};
  uint64_t threadId{0};
  uint64_t streamHandle{0};
  int32_t deviceId{-1};
  int32_t streamId{-1};
  uint32_t taskId{0};
  int32_t launchStatus{-1};
  int32_t deviceQueryStatus{-1};
  int32_t streamQueryStatus{-1};
  int32_t taskQueryStatus{-1};
  uint32_t reserved{0};
};
static_assert(sizeof(CannLaunchWorkerRecordV1) == 64);

// Versioned POD capsule ABI. All callbacks are pure C++ and acquire no GIL.
// A caller obtains one owning reference from create and releases it exactly
// once. A queued worker must retain before dispatch and release at destruction.
struct CannLaunchReceiptSinkV1 {
  uint32_t abiVersion{1};
  uint32_t structSize{0};
  void *context{nullptr};
  void (*retain)(void *) noexcept {nullptr};
  void (*release)(void *) noexcept {nullptr};
  void (*publish)(void *, const CannLaunchWorkerRecordV1 *) noexcept {nullptr};
  void (*cancel)(void *, uint32_t) noexcept {nullptr};
  uint64_t tokenId{0};
  uint64_t scopeId{0};
  uint64_t sessionId{0};
  uint64_t captureEpoch{0};
};
static_assert(sizeof(CannLaunchReceiptSinkV1) == 80);

struct CannLaunchReceipt {
  uint64_t tokenId{0};
  uint64_t scopeId{0};
  uint64_t sessionId{0};
  uint64_t captureEpoch{0};
  std::string collectorOutputPath;
  std::string sdkCapturePath;
  std::string sdkCaptureBindingStatus;
  std::string sdkCaptureBindingEvidence;
  CannLaunchWorkerRecordV1 worker;
  uint64_t publishCount{0};
  bool lateCallback{false};
  std::string status;
  std::string reason;
};

// The binding must validate that sessionId is a live CANN session before this
// call. nullptr means no active native SDK collector or a bounded registry
// full.
CannLaunchReceiptSinkV1 *createCannLaunchReceiptSink(uint64_t scopeId,
                                                     uint64_t sessionId);
bool cannLaunchReceiptCaptureActive() noexcept;
void cancelCannLaunchReceiptSink(CannLaunchReceiptSinkV1 *sink,
                                 const std::string &reason);
// Returns snapshots (including pending/late/ambiguous), never infers a task.
std::vector<CannLaunchReceipt> drainCannLaunchReceipts(uint64_t sessionId);

// Native collector lifecycle only; no SDK session can be started by a capsule.
uint64_t beginCannLaunchReceiptCapture(uint32_t deviceId,
                                       const std::string &outputPath);
void endCannLaunchReceiptCapture(uint64_t captureEpoch,
                                 const std::string &reason);
void sealCannLaunchReceiptCapture(uint64_t captureEpoch,
                                  const std::string &sdkCapturePath,
                                  const std::string &bindingStatus,
                                  const std::string &bindingEvidence);

} // namespace proton

#endif
