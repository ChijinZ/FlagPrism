#include "Conversion/ProtonGPUToLLVM/Utility.h"
#include "triton/Conversion/TritonGPUToLLVM/Utility.h"

namespace mlir {

Value getRawThreadId(OpBuilder &rewriter, Location loc) {
  Value tid =
      rewriter.create<::mlir::gpu::ThreadIdOp>(loc, ::mlir::gpu::Dimension::x);
  Value threadId = rewriter.create<arith::IndexCastOp>(loc, i32_ty, tid);
  return threadId;
}

namespace LLVM {

LLVMStructType SegmentObject::getStructType(MLIRContext *ctx, int memorySpace,
                                            int indexPtrAddrSpace) {
  SmallVector<Type, 4> types;
  // ------------
  // Memory descriptor
  // ------------
  auto ptrType = LLVM::LLVMPointerType::get(ctx, memorySpace);
  types.push_back(ptrType);
  // ------------
  // Segment base
  // ------------
  auto SegmentAllocType = IntegerType::get(ctx, 32);
  types.push_back(SegmentAllocType);
  // ------------
  // Index ptr
  // ------------
  auto indexPtrType = LLVM::LLVMPointerType::get(ctx, indexPtrAddrSpace);
  types.push_back(indexPtrType);
  return LLVM::LLVMStructType::getLiteral(ctx, types);
}

Value SegmentObject::getStruct(Location loc,
                               ConversionPatternRewriter &rewriter) {
  auto b = TritonLLVMOpBuilder(loc, rewriter);
  int memorySpace =
      mlir::cast<LLVM::LLVMPointerType>(base.getType()).getAddressSpace();
  int indexPtrAddrSpace =
      mlir::cast<LLVM::LLVMPointerType>(indexPtr.getType()).getAddressSpace();
  auto structTy =
      getStructType(loc.getContext(), memorySpace, indexPtrAddrSpace);
  Value segmentStruct = rewriter.create<LLVM::UndefOp>(loc, structTy);
  segmentStruct = b.insert_val(structTy, segmentStruct, base, 0);
  segmentStruct = b.insert_val(structTy, segmentStruct, segmentBase, 1);
  segmentStruct = b.insert_val(structTy, segmentStruct, indexPtr, 2);
  return segmentStruct;
}

SegmentObject SegmentObject::fromStruct(Location loc, Value segmentStruct,
                                        ConversionPatternRewriter &rewriter) {
  auto b = TritonLLVMOpBuilder(loc, rewriter);
  auto structTy = mlir::cast<LLVM::LLVMStructType>(segmentStruct.getType());
  Value memoryDescriptorPtr =
      b.extract_val(structTy.getBody()[0], segmentStruct, 0);
  Value segmentBase = b.extract_val(structTy.getBody()[1], segmentStruct, 1);
  Value indexPtr = b.extract_val(structTy.getBody()[2], segmentStruct, 2);
  return SegmentObject(memoryDescriptorPtr, segmentBase, indexPtr);
}

} // namespace LLVM

namespace triton {
namespace proton::gpu {

Value getLinearCTAId(Location loc, ConversionPatternRewriter &rewriter) {
  auto b = TritonLLVMOpBuilder(loc, rewriter);
  // Note:
  // 1. We compute use i64 data type to compute and then truncate to i32
  // to support various backend intrinsics (e.g. amd).
  // 2. We avoid using the targetInfo's programId() because of its coupling
  // with cluster id in Nvidia TritonGPU's llvm lowering.
  Value pidX = rewriter.create<arith::IndexCastOp>(
      loc, i64_ty,
      rewriter.create<mlir::gpu::BlockIdOp>(loc, mlir::gpu::Dimension::x));
  Value pidY = rewriter.create<arith::IndexCastOp>(
      loc, i64_ty,
      rewriter.create<mlir::gpu::BlockIdOp>(loc, mlir::gpu::Dimension::y));
  Value pidZ = rewriter.create<arith::IndexCastOp>(
      loc, i64_ty,
      rewriter.create<mlir::gpu::BlockIdOp>(loc, mlir::gpu::Dimension::z));

  Value gridDimX = rewriter.create<arith::IndexCastOp>(
      loc, i64_ty,
      rewriter.create<::mlir::gpu::GridDimOp>(loc, mlir::gpu::Dimension::x));
  Value gridDimY = rewriter.create<arith::IndexCastOp>(
      loc, i64_ty,
      rewriter.create<::mlir::gpu::GridDimOp>(loc, mlir::gpu::Dimension::y));
  Value linearId =
      b.trunc(i32_ty, b.add(b.add(pidX, b.mul(pidY, gridDimX)),
                            b.mul(pidZ, b.mul(gridDimX, gridDimY))));
  return linearId;
}

Value getProgramCollectionPredicate(ModuleOp mod, Location loc,
                                    ConversionPatternRewriter &rewriter) {
  auto b = TritonLLVMOpBuilder(loc, rewriter);
  auto programs =
      mod->getAttrOfType<DenseI32ArrayAttr>("proton.selected_programs");
  if (!programs)
    return b.true_val();
  Value pid = getLinearCTAId(loc, rewriter);
  Value enabled = b.false_val();
  for (int32_t program : programs.asArrayRef())
    enabled = b.or_(enabled, b.icmp_eq(pid, b.i32_val(program)));
  return enabled;
}

CircularStoreDataPack
lowerCircularStoreOpHelper(CircularStoreOp op, Value segmentStruct,
                           ConversionPatternRewriter &rewriter) {
  auto loc = op.getLoc();
  auto mod = op.getOperation()->getParentOfType<ModuleOp>();
  auto b = TritonLLVMOpBuilder(loc, rewriter);
  const int bytesPerEntry = proton::gpu::getBytesPerClockEntry(mod);
  const int wordsPerEntry = bytesPerEntry / 4; // 1 word = 4 bytes

  auto segmentObj =
      LLVM::SegmentObject::fromStruct(loc, segmentStruct, rewriter);
  Value indexPtr = segmentObj.indexPtr;
  Value bufferBase = segmentObj.base;
  Value segmentBase = segmentObj.segmentBase;

  // Update the index (could be register promoted).
  Value curIdx = b.load(i32_ty, indexPtr);
  Value enabled = getProgramCollectionPredicate(mod, loc, rewriter);
  const bool timeline = bytesPerEntry == 16;
  Value writable = b.true_val();
  Value newIdx = b.add(curIdx, b.i32_val(wordsPerEntry));
  if (timeline) {
    // Aligned counters cannot equal this sentinel during normal collection.
    // Freeze instead of silently wrapping the absolute record sequence.
    writable = b.icmp_ule(curIdx, b.i32_val(0xffffffffu - wordsPerEntry));
    newIdx = b.select(writable, newIdx, b.i32_val(0xffffffffu));
  }
  newIdx = b.select(enabled, newIdx, curIdx);
  b.store(newIdx, indexPtr);

  // Compute the segment size in word (4 bytes).
  int selectedWarpNum = getTotalNumWarps(mod);
  auto segmentType = op.getSegment().getType();
  auto selectedIds = segmentType.getSelectIds();
  if (!selectedIds.empty())
    selectedWarpNum = selectedIds.size();
  const int bufferSizeInBytes = segmentType.getNBytes();
  const int segmentWordSize = bufferSizeInBytes / selectedWarpNum / 4;

  // Compute the actual base offset (with urem as circular buffer).
  Value tagOffset =
      b.add(segmentBase, b.urem(curIdx, b.i32_val(segmentWordSize)));

  // Store the counter into buffer.
  auto bufferBaseType = bufferBase.getType();
  Value vecPtr = b.gep(bufferBaseType, i32_ty, bufferBase, tagOffset);

  // Constructing the tag and clock (8 byte)
  // =======================================
  // tag and upper clock (4 bytes):
  // 31: start or end (1 bit)
  // 30:23 scope id (8 bits)
  // 22:11 reserved (12 bits)
  // 10:0  64-bit clock bit 32:42 (11 bits)
  // =======================================
  // lower clock (4 bytes):
  // 31:0 64-bit clock bit 0:31
  // =======================================
  Value clock = op.getCounter();
  auto clkTy = mlir::cast<IntegerType>(clock.getType());
  uint32_t maskedScopeId = op.getScopeId() & 0xff;
  Value tag = op.getIsStart() ? b.i32_val(maskedScopeId << 23)
                              : b.i32_val(1 << 31 | maskedScopeId << 23);
  Value valsVec;
  if (timeline) {
    auto clkVec = b.bitcast(clock, vec_ty(i32_ty, 2));
    Value timelineTag = b.i32_val(
        (op.getIsStart() ? 0u : 0x80000000u) | uint32_t(op.getScopeId()));
    valsVec = packLLVector(
        loc, {timelineTag, b.extract_element(i32_ty, clkVec, b.i32_val(0)),
              b.extract_element(i32_ty, clkVec, b.i32_val(1)),
              b.udiv(curIdx, b.i32_val(wordsPerEntry))}, rewriter);
  } else if (clkTy.getWidth() == 64) {
    auto clkVecTy = vec_ty(i32_ty, 2);
    auto clkVec = b.bitcast(clock, clkVecTy);
    Value clkLower = b.extract_element(i32_ty, clkVec, b.i32_val(0));
    Value clkUpper = b.extract_element(i32_ty, clkVec, b.i32_val(1));
    Value tagClkUpper = b.or_(tag, b.and_(clkUpper, b.i32_val(0x7ff)));
    valsVec = packLLVector(loc, {tagClkUpper, clkLower}, rewriter);
  } else {
    valsVec = packLLVector(loc, {tag, clock}, rewriter);
  }

  // Compute the predicate for the writer.
  const int warpSize = triton::gpu::TritonGPUDialect::getThreadsPerWarp(mod);
  Value curThreadId = getThreadId(rewriter, loc);
  Value isWarpMaster =
      b.icmp_eq(b.urem(curThreadId, b.i32_val(warpSize)), b.i32_val(0));
  Value isWriter;

  auto granularity = segmentType.getGranularity();
  if (selectedIds.empty()) {
    if (granularity == proton::gpu::Granularity::WARP) {
      isWriter = isWarpMaster;
    } else {
      llvm::report_fatal_error(
          "segment address specialization not implemented yet");
    }
  } else {
    Value isCurWarpEnabled = b.icmp_ne(segmentBase, b.i32_val(-1));
    isWriter = b.and_(isCurWarpEnabled, isWarpMaster);
  }

  if (timeline)
    isWriter = b.and_(isWriter, b.and_(enabled, writable));

  uint32_t addrSpace =
      cast<LLVM::LLVMPointerType>(bufferBaseType).getAddressSpace();

  return {isWriter, valsVec, vecPtr, addrSpace};
}

} // namespace proton::gpu
} // namespace triton

} // namespace mlir
