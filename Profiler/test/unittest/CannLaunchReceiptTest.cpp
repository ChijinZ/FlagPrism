// CPU unit tests of the actual registry API. Constructed worker POD records
// exercise ownership/schema contracts; no SDK query or NPU launch is performed.
#include "Profiler/Vendor/CannLaunchReceipt.h"
#include "gtest/gtest.h"

#include <algorithm>
#include <atomic>
#include <set>
#include <thread>
#include <vector>

namespace proton {
namespace {

CannLaunchWorkerRecordV1 validWorker(uint32_t task = 0) {
  CannLaunchWorkerRecordV1 value;
  value.structSize = sizeof(value);
  value.processId = 17;
  value.threadId = 19;
  value.deviceId = 0;
  value.streamId = 0;
  value.taskId = task;
  value.launchStatus = 0;
  value.deviceQueryStatus = 0;
  value.streamQueryStatus = 0;
  value.taskQueryStatus = 0;
  return value;
}

class CannLaunchReceiptTest : public testing::Test {
protected:
  void SetUp() override { ASSERT_NE(open(), 0u); }
  void TearDown() override {
    for (auto epoch : epochs)
      endCannLaunchReceiptCapture(epoch, "CPU fixture closed");
    for (auto session : sessions)
      drainCannLaunchReceipts(session);
    for (auto *sink : owners)
      sink->release(sink->context);
  }
  uint64_t open() {
    auto epoch = beginCannLaunchReceiptCapture(0, "CPU registry fixture");
    if (epoch)
      epochs.push_back(epoch);
    return epoch;
  }
  CannLaunchReceiptSinkV1 *create(uint64_t scope = 0, uint64_t session = 0) {
    auto *sink = createCannLaunchReceiptSink(scope, session);
    if (sink) {
      owners.push_back(sink);
      sessions.insert(session);
    }
    return sink;
  }
  void releaseOwner(CannLaunchReceiptSinkV1 *sink) {
    auto found = std::find(owners.begin(), owners.end(), sink);
    ASSERT_NE(found, owners.end());
    owners.erase(found);
    sink->release(sink->context);
  }
  CannLaunchReceipt row(CannLaunchReceiptSinkV1 *sink) {
    const auto rows = drainCannLaunchReceipts(sink->sessionId);
    auto found = std::find_if(rows.begin(), rows.end(), [&](const auto &value) {
      return value.tokenId == sink->tokenId;
    });
    EXPECT_NE(found, rows.end());
    return found == rows.end() ? CannLaunchReceipt{} : *found;
  }
  std::vector<uint64_t> epochs;
  std::vector<CannLaunchReceiptSinkV1 *> owners;
  std::set<uint64_t> sessions;
};

TEST_F(CannLaunchReceiptTest, ZeroIdsAndSuccessfulQueriesAreValid) {
  auto *sink = create();
  ASSERT_NE(sink, nullptr);
  EXPECT_EQ(sink->abiVersion, kCannLaunchReceiptAbiVersion);
  EXPECT_EQ(sink->structSize, sizeof(*sink));
  EXPECT_NE(sink->context, nullptr);
  EXPECT_NE(sink->retain, nullptr);
  EXPECT_NE(sink->release, nullptr);
  EXPECT_NE(sink->publish, nullptr);
  EXPECT_NE(sink->cancel, nullptr);
  auto worker = validWorker();
  sink->publish(sink->context, &worker);
  auto receipt = row(sink);
  EXPECT_EQ(receipt.status, "collected");
  EXPECT_EQ(receipt.scopeId, 0u);
  EXPECT_EQ(receipt.sessionId, 0u);
  EXPECT_EQ(receipt.worker.deviceId, 0);
  EXPECT_EQ(receipt.worker.streamId, 0);
  EXPECT_EQ(receipt.worker.taskId, 0u);
  EXPECT_EQ(receipt.publishCount, 1u);
  EXPECT_FALSE(receipt.lateCallback);
}

TEST_F(CannLaunchReceiptTest, FailedQueriesNeverCertifyIdentity) {
  for (int query = 0; query != 3; ++query) {
    auto *sink = create(query);
    ASSERT_NE(sink, nullptr);
    auto worker = validWorker();
    if (query == 0)
      worker.deviceQueryStatus = 1;
    if (query == 1)
      worker.streamQueryStatus = 1;
    if (query == 2)
      worker.taskQueryStatus = 1;
    sink->publish(sink->context, &worker);
    EXPECT_EQ(row(sink).status, "query_failed");
  }
}

TEST_F(CannLaunchReceiptTest, LaunchFailurePreservesActualStatus) {
  auto *sink = create();
  ASSERT_NE(sink, nullptr);
  auto worker = validWorker();
  worker.launchStatus = 7;
  sink->publish(sink->context, &worker);
  EXPECT_EQ(row(sink).status, "launch_failed");
  EXPECT_EQ(row(sink).worker.launchStatus, 7);
}

TEST_F(CannLaunchReceiptTest, InvalidVersionSizeAndNullPayloadAreRejected) {
  for (int kind = 0; kind != 3; ++kind) {
    auto *sink = create(kind);
    ASSERT_NE(sink, nullptr);
    auto worker = validWorker();
    if (kind == 0)
      ++worker.abiVersion;
    if (kind == 1)
      --worker.structSize;
    sink->publish(sink->context, kind == 2 ? nullptr : &worker);
    EXPECT_NE(row(sink).status, "collected");
    EXPECT_EQ(row(sink).publishCount, 1u);
  }
}

TEST_F(CannLaunchReceiptTest, DeviceMismatchIsNotACollectedReceipt) {
  auto *sink = create();
  ASSERT_NE(sink, nullptr);
  auto worker = validWorker();
  worker.deviceId = 1;
  sink->publish(sink->context, &worker);
  EXPECT_EQ(row(sink).status, "device_mismatch");
}

TEST_F(CannLaunchReceiptTest, DuplicateCannotReplaceFirstPayload) {
  auto *sink = create();
  ASSERT_NE(sink, nullptr);
  auto first = validWorker(3), second = validWorker(5);
  sink->publish(sink->context, &first);
  sink->publish(sink->context, &second);
  auto receipt = row(sink);
  EXPECT_EQ(receipt.status, "duplicate_publish");
  EXPECT_EQ(receipt.publishCount, 2u);
  EXPECT_EQ(receipt.worker.taskId, first.taskId);
}

TEST_F(CannLaunchReceiptTest, CloseRejectsCreationAndLatePayloadMutation) {
  auto *sink = create();
  ASSERT_NE(sink, nullptr);
  auto first = validWorker(3), later = validWorker(5);
  sink->publish(sink->context, &first);
  endCannLaunchReceiptCapture(sink->captureEpoch, "collector closed");
  EXPECT_FALSE(cannLaunchReceiptCaptureActive());
  EXPECT_EQ(createCannLaunchReceiptSink(9, 0), nullptr);
  sink->publish(sink->context, &later);
  auto receipt = row(sink);
  EXPECT_TRUE(receipt.lateCallback);
  EXPECT_NE(receipt.status, "collected");
  EXPECT_EQ(receipt.publishCount, 1u);
  EXPECT_EQ(receipt.worker.taskId, first.taskId);
}

TEST_F(CannLaunchReceiptTest,
       PendingCloseThenLatePublishNeverBecomesCollected) {
  auto *sink = create();
  ASSERT_NE(sink, nullptr);
  EXPECT_EQ(row(sink).status, "pending");
  endCannLaunchReceiptCapture(sink->captureEpoch, "closed before worker");
  auto worker = validWorker();
  sink->publish(sink->context, &worker);
  EXPECT_TRUE(row(sink).lateCallback);
  EXPECT_NE(row(sink).status, "collected");
  EXPECT_EQ(row(sink).publishCount, 0u);
}

TEST_F(CannLaunchReceiptTest, CancelBeforeOrAfterPublishCannotCertifyReceipt) {
  for (bool before : {true, false}) {
    auto *sink = create(before ? 1 : 2);
    ASSERT_NE(sink, nullptr);
    auto worker = validWorker();
    if (before)
      cancelCannLaunchReceiptSink(sink, "prelaunch rejection");
    sink->publish(sink->context, &worker);
    if (!before)
      sink->cancel(sink->context, 9);
    EXPECT_EQ(row(sink).status, "cancelled");
  }
}

TEST_F(CannLaunchReceiptTest, ReusedTaskIdsDoNotMixEpochOrSessionMembership) {
  auto *old = create(0, 10);
  ASSERT_NE(old, nullptr);
  auto worker = validWorker();
  old->publish(old->context, &worker);
  ASSERT_NE(open(), 0u);
  auto *next = create(0, 11);
  ASSERT_NE(next, nullptr);
  next->publish(next->context, &worker);
  EXPECT_NE(old->captureEpoch, next->captureEpoch);
  EXPECT_NE(old->tokenId, next->tokenId);
  auto oldRows = drainCannLaunchReceipts(10);
  auto nextRows = drainCannLaunchReceipts(11);
  ASSERT_EQ(oldRows.size(), 1u);
  ASSERT_EQ(nextRows.size(), 1u);
  EXPECT_EQ(oldRows[0].captureEpoch, old->captureEpoch);
  EXPECT_EQ(nextRows[0].captureEpoch, next->captureEpoch);
  EXPECT_TRUE(drainCannLaunchReceipts(12).empty());
}

TEST_F(CannLaunchReceiptTest, QueuedRetainOutlivesCapsuleOwner) {
  auto *sink = create();
  ASSERT_NE(sink, nullptr);
  sink->retain(sink->context);
  releaseOwner(sink);
  auto worker = validWorker();
  std::thread queued([&] { sink->publish(sink->context, &worker); });
  queued.join();
  EXPECT_EQ(row(sink).status, "collected");
  const auto token = sink->tokenId;
  endCannLaunchReceiptCapture(sink->captureEpoch,
                              "queued reference still live");
  drainCannLaunchReceipts(sink->sessionId);
  ASSERT_NE(open(),
            0u); // Attempt pruning while only registry + queued refs exist.
  auto late = validWorker(5);
  sink->publish(sink->context, &late);
  EXPECT_TRUE(row(sink).lateCallback);
  EXPECT_EQ(row(sink).worker.taskId, worker.taskId);
  sink->release(sink->context);
  ASSERT_NE(open(),
            0u); // Drained + final queued release now permits reclamation.
  const auto remaining = drainCannLaunchReceipts(0);
  EXPECT_TRUE(std::none_of(remaining.begin(), remaining.end(),
                           [&](const auto &r) { return r.tokenId == token; }));
}

TEST_F(CannLaunchReceiptTest, ConcurrentWorkersKeepDistinctTokensAndPayloads) {
  std::vector<CannLaunchReceiptSinkV1 *> sinks;
  for (uint32_t i = 0; i != 32; ++i) {
    sinks.push_back(create(i));
    ASSERT_NE(sinks.back(), nullptr);
  }
  std::vector<std::thread> threads;
  for (uint32_t i = 0; i != sinks.size(); ++i)
    threads.emplace_back([&, i] {
      auto worker = validWorker(i);
      worker.threadId += i;
      sinks[i]->publish(sinks[i]->context, &worker);
    });
  for (auto &thread : threads)
    thread.join();
  for (uint32_t i = 0; i != sinks.size(); ++i) {
    auto receipt = row(sinks[i]);
    EXPECT_EQ(receipt.status, "collected");
    EXPECT_EQ(receipt.scopeId, i);
    EXPECT_EQ(receipt.worker.taskId, i);
    EXPECT_EQ(receipt.worker.threadId, 19u + i);
  }
}

TEST_F(CannLaunchReceiptTest, ClosePublishRaceOnlyRetainsEligibleOrLateData) {
  std::atomic<bool> start{false};
  std::vector<std::thread> threads;
  std::vector<CannLaunchReceiptSinkV1 *> sinks;
  for (uint32_t i = 0; i != 32; ++i) {
    auto *sink = create(i);
    ASSERT_NE(sink, nullptr);
    sinks.push_back(sink);
    threads.emplace_back([&, sink, i] {
      while (!start.load(std::memory_order_acquire))
        std::this_thread::yield();
      auto worker = validWorker(i);
      sink->publish(sink->context, &worker);
    });
  }
  start.store(true, std::memory_order_release);
  endCannLaunchReceiptCapture(epochs.back(), "racing close");
  for (auto &thread : threads)
    thread.join();
  for (uint32_t i = 0; i != sinks.size(); ++i) {
    auto receipt = row(sinks[i]);
    EXPECT_TRUE(receipt.status == "collected" || receipt.lateCallback);
    EXPECT_LE(receipt.publishCount, 1u);
    if (receipt.publishCount)
      EXPECT_EQ(receipt.worker.taskId, i);
  }
}

// These calls validate the public seal storage/lifetime protocol. The paths and
// evidence are explicitly constructed unit data, not an SDK capture oracle.
TEST_F(CannLaunchReceiptTest, SealRequiresClosedEpochAndIsImmutable) {
  auto *sink = create();
  ASSERT_NE(sink, nullptr);
  auto worker = validWorker();
  sink->publish(sink->context, &worker);
  sealCannLaunchReceiptCapture(sink->captureEpoch, "unit-active", "unit-only",
                               "{}");
  EXPECT_EQ(row(sink).sdkCaptureBindingStatus, "unsealed");
  endCannLaunchReceiptCapture(sink->captureEpoch, "unit close");
  sealCannLaunchReceiptCapture(sink->captureEpoch, "unit-closed", "unit-only",
                               "{\"unit\":true}");
  auto sealed = row(sink);
  EXPECT_EQ(sealed.sdkCapturePath, "unit-closed");
  EXPECT_EQ(sealed.sdkCaptureBindingStatus, "unit-only");
  EXPECT_EQ(sealed.sdkCaptureBindingEvidence, "{\"unit\":true}");
  EXPECT_EQ(sealed.worker.taskId, worker.taskId);
  sealCannLaunchReceiptCapture(sink->captureEpoch, "replacement", "replacement",
                               "{}");
  EXPECT_EQ(row(sink).sdkCapturePath, sealed.sdkCapturePath);
  EXPECT_EQ(row(sink).sdkCaptureBindingEvidence,
            sealed.sdkCaptureBindingEvidence);
}

TEST_F(CannLaunchReceiptTest, SealDoesNotCrossEpochOrSessionMembership) {
  auto *old = create(0, 30);
  ASSERT_NE(old, nullptr);
  const auto oldEpoch = old->captureEpoch;
  ASSERT_NE(open(), 0u);
  auto *next = create(0, 31);
  ASSERT_NE(next, nullptr);
  sealCannLaunchReceiptCapture(oldEpoch, "unit-old", "unit-only", "{}");
  EXPECT_EQ(row(old).sdkCapturePath, "unit-old");
  EXPECT_EQ(row(next).sdkCaptureBindingStatus, "unsealed");
  EXPECT_EQ(row(next).sdkCapturePath, "");
  sealCannLaunchReceiptCapture(~uint64_t{0}, "unknown", "unit-only", "{}");
  EXPECT_EQ(row(next).sdkCapturePath, "");
}

TEST_F(CannLaunchReceiptTest, FailedSealRemainsUncertifiedAndCannotBeReplaced) {
  auto *sink = create();
  ASSERT_NE(sink, nullptr);
  endCannLaunchReceiptCapture(sink->captureEpoch, "unit close");
  sealCannLaunchReceiptCapture(sink->captureEpoch, "", "unit-missing", "{}");
  EXPECT_EQ(row(sink).sdkCapturePath, "");
  EXPECT_EQ(row(sink).sdkCaptureBindingStatus, "unit-missing");
  sealCannLaunchReceiptCapture(sink->captureEpoch, "later", "unit-only", "{}");
  EXPECT_EQ(row(sink).sdkCapturePath, "");
  EXPECT_EQ(row(sink).sdkCaptureBindingStatus, "unit-missing");
}

TEST_F(CannLaunchReceiptTest, BoundedEpochCapacityAndReferenceRecovery) {
  // One retained sink per epoch, at most 8192 small records; never allocate the
  // million-entry per-capture ceiling. No test-only capacity override is used.
  bool full = false;
  for (uint32_t i = 0; i != 8192; ++i) {
    if (!open()) {
      full = true;
      break;
    }
    ASSERT_NE(create(i, 41), nullptr);
  }
  ASSERT_TRUE(full) << "finite epoch registry bound was not observed";
  EXPECT_FALSE(cannLaunchReceiptCaptureActive());
  EXPECT_EQ(createCannLaunchReceiptSink(0, 41), nullptr);
  auto drained = drainCannLaunchReceipts(41);
  EXPECT_FALSE(drained.empty());
  for (auto *sink : owners)
    sink->release(sink->context);
  owners.clear();
  ASSERT_NE(open(), 0u);
  auto *recovered = create(0, 41);
  ASSERT_NE(recovered, nullptr);
  auto worker = validWorker();
  recovered->publish(recovered->context, &worker);
  EXPECT_EQ(row(recovered).status, "collected");
}

} // namespace
} // namespace proton
