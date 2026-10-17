#include "Conversion/ProtonGPUToLLVM/PatternProtonGPUOpToLLVM.h"
#include "Conversion/ProtonGPUToLLVM/TargetInfoBase.h"
#include "Conversion/ProtonGPUToLLVM/Utility.h"
#include "Dialect/ProtonGPU/IR/Dialect.h"
#include "mlir/Conversion/LLVMCommon/Pattern.h"
#include "mlir/Conversion/LLVMCommon/TypeConverter.h"
#include "mlir/Dialect/ControlFlow/IR/ControlFlowOps.h"
#include "mlir/IR/PatternMatch.h"
#include "third_party/nvidia/include/TritonNVIDIAGPUToLLVM/PTXAsmFormat.h"
#include "triton/Conversion/TritonGPUToLLVM/Utility.h"

namespace mlir::triton {
namespace proton::gpu {

namespace {

struct CensusStoreOpConversion
    : public ConvertOpToLLVMPattern<proton::gpu::CensusStoreOp> {
  using ConvertOpToLLVMPattern<
      proton::gpu::CensusStoreOp>::ConvertOpToLLVMPattern;
  LogicalResult
  matchAndRewrite(proton::gpu::CensusStoreOp op, OpAdaptor adaptor,
                  ConversionPatternRewriter &rewriter) const override {
    auto loc = op.getLoc();
    auto b = TritonLLVMOpBuilder(loc, rewriter);
    // One physical lane owns each site cell for its declared logical observer.
    // No other program can address this program's per-CTA scratch segment.
    auto threads = op->getAttrOfType<IntegerAttr>("census_observer_threads");
    auto actorOffset =
        op->getAttrOfType<IntegerAttr>("census_actor_word_offset");
    int64_t observerThreads = threads ? threads.getInt() : 0;
    int64_t base = actorOffset ? actorOffset.getInt() : 0;
    Value thread = getRawThreadId(rewriter, loc);
    // A contiguous partition interval of P threads contains exactly one
    // multiple of P, independent of its assigned physical warp start. This is a
    // logical partition observer, not a claim that its physical warp ID equals
    // actor ID.
    Value writer = b.icmp_eq(
        observerThreads ? b.urem(thread, b.i32_val(observerThreads)) : thread,
        b.i32_val(0));
    Block *before = op->getBlock();
    Block *body = rewriter.splitBlock(before, op->getIterator());
    Block *after = rewriter.splitBlock(body, op->getIterator());
    rewriter.setInsertionPointToEnd(before);
    rewriter.create<cf::CondBranchOp>(loc, writer, body, after);
    rewriter.setInsertionPointToStart(body);
    auto ptrTy = adaptor.getScratchPtr().getType();
    Value countPtr = b.gep(ptrTy, i32_ty, adaptor.getScratchPtr(),
                           b.i32_val(base + op.getScopeId() * 2));
    Value flagsPtr = b.gep(ptrTy, i32_ty, adaptor.getScratchPtr(),
                           b.i32_val(base + op.getScopeId() * 2 + 1));
    Value count = b.load(i32_ty, countPtr);
    Value flags = b.load(i32_ty, flagsPtr);
    Value full = b.icmp_eq(count, b.i32_val(-1));
    Value next = b.select(full, count, b.add(count, b.i32_val(1)));
    Value newFlags = b.or_(
        flags, b.or_(b.i32_val(1), b.select(full, b.i32_val(2), b.i32_val(0))));
    b.store(next, countPtr);
    b.store(newFlags, flagsPtr);
    rewriter.create<cf::BranchOp>(loc, after);
    rewriter.eraseOp(op);
    return success();
  }
};

struct ReadCounterOpConversion
    : public ConvertOpToLLVMPattern<mlir::triton::proton::gpu::ReadCounterOp> {
  explicit ReadCounterOpConversion(
      LLVMTypeConverter &typeConverter,
      const proton::gpu::TargetInfoBase &targetInfo, PatternBenefit benefit)
      : mlir::ConvertOpToLLVMPattern<mlir::triton::proton::gpu::ReadCounterOp>(
            typeConverter, benefit),
        targetInfo(targetInfo) {}

  LogicalResult
  matchAndRewrite(mlir::triton::proton::gpu::ReadCounterOp op,
                  OpAdaptor adaptor,
                  ConversionPatternRewriter &rewriter) const override {
    bool isClock64 = false;
    auto intType = mlir::cast<IntegerType>(op.getResult().getType());
    isClock64 = intType.getWidth() == 64;
    auto module = op->getParentOfType<ModuleOp>();
    if (auto attr = module->getAttr("proton.timeline_timer")) {
      auto timer = dyn_cast<StringAttr>(attr);
      auto version = module->getAttrOfType<IntegerAttr>(
          "proton.timeline_timer_version");
      auto recordVersion = module->getAttrOfType<IntegerAttr>(
          "proton.timeline_record_version");
      if (module->hasAttr("proton.timeline_record_version") &&
          (!recordVersion || recordVersion.getInt() != 2)) {
        op.emitError("Unsupported timeline record version");
        return failure();
      }
      if (!timer || !version || version.getInt() != 1 || !isClock64 ||
          !targetInfo.supportsTimelineTimer(timer.getValue())) {
        op.emitError("Unsupported timeline getter/version or non-64-bit read");
        return failure();
      }
    }
    Value clock = targetInfo.clock(rewriter, op.getLoc(), isClock64);
    rewriter.replaceOp(op, clock);
    return success();
  }

protected:
  const proton::gpu::TargetInfoBase &targetInfo;
};

struct FinalizeOpConversion
    : public ConvertOpToLLVMPattern<mlir::triton::proton::gpu::FinalizeOp> {
  explicit FinalizeOpConversion(LLVMTypeConverter &typeConverter,
                                const proton::gpu::TargetInfoBase &targetInfo,
                                PatternBenefit benefit)
      : mlir::ConvertOpToLLVMPattern<mlir::triton::proton::gpu::FinalizeOp>(
            typeConverter, benefit),
        targetInfo(targetInfo) {}

  LogicalResult
  matchAndRewrite(mlir::triton::proton::gpu::FinalizeOp op, OpAdaptor adaptor,
                  ConversionPatternRewriter &rewriter) const override {
    auto loc = op.getLoc();
    auto segmentObj =
        LLVM::SegmentObject::fromStruct(loc, adaptor.getSegment(), rewriter);
    Value scratchPtr = adaptor.getScratchPtr();

    auto mod = op.getOperation()->getParentOfType<ModuleOp>();
    auto b = TritonLLVMOpBuilder(loc, rewriter);
    const int bytesPerEntry = proton::gpu::getBytesPerClockEntry(mod);
    const int wordsPerEntry = bytesPerEntry / 4; // 1 word = 4 bytes

    int numWarps = getTotalNumWarps(mod);

    Value threadId = getRawThreadId(rewriter, loc);
    Value warpId = b.udiv(
        threadId,
        b.i32_val(triton::gpu::TritonGPUDialect::getThreadsPerWarp(mod)));
    Value isFirstThread = b.icmp_eq(threadId, b.i32_val(0));
    const int bufferSizeInWords = op.getSegment().getType().getNBytes() / 4;
    const int circularHeaderWordSize = proton::gpu::getCircularHeaderSize() / 4;

    // Header: preamble (1 word), threadblock id (1 word), SM id (1 word),
    // buffer size (1 word)

    // Circular strategy memory layout (total: allocprofileScratchSize bytes)
    //  +-----------------------------------------------+
    //  | header (circularHeaderSize bytes)             |
    //  +-----------------------------------------------+
    //  | contexts for all warps (4 bytes x numWarps)   |
    //  +-----------------------------------------------+
    //  | profiled data (allocBufferSize bytes)         |
    //  +-----------------------------------------------+
    const int metadataWordSize = circularHeaderWordSize + numWarps;
    const int scratchWordSize = metadataWordSize + bufferSizeInWords;

    auto &tritonTargetInfo = targetInfo.getTritonTargetInfo();

    Value hwid = targetInfo.processorId(rewriter, loc);

    auto scratchPtrTy = mlir::cast<LLVM::LLVMPointerType>(scratchPtr.getType());

    // Add the `warp_index` section.
    Value warpIndexOffset = b.add(warpId, b.i32_val(circularHeaderWordSize));
    Value gmemWarpIndexPtr =
        b.gep(scratchPtrTy, i32_ty, scratchPtr, warpIndexOffset);
    Value index = b.load(i32_ty, segmentObj.indexPtr);
    if (bytesPerEntry == 16) {
      // A single lane publishes each observer counter. Other lanes have private
      // counters and must not race this global metadata store.
      Value lane = b.urem(threadId, b.i32_val(
          triton::gpu::TritonGPUDialect::getThreadsPerWarp(mod)));
      Value publish = b.and_(b.icmp_eq(lane, b.i32_val(0)),
                            getProgramCollectionPredicate(mod, loc, rewriter));
      Block *before = op->getBlock();
      Block *after = rewriter.splitBlock(before, op->getIterator());
      Block *write = rewriter.createBlock(after);
      rewriter.setInsertionPointToEnd(before);
      rewriter.create<cf::CondBranchOp>(loc, publish, write, after);
      rewriter.setInsertionPointToStart(write);
      b.store(index, gmemWarpIndexPtr);
      rewriter.create<cf::BranchOp>(loc, after);
      rewriter.setInsertionPoint(op);
      isFirstThread = b.and_(isFirstThread,
                            getProgramCollectionPredicate(mod, loc, rewriter));
    } else {
      b.store(index, gmemWarpIndexPtr);
    }

    Block *prevBlock = op->getBlock();
    // Add the 'if' block.
    Block *ifBlock = rewriter.splitBlock(prevBlock, op->getIterator());
    rewriter.setInsertionPointToStart(ifBlock);

    auto bufferBaseType = segmentObj.base.getType();
    auto copyWord = [&](Value bufOffset, Value gmemOffset, Attribute memSpace) {
      // Load the value from buffer
      Value ptr = b.gep(bufferBaseType, i32_ty, segmentObj.base, bufOffset);
      Value load;
      if (mlir::isa<triton::gpu::SharedMemorySpaceAttr>(memSpace)) {
        load = tritonTargetInfo.loadShared(rewriter, loc, ptr, i32_ty,
                                           b.true_val());
      } else {
        llvm::report_fatal_error(
            "unsupported memory space buffer in finalize copy");
      }

      // Store the value to global memory
      Value gmemPtr = b.gep(scratchPtrTy, i32_ty, scratchPtr, gmemOffset);
      b.store(load, gmemPtr);
    };
    // Write back 'preamble'.
    Value preamble = b.i32_val(bytesPerEntry == 16 ? 0x46505432 : 0xdeadbeef);
    Value gmemPreambleOffset = b.i32_val(0);
    Value gmemPreamblePtr =
        b.gep(scratchPtrTy, i32_ty, scratchPtr, gmemPreambleOffset);
    b.store(preamble, gmemPreamblePtr);

    // Write back 'program id'.
    Value gmemPidOffset = b.i32_val(1);
    Value gmemPidPtr = b.gep(scratchPtrTy, i32_ty, scratchPtr, gmemPidOffset);
    Value pid = getLinearCTAId(loc, rewriter);
    b.store(pid, gmemPidPtr);

    // Write back 'hw id'.
    Value gmemHwidOffset = b.i32_val(2);
    Value gmemHwidPtr = b.gep(scratchPtrTy, i32_ty, scratchPtr, gmemHwidOffset);
    b.store(hwid, gmemHwidPtr);

    // Write back 'buffer size in byte'.
    Value gmemBufSizeOffset = b.i32_val(3);
    Value gmemBufSizePtr =
        b.gep(scratchPtrTy, i32_ty, scratchPtr, gmemBufSizeOffset);
    b.store(b.i32_val(bufferSizeInWords * 4), gmemBufSizePtr);

    // Add the 'else' block and the condition.
    Block *thenBlock = rewriter.splitBlock(ifBlock, op->getIterator());
    rewriter.setInsertionPointToEnd(prevBlock);
    rewriter.create<cf::CondBranchOp>(loc, isFirstThread, ifBlock, thenBlock);

    // Each warp master copies its own retained prefix. Its local counter is
    // authoritative, so no cross-warp synchronization or global counter reads
    // are needed. Once a segment wraps, the entire ring remains live.
    rewriter.setInsertionPoint(prevBlock->getTerminator());
    auto selectedIds = op.getSegment().getType().getSelectIds();
    const int segmentWords =
        bufferSizeInWords /
        (selectedIds.empty() ? numWarps : selectedIds.size());
    Value rawThreadId = getRawThreadId(rewriter, loc);
    Value laneId = b.urem(
        rawThreadId,
        b.i32_val(triton::gpu::TritonGPUDialect::getThreadsPerWarp(mod)));
    Value retainedWords = b.select(b.icmp_ult(index, b.i32_val(segmentWords)),
                                   index, b.i32_val(segmentWords));
    const bool warpSpecialized = numWarps != triton::gpu::lookupNumWarps(mod);
    Value copyBase = segmentObj.segmentBase;
    if (warpSpecialized) {
      // Worker warps save their counters and return before finalization in
      // the master partition. Preserve the inherited whole-buffer copy here;
      // a master lane's private index cannot describe worker-written prefixes.
      retainedWords = b.i32_val(bufferSizeInWords);
      copyBase = b.i32_val(0);
    }
    Value shouldCopy = b.and_(b.icmp_eq(laneId, b.i32_val(0)),
                              b.icmp_sge(segmentObj.segmentBase, b.i32_val(0)));
    shouldCopy = b.and_(shouldCopy, b.icmp_ugt(retainedWords, b.i32_val(0)));
    if (warpSpecialized)
      shouldCopy = isFirstThread;
    if (bytesPerEntry == 16)
      shouldCopy = b.and_(shouldCopy,
                         getProgramCollectionPredicate(mod, loc, rewriter));

    Block *copyDispatch = rewriter.createBlock(op->getParentRegion(),
                                               Region::iterator(thenBlock));
    rewriter.setInsertionPointToEnd(ifBlock);
    rewriter.create<cf::BranchOp>(loc, copyDispatch);
    // Both the metadata writer and all remaining threads reach this block.
    rewriter.setInsertionPointToEnd(prevBlock);
    prevBlock->getTerminator()->setSuccessor(copyDispatch, 1);
    rewriter.setInsertionPointToStart(copyDispatch);
    Block *writeBackBlock = rewriter.createBlock(
        op->getParentRegion(), Region::iterator(thenBlock), {i32_ty}, {loc});
    rewriter.setInsertionPointToEnd(copyDispatch);
    rewriter.create<cf::CondBranchOp>(loc, shouldCopy, writeBackBlock,
                                      b.i32_val(0), thenBlock,
                                      ArrayRef<Value>());
    rewriter.setInsertionPointToStart(writeBackBlock);
    BlockArgument idx = writeBackBlock->getArgument(0);
    Value bufTagOffset = b.add(copyBase, idx);
    Value gmemWbTagOffset = b.add(b.i32_val(metadataWordSize), bufTagOffset);
    auto memSpace = op.getSegment().getType().getMemorySpace();
    for (int word = 0; word < wordsPerEntry; ++word)
      copyWord(b.add(bufTagOffset, b.i32_val(word)),
               b.add(gmemWbTagOffset, b.i32_val(word)), memSpace);
    Value updatedIdx = b.add(idx, b.i32_val(wordsPerEntry));
    Value pred = b.icmp_ult(updatedIdx, retainedWords);
    rewriter.create<cf::CondBranchOp>(loc, pred, writeBackBlock, updatedIdx,
                                      thenBlock, ArrayRef<Value>());

    rewriter.eraseOp(op);
    return success();
  }

protected:
  const proton::gpu::TargetInfoBase &targetInfo;
};

struct SegmentAllocOpConversion
    : public ConvertOpToLLVMPattern<mlir::triton::proton::gpu::SegmentAllocOp> {
  explicit SegmentAllocOpConversion(
      LLVMTypeConverter &typeConverter,
      const proton::gpu::TargetInfoBase &targetInfo, PatternBenefit benefit)
      : mlir::ConvertOpToLLVMPattern<mlir::triton::proton::gpu::SegmentAllocOp>(
            typeConverter, benefit),
        targetInfo(targetInfo) {}

  LogicalResult
  matchAndRewrite(mlir::triton::proton::gpu::SegmentAllocOp op,
                  OpAdaptor adaptor,
                  ConversionPatternRewriter &rewriter) const override {

    auto mod = op.getOperation()->getParentOfType<ModuleOp>();
    auto loc = op.getLoc();
    auto b = TritonLLVMOpBuilder(loc, rewriter);

    int numWarps = getTotalNumWarps(mod);

    auto segmentType = op.getResult().getType();
    auto granularity = segmentType.getGranularity();
    auto selectIds = segmentType.getSelectIds();
    bool isAllIds = selectIds.empty() ? true : false;

    if (granularity != proton::gpu::Granularity::WARP) {
      mlir::emitError(loc, "granularity must be warp for now");
      return failure();
    }

    Value curThreadId = getRawThreadId(rewriter, loc);

    Value threadsPerWarp =
        b.i32_val(triton::gpu::TritonGPUDialect::getThreadsPerWarp(mod));
    Value curWarpId = b.udiv(curThreadId, threadsPerWarp);
    const int bufferSizeInBytes = op.getSegment().getType().getNBytes();

    // Specialize the segment base address calculation might bring a few cycles
    // saving per record measurement overhead.
    Value segmentBase;
    if (isAllIds) {
      if (granularity == proton::gpu::Granularity::WARP)
        segmentBase =
            allWarpSegmentAlloc(b, curWarpId, numWarps, bufferSizeInBytes);
      else
        llvm::report_fatal_error(
            "segment address specialization not implemented yet");
    } else {
      segmentBase =
          defaultSegmentAlloc(b, curWarpId, selectIds, bufferSizeInBytes);
    }

    segmentBase = b.select(getProgramCollectionPredicate(mod, loc, rewriter),
                           segmentBase, b.i32_val(-1));
    Value buffer = adaptor.getBuffer();
    auto bufferBaseTy =
        mlir::cast<LLVM::LLVMStructType>(buffer.getType()).getBody()[0];
    Value bufferBase = b.extract_val(bufferBaseTy, buffer, 0);
    auto indexPtrTy =
        ptr_ty(rewriter.getContext(), targetInfo.getIndexPtrAddrSpace());
    auto indexPtr = rewriter.create<LLVM::AllocaOp>(
        loc, indexPtrTy, i32_ty, b.i32_val(1), /*alignment=*/0);
    b.store(b.i32_val(0), indexPtr);

    auto segmentObj = LLVM::SegmentObject(bufferBase, segmentBase, indexPtr);
    auto llvmStruct = segmentObj.getStruct(loc, rewriter);
    rewriter.replaceOp(op, llvmStruct);
    return success();
  }

private:
  Value defaultSegmentAlloc(TritonLLVMOpBuilder &b, Value curWarpId,
                            llvm::ArrayRef<int> selectedIds,
                            int bufferSize) const {
    const int segmentWordSize = bufferSize / selectedIds.size() / 4;
    int warpSegmentAlloc = 0;
    Value segmentAlloc = b.i32_val(-1);
    for (int warpId : selectedIds) {
      segmentAlloc = b.select(b.icmp_eq(curWarpId, b.i32_val(warpId)),
                              b.i32_val(warpSegmentAlloc), segmentAlloc);
      warpSegmentAlloc += segmentWordSize;
    }
    return segmentAlloc;
  }

  Value allWarpSegmentAlloc(TritonLLVMOpBuilder &b, Value curWarpId,
                            int numWarps, int bufferSize) const {
    const int segmentWordSize = bufferSize / numWarps / 4;
    return b.mul(curWarpId, b.i32_val(segmentWordSize));
  }

protected:
  const proton::gpu::TargetInfoBase &targetInfo;
};

struct GlobalScratchAllocOpConversion
    : public ConvertOpToLLVMPattern<proton::gpu::GlobalScratchAllocOp> {
  explicit GlobalScratchAllocOpConversion(
      LLVMTypeConverter &typeConverter,
      const proton::gpu::TargetInfoBase &targetInfo, PatternBenefit benefit)
      : mlir::ConvertOpToLLVMPattern<proton::gpu::GlobalScratchAllocOp>(
            typeConverter, benefit),
        targetInfo(targetInfo) {}

  LogicalResult
  matchAndRewrite(proton::gpu::GlobalScratchAllocOp op, OpAdaptor adaptor,
                  ConversionPatternRewriter &rewriter) const override {
    auto loc = op.getLoc();
    auto b = TritonLLVMOpBuilder(loc, rewriter);
    auto *ctx = rewriter.getContext();
    auto &tritonTargetInfo = targetInfo.getTritonTargetInfo();

    auto funcOp = op->getParentOfType<LLVM::LLVMFuncOp>();
    if (!funcOp) {
      return failure();
    }

    ModuleOp mod = funcOp.getOperation()->getParentOfType<ModuleOp>();
    auto ptrTy = mlir::LLVM::LLVMPointerType::get(ctx, 1);
    assert(op->hasAttr("offset"));
    size_t offset =
        cast<IntegerAttr>(op->getAttr("offset")).getValue().getZExtValue();

    Value allocOffset = b.i32_val(offset);

    // See NOTE: [Additional Function Arguments]
    if (!LLVM::isKernel(funcOp)) {
      // Base for this function
      auto gmemBase = funcOp.getArgument(funcOp.getNumArguments() +
                                         kProfileScratchBufferOffset);

      Value ptr = b.gep(ptrTy, i8_ty, gmemBase, allocOffset);
      rewriter.replaceOp(op, ptr);
      return success();
    }

    // Base for entire kernel
    auto gmemBase = funcOp.getArgument(funcOp.getNumArguments() +
                                       kProfileScratchBufferOffset);
    auto allocSizeAttr = mod.getOperation()->getAttrOfType<mlir::IntegerAttr>(
        "ttg.profile_scratch_memory_size");
    assert(allocSizeAttr);

    Value linearId = getProgramCollectionSlot(mod, loc, rewriter);

    auto allocSize = allocSizeAttr.getValue().getZExtValue();
    Value gmemOffset =
        b.add(allocOffset, b.mul(linearId, b.i32_val(allocSize)));

    auto ptr = b.gep(ptrTy, i8_ty, gmemBase, gmemOffset);

    rewriter.replaceOp(op, ptr);
    return success();
  }

protected:
  const proton::gpu::TargetInfoBase &targetInfo;
};

struct InitCtxOpConversion
    : public ConvertOpToLLVMPattern<mlir::triton::proton::gpu::InitCtxOp> {
  explicit InitCtxOpConversion(LLVMTypeConverter &typeConverter,
                               const proton::gpu::TargetInfoBase &targetInfo,
                               PatternBenefit benefit)
      : mlir::ConvertOpToLLVMPattern<mlir::triton::proton::gpu::InitCtxOp>(
            typeConverter, benefit),
        targetInfo(targetInfo) {}

  LogicalResult
  matchAndRewrite(mlir::triton::proton::gpu::InitCtxOp op, OpAdaptor adaptor,
                  ConversionPatternRewriter &rewriter) const override {
    auto loc = op.getLoc();
    Value scratchPtr = adaptor.getScratchPtr();
    auto scratchPtrTy = mlir::cast<LLVM::LLVMPointerType>(scratchPtr.getType());

    auto mod = op.getOperation()->getParentOfType<ModuleOp>();
    auto b = TritonLLVMOpBuilder(loc, rewriter);

    int numWarps = getTotalNumWarps(mod);

    // InitCtxOp can only be called in the master warps, so using `getThreadId`
    // is fine.
    Value threadId = getThreadId(rewriter, loc);
    Value isFirstThread = b.icmp_eq(threadId, b.i32_val(0));
    if (mod->hasAttr("proton.timeline_storage_version"))
      isFirstThread = b.and_(
          isFirstThread, getProgramCollectionPredicate(mod, loc, rewriter));
    const int circularHeaderWordSize = proton::gpu::getCircularHeaderSize() / 4;

    Block *prevBlock = op->getBlock();

    // Add the 'if' block.
    Block *ifBlock = rewriter.splitBlock(prevBlock, op->getIterator());
    rewriter.setInsertionPointToStart(ifBlock);

    // Initialize the `warp_index` section.
    for (int warpId = 0; warpId < numWarps; warpId++) {
      Value warpIndexOffset = b.i32_val(warpId + circularHeaderWordSize);
      Value gmemWarpIndexPtr =
          b.gep(scratchPtrTy, i32_ty, scratchPtr, warpIndexOffset);
      b.store(b.i32_val(0), gmemWarpIndexPtr);
    }

    // Add the 'else' block and the condition.
    Block *thenBlock = rewriter.splitBlock(ifBlock, op->getIterator());
    rewriter.setInsertionPointToEnd(prevBlock);
    rewriter.create<cf::CondBranchOp>(loc, isFirstThread, ifBlock, thenBlock);
    rewriter.setInsertionPointToEnd(ifBlock);
    rewriter.create<cf::BranchOp>(loc, thenBlock);

    rewriter.eraseOp(op);
    return success();
  }

protected:
  const proton::gpu::TargetInfoBase &targetInfo;
};

struct RestoreCtxOpConversion
    : public ConvertOpToLLVMPattern<mlir::triton::proton::gpu::RestoreCtxOp> {
  explicit RestoreCtxOpConversion(LLVMTypeConverter &typeConverter,
                                  const proton::gpu::TargetInfoBase &targetInfo,
                                  PatternBenefit benefit)
      : mlir::ConvertOpToLLVMPattern<mlir::triton::proton::gpu::RestoreCtxOp>(
            typeConverter, benefit),
        targetInfo(targetInfo) {}

  LogicalResult
  matchAndRewrite(mlir::triton::proton::gpu::RestoreCtxOp op, OpAdaptor adaptor,
                  ConversionPatternRewriter &rewriter) const override {
    auto loc = op.getLoc();
    auto segmentObj =
        LLVM::SegmentObject::fromStruct(loc, adaptor.getSegment(), rewriter);
    Value scratchPtr = adaptor.getScratchPtr();

    auto mod = op.getOperation()->getParentOfType<ModuleOp>();
    auto b = TritonLLVMOpBuilder(loc, rewriter);
    int numWarps = getTotalNumWarps(mod);

    // We need to use the absolute warp id in case warp specialization is used.
    Value threadId = getRawThreadId(rewriter, loc);

    Value warpId = b.udiv(
        threadId,
        b.i32_val(triton::gpu::TritonGPUDialect::getThreadsPerWarp(mod)));
    const int circularHeaderWordSize = proton::gpu::getCircularHeaderSize() / 4;

    auto scratchPtrTy = mlir::cast<LLVM::LLVMPointerType>(scratchPtr.getType());

    // Get the `warp_index` and store it into indexPtr.
    Value warpIndexOffset = b.add(warpId, b.i32_val(circularHeaderWordSize));
    Value gmemWarpIndexPtr =
        b.gep(scratchPtrTy, i32_ty, scratchPtr, warpIndexOffset);
    Block *selectedBlock = nullptr;
    Block *continuation = nullptr;
    if (mod->hasAttr("proton.timeline_storage_version")) {
      // An unselected CTA aliases a compact slot but owns none of its memory.
      // Initialize its private cursor without reading any global slot.
      b.store(b.i32_val(0), segmentObj.indexPtr);
      Value enabled = getProgramCollectionPredicate(mod, loc, rewriter);
      Block *before = op->getBlock();
      continuation = rewriter.splitBlock(before, op->getIterator());
      selectedBlock = rewriter.createBlock(continuation);
      rewriter.setInsertionPointToEnd(before);
      rewriter.create<cf::CondBranchOp>(loc, enabled, selectedBlock,
                                      continuation);
      rewriter.setInsertionPointToStart(selectedBlock);
    }
    Value index = b.load(i32_ty, gmemWarpIndexPtr);
    b.store(index, segmentObj.indexPtr);
    if (selectedBlock) {
      rewriter.create<cf::BranchOp>(loc, continuation);
      rewriter.setInsertionPoint(op);
    }

    rewriter.eraseOp(op);
    return success();
  }

protected:
  const proton::gpu::TargetInfoBase &targetInfo;
};

struct SaveCtxOpConversion
    : public ConvertOpToLLVMPattern<mlir::triton::proton::gpu::SaveCtxOp> {
  explicit SaveCtxOpConversion(LLVMTypeConverter &typeConverter,
                               const proton::gpu::TargetInfoBase &targetInfo,
                               PatternBenefit benefit)
      : mlir::ConvertOpToLLVMPattern<mlir::triton::proton::gpu::SaveCtxOp>(
            typeConverter, benefit),
        targetInfo(targetInfo) {}

  LogicalResult
  matchAndRewrite(mlir::triton::proton::gpu::SaveCtxOp op, OpAdaptor adaptor,
                  ConversionPatternRewriter &rewriter) const override {
    auto loc = op.getLoc();
    Value scratchPtr = adaptor.getScratchPtr();
    auto scratchPtrTy = mlir::cast<LLVM::LLVMPointerType>(scratchPtr.getType());
    auto segmentObj =
        LLVM::SegmentObject::fromStruct(loc, adaptor.getSegment(), rewriter);

    auto mod = op.getOperation()->getParentOfType<ModuleOp>();
    auto b = TritonLLVMOpBuilder(loc, rewriter);

    int numWarps = getTotalNumWarps(mod);

    int numLanes = triton::gpu::TritonGPUDialect::getThreadsPerWarp(mod);
    Value warpSize = b.i32_val(numLanes);

    // We need to use the absolute warp id in case warp specialization is used.
    Value threadId = getRawThreadId(rewriter, loc);

    Value warpId = b.udiv(threadId, warpSize);
    Value laneId = b.urem(threadId, warpSize);
    Value isWarpMaster = b.icmp_eq(laneId, b.i32_val(0));
    if (mod->hasAttr("proton.timeline_storage_version"))
      isWarpMaster = b.and_(
          isWarpMaster, getProgramCollectionPredicate(mod, loc, rewriter));
    const int circularHeaderWordSize = proton::gpu::getCircularHeaderSize() / 4;

    Block *prevBlock = op->getBlock();

    // Add the 'if' block.
    Block *ifBlock = rewriter.splitBlock(prevBlock, op->getIterator());
    rewriter.setInsertionPointToStart(ifBlock);

    // Update the `warp_index` section.
    Value warpIndexOffset = b.add(warpId, b.i32_val(circularHeaderWordSize));
    Value gmemWarpIndexPtr =
        b.gep(scratchPtrTy, i32_ty, scratchPtr, warpIndexOffset);
    Value index = b.load(i32_ty, segmentObj.indexPtr);
    b.store(index, gmemWarpIndexPtr);

    // Add the 'else' block and the condition.
    Block *thenBlock = rewriter.splitBlock(ifBlock, op->getIterator());
    rewriter.setInsertionPointToEnd(prevBlock);
    rewriter.create<cf::CondBranchOp>(loc, isWarpMaster, ifBlock, thenBlock);
    rewriter.setInsertionPointToEnd(ifBlock);
    rewriter.create<cf::BranchOp>(loc, thenBlock);

    rewriter.eraseOp(op);
    return success();
  }

protected:
  const proton::gpu::TargetInfoBase &targetInfo;
};

Type convertProtonGPUMemDescType(triton::gpu::MemDescType type,
                                 const TargetInfoBase &targetInfo) {
  auto ctx = type.getContext();
  // base ptr
  auto ptrType = LLVM::LLVMPointerType::get(
      ctx, targetInfo.getAddressSpace(type.getMemorySpace()));

  SmallVector<Type, 4> types;
  types.push_back(ptrType);
  auto rank = type.getRank();
  // offsets
  for (auto i = 0; i < rank; i++) {
    types.push_back(IntegerType::get(ctx, 32));
  }

  return LLVM::LLVMStructType::getLiteral(ctx, types);
}

Type convertProtonGPUSegmentType(SegmentType type,
                                 const TargetInfoBase &targetInfo) {
  auto memorySpace = targetInfo.getAddressSpace(type.getMemorySpace());
  return LLVM::SegmentObject::getStructType(type.getContext(), memorySpace,
                                            targetInfo.getIndexPtrAddrSpace());
}

} // namespace

void populateProtonGPUOpPatterns(LLVMTypeConverter &typeConverter,
                                 RewritePatternSet &patterns,
                                 const TargetInfoBase &targetInfo,
                                 PatternBenefit benefit) {
  patterns.add<CensusStoreOpConversion>(typeConverter, benefit);
  patterns.add<ReadCounterOpConversion>(typeConverter, targetInfo, benefit);
  patterns.add<FinalizeOpConversion>(typeConverter, targetInfo, benefit);
  patterns.add<SegmentAllocOpConversion>(typeConverter, targetInfo, benefit);
  patterns.add<GlobalScratchAllocOpConversion>(typeConverter, targetInfo,
                                               benefit);
  patterns.add<InitCtxOpConversion>(typeConverter, targetInfo, benefit);
  patterns.add<RestoreCtxOpConversion>(typeConverter, targetInfo, benefit);
  patterns.add<SaveCtxOpConversion>(typeConverter, targetInfo, benefit);
}

void populateTypeConversions(LLVMTypeConverter &typeConverter,
                             const TargetInfoBase &targetInfo) {
  typeConverter.addConversion(
      [&](triton::gpu::MemDescType type) -> std::optional<Type> {
        return convertProtonGPUMemDescType(type, targetInfo);
      });
  typeConverter.addConversion(
      [&](proton::gpu::SegmentType type) -> std::optional<Type> {
        return convertProtonGPUSegmentType(type, targetInfo);
      });
  typeConverter.addConversion(
      [&](triton::PointerType type) -> std::optional<Type> {
        auto ctx = type.getContext();
        return LLVM::LLVMPointerType::get(ctx, type.getAddressSpace());
      });
}

} // namespace proton::gpu
} // namespace mlir::triton
