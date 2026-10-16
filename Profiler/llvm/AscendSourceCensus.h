// Ascend-only census primitive. Coordinates and single-writer ownership must be
// established by the compiler before calling this helper. No timer is emitted.
#pragma once
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/Instructions.h"
#include "llvm/Support/ErrorHandling.h"
#include <cstdint>

namespace flagprism_ascend {
inline constexpr uint64_t kCensusHeaderBytes = 32;
inline constexpr uint64_t kCensusActorSlots = 3;
inline constexpr uint64_t kCensusReservedSites = 128;

inline void appendCensus(llvm::Instruction *position, llvm::Value *pointer,
                         llvm::Value *sourceProgram, llvm::Value *actor,
                         uint64_t column,
                         uint64_t columns = kCensusReservedSites,
                         unsigned physicalVersion = 1) {
  if (!columns || columns > kCensusReservedSites || column >= columns)
    llvm::report_fatal_error(
        "Ascend census column exceeds physical reserved stride");
  const uint64_t headerBytes = physicalVersion == 3 ? 64 : kCensusHeaderBytes;
  const uint64_t strideColumns = physicalVersion == 3 ? ((columns + 7) / 8) * 8 : columns;
  llvm::IRBuilder<> builder(position);
  auto *i32 = builder.getInt32Ty();
  auto *cell = builder.CreateAdd(
      builder.CreateMul(
          builder.CreateAdd(
              builder.CreateMul(sourceProgram,
                                builder.getInt64(kCensusActorSlots)),
              actor),
          builder.getInt64(strideColumns)),
      builder.getInt64(column));
  auto *word = builder.CreateAdd(builder.getInt64(headerBytes / 4),
                                 builder.CreateMul(cell, builder.getInt64(2)));
  auto *address = builder.CreateGEP(i32, pointer, word);
  auto *flagAddress = builder.CreateGEP(
      i32, pointer, builder.CreateAdd(word, builder.getInt64(1)));
  auto *oldCount = builder.CreateLoad(i32, address);
  oldCount->setVolatile(true);
  auto *oldFlags = builder.CreateLoad(i32, flagAddress);
  oldFlags->setVolatile(true);
  auto *saturated =
      builder.CreateICmpEQ(oldCount, builder.getInt32(UINT32_MAX));
  auto *count = builder.CreateSelect(
      saturated, oldCount, builder.CreateAdd(oldCount, builder.getInt32(1)));
  auto *flags = builder.CreateOr(
      oldFlags, builder.CreateSelect(saturated, builder.getInt32(3),
                                     builder.getInt32(1)));
  auto *countStore = builder.CreateStore(count, address);
  countStore->setVolatile(true);
  auto *flagStore = builder.CreateStore(flags, flagAddress);
  flagStore->setVolatile(true);
}
} // namespace flagprism_ascend
