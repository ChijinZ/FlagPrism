// Ascend timeline writer. Source coordinates/actor ownership are supplied by
// the real compiler carrier. This does not certify region bounds or clocks.
#pragma once
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/InlineAsm.h"
#include "llvm/Support/ErrorHandling.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"
#include <cstdint>

namespace flagprism_ascend {
inline constexpr uint64_t kTimelineMagic = UINT64_C(0x46505441314c4f47);
inline constexpr uint64_t kTimelineCommit = UINT64_C(0x46505441434f4d31);
inline constexpr uint64_t kTimelineMaxCount = (UINT64_C(1) << 63) - 1;
inline constexpr uint64_t kTimelineHeaderWords = 8;
inline constexpr uint64_t kTimelineRecordWords = 8;
inline constexpr uint64_t kTimelineActorSlots = 3;

inline llvm::Value *timelineTick(llvm::IRBuilder<> &builder) {
  auto *type = llvm::FunctionType::get(builder.getInt64Ty(), false);
  auto *clock = llvm::InlineAsm::get(type, "MOV $0, SYS_CNT", "=l", true);
  return builder.CreateCall(type, clock, {});
}

inline llvm::Value *timelineSelected(llvm::IRBuilder<> &b,
                                     llvm::Value *program,
                                     llvm::Value *lastProgram,
                                     llvm::Value *actor) {
  return b.CreateAnd(
      b.CreateOr(b.CreateICmpEQ(program, b.getInt64(0)),
                 b.CreateICmpEQ(program, lastProgram)),
      b.CreateICmpULT(actor, b.getInt64(kTimelineActorSlots)));
}

inline llvm::Value *timelineBase(llvm::IRBuilder<> &b, llvm::Value *program,
                                 llvm::Value *actor, uint64_t capacity) {
  if (!capacity || capacity > 16384)
    llvm::report_fatal_error("Ascend timeline pair capacity must be 1..16384");
  // Grid volume one uses only slot zero. Addressing is in actual i64 words;
  // both header and each pair occupy one independent 64-byte cache line.
  auto *slot = b.CreateSelect(b.CreateICmpEQ(program, b.getInt64(0)),
                              b.getInt64(0), b.getInt64(1));
  return b.CreateMul(
      b.CreateAdd(b.CreateMul(slot, b.getInt64(kTimelineActorSlots)), actor),
      b.getInt64(kTimelineHeaderWords + capacity * kTimelineRecordWords));
}

inline llvm::LoadInst *timelineLoad(llvm::IRBuilder<> &b, llvm::Value *pointer,
                                    llvm::Value *word) {
  auto *value = b.CreateLoad(b.getInt64Ty(), b.CreateGEP(b.getInt64Ty(), pointer, word));
  value->setVolatile(true);
  return value;
}

inline void timelineStore(llvm::IRBuilder<> &b, llvm::Value *pointer,
                           llvm::Value *word, llvm::Value *value) {
  auto *store = b.CreateStore(value, b.CreateGEP(b.getInt64Ty(), pointer, word));
  store->setVolatile(true);
}

inline llvm::Value *beginTimeline(llvm::Instruction *position,
                                  llvm::Value *pointer, llvm::Value *program,
                                  llvm::Value *lastProgram, llvm::Value *actor,
                                  llvm::Value *physicalBlock,
                                  uint64_t capacity) {
  llvm::IRBuilder<> b(position);
  auto *selected = timelineSelected(b, program, lastProgram, actor);
  auto *head = position->getParent();
  auto *thenTerminator = llvm::SplitBlockAndInsertIfThen(selected, position, false);
  llvm::IRBuilder<> selectedBuilder(thenTerminator);
  auto *base = timelineBase(selectedBuilder, program, actor, capacity);
  auto word = [&](uint64_t offset) {
    return selectedBuilder.CreateAdd(base, selectedBuilder.getInt64(offset));
  };
  auto *flags = timelineLoad(selectedBuilder, pointer, word(7));
  timelineStore(selectedBuilder, pointer, word(4), program);
  timelineStore(selectedBuilder, pointer, word(5), actor);
  timelineStore(selectedBuilder, pointer, word(6), physicalBlock);
  timelineStore(selectedBuilder, pointer, word(7),
                selectedBuilder.CreateOr(flags, selectedBuilder.getInt64(1)));
  timelineStore(selectedBuilder, pointer, word(0), selectedBuilder.getInt64(kTimelineMagic));
  auto *tick = timelineTick(selectedBuilder);
  auto *tail = position->getParent();
  auto *phi = llvm::PHINode::Create(b.getInt64Ty(), 2, "timeline.start", &*tail->begin());
  phi->addIncoming(b.getInt64(0), head);
  phi->addIncoming(tick, thenTerminator->getParent());
  return phi;
}

inline void endTimeline(llvm::Instruction *position, llvm::Value *pointer,
                         llvm::Value *program, llvm::Value *lastProgram,
                         llvm::Value *actor, llvm::Value *physicalBlock,
                         llvm::Value *start, uint64_t capacity, uint32_t site,
                         uint32_t semantic) {
  llvm::IRBuilder<> b(position);
  auto *selected = timelineSelected(b, program, lastProgram, actor);
  auto *selectedTerminator = llvm::SplitBlockAndInsertIfThen(selected, position, false);
  llvm::IRBuilder<> s(selectedTerminator);
  auto *end = timelineTick(s);
  auto *base = timelineBase(s, program, actor, capacity);
  auto word = [&](uint64_t offset) { return s.CreateAdd(base, s.getInt64(offset)); };
  auto *attempt = timelineLoad(s, pointer, word(2));
  auto *saturated = s.CreateICmpEQ(attempt, s.getInt64(kTimelineMaxCount));
  timelineStore(s, pointer, word(2), s.CreateSelect(
      saturated, attempt, s.CreateAdd(attempt, s.getInt64(1))));
  auto *flags = timelineLoad(s, pointer, word(7));
  timelineStore(s, pointer, word(7), s.CreateOr(flags,
      s.CreateSelect(saturated, s.getInt64(2), s.getInt64(0))));
  auto *cursor = timelineLoad(s, pointer, word(1));
  llvm::Instruction *successTerminator = nullptr, *dropTerminator = nullptr;
  llvm::SplitBlockAndInsertIfThenElse(s.CreateICmpULT(cursor, s.getInt64(capacity)),
      selectedTerminator, &successTerminator, &dropTerminator);
  llvm::IRBuilder<> success(successTerminator);
  auto *offset = success.CreateAdd(base, success.CreateAdd(
      success.getInt64(kTimelineHeaderWords),
      success.CreateMul(cursor, success.getInt64(kTimelineRecordWords))));
  const uint64_t descriptor = site | (uint64_t(semantic) << 32);
  auto *tag = success.CreateXor(success.getInt64(kTimelineCommit ^ descriptor), attempt);
  tag = success.CreateXor(tag, program);
  tag = success.CreateXor(tag, actor);
  tag = success.CreateXor(tag, physicalBlock);
  llvm::Value *values[] = {success.getInt64(descriptor), attempt, start, end,
                           program, actor, physicalBlock, tag};
  for (uint64_t index = 0; index < kTimelineRecordWords; ++index)
    timelineStore(success, pointer,
                  success.CreateAdd(offset, success.getInt64(index)), values[index]);
  // Readers wait for actual kernel/transfer completion; no new device barrier
  // or cross-actor shared header is inserted by this writer.
  timelineStore(success, pointer, success.CreateAdd(base, success.getInt64(1)),
                success.CreateAdd(cursor, success.getInt64(1)));
  llvm::IRBuilder<> drop(dropTerminator);
  auto *dropAddress = drop.CreateAdd(base, drop.getInt64(3));
  auto *oldDrop = timelineLoad(drop, pointer, dropAddress);
  timelineStore(drop, pointer, dropAddress, drop.CreateSelect(
      drop.CreateICmpEQ(oldDrop, drop.getInt64(kTimelineMaxCount)), oldDrop,
      drop.CreateAdd(oldDrop, drop.getInt64(1))));
  auto *oldFlags = timelineLoad(drop, pointer, drop.CreateAdd(base, drop.getInt64(7)));
  timelineStore(drop, pointer, drop.CreateAdd(base, drop.getInt64(7)),
                drop.CreateOr(oldFlags, drop.getInt64(4)));
}
} // namespace flagprism_ascend
