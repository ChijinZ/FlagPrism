#ifndef PROTONGPU_TO_LLVM_UTILITY_H
#define PROTONGPU_TO_LLVM_UTILITY_H

#include "Dialect/ProtonGPU/IR/Dialect.h"
#include "mlir/Dialect/LLVMIR/LLVMTypes.h"
#include "mlir/IR/Value.h"
#include "mlir/Transforms/DialectConversion.h"

namespace mlir {

Value getRawThreadId(OpBuilder &rewriter, Location loc);

namespace LLVM {

struct SegmentObject {
  Value base;
  Value segmentBase;
  Value indexPtr;

  SegmentObject(Value base, Value segmentBase, Value indexPtr)
      : base(base), segmentBase(segmentBase), indexPtr(indexPtr) {}

  Value getStruct(Location loc, ConversionPatternRewriter &rewriter);

  static LLVMStructType getStructType(MLIRContext *ctx, int memorySpace,
                                      int indexPtrAddrSpace);

  static SegmentObject fromStruct(Location loc, Value segmentStruct,
                                  ConversionPatternRewriter &rewriter);
};

} // namespace LLVM

namespace triton {
namespace proton::gpu {

Value getLinearCTAId(Location loc, ConversionPatternRewriter &rewriter);
// Physical record slot, distinct from the logical CTA identity in the header.
Value getProgramCollectionSlot(ModuleOp mod, Location loc,
                               ConversionPatternRewriter &rewriter);
Value getProgramCollectionPredicate(ModuleOp mod, Location loc,
                                    ConversionPatternRewriter &rewriter);

struct CircularStoreDataPack {
  Value isWriter;
  Value record;
  Value ptr;
  uint32_t addrSpace;
};

CircularStoreDataPack
lowerCircularStoreOpHelper(CircularStoreOp op, Value segmentStruct,
                           ConversionPatternRewriter &rewriter);

} // namespace proton::gpu
} // namespace triton

} // namespace mlir

#endif // PROTONGPU_TO_LLVM_UTILITY_H
