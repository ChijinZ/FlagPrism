#include "Conversion/ProtonGPUToLLVM/ProtonNvidiaGPUToLLVM/NvidiaPatternProtonGPUOpToLLVM.h"
#include "Conversion/ProtonGPUToLLVM/ProtonNvidiaGPUToLLVM/TargetInfo.h"
#include "Conversion/ProtonGPUToLLVM/Utility.h"
#include "Dialect/ProtonGPU/IR/Dialect.h"
#include "mlir/Conversion/LLVMCommon/Pattern.h"
#include "mlir/Conversion/LLVMCommon/TypeConverter.h"
#include "mlir/IR/PatternMatch.h"
#include "third_party/nvidia/include/TritonNVIDIAGPUToLLVM/PTXAsmFormat.h"
#include "triton/Conversion/TritonGPUToLLVM/Utility.h"

using namespace mlir;
using namespace mlir::triton;

namespace {

// Circular strategy memory layout of profiled data (total: N bytes).
// Assuming we record data from warp 0, 2, 7 so buffer looks like:
//  +-----------------------------------------------+
//  | warp 0 data (N/3 bytes)                       |
//  +-----------------------------------------------+
//  | warp 2 data (N/3 bytes)                       |
//  +-----------------------------------------------+
//  | warp 7 data (N/3 bytes)                       |
//  +-----------------------------------------------+

struct CircularStoreOpConversion
    : public ConvertOpToLLVMPattern<
          mlir::triton::proton::gpu::CircularStoreOp> {
  explicit CircularStoreOpConversion(
      LLVMTypeConverter &typeConverter,
      const proton::gpu::TargetInfoBase &targetInfo, PatternBenefit benefit)
      : mlir::ConvertOpToLLVMPattern<
            mlir::triton::proton::gpu::CircularStoreOp>(typeConverter, benefit),
        targetInfo(targetInfo) {}

  LogicalResult
  matchAndRewrite(mlir::triton::proton::gpu::CircularStoreOp op,
                  OpAdaptor adaptor,
                  ConversionPatternRewriter &rewriter) const override {
    auto loc = op.getLoc();

    Value origin;
    if (auto association = op.getAssociation()) {
      auto type = cast<triton::gpu::MemDescType>(association.getType());
      Type element = getTypeConverter()->convertType(type.getElementType());
      auto object = LLVM::getSharedMemoryObjectFromStruct(
          loc, adaptor.getAssociation(), element, rewriter);
      auto b = TritonLLVMOpBuilder(loc, rewriter);
      Value offset = object.getShmemOffset(loc, rewriter, type);
      if (auto padded = dyn_cast<triton::gpu::PaddedSharedEncodingAttr>(
              type.getEncoding()))
        offset = b.add(offset, emitPadding(loc, rewriter, padded,
                                           type.getElementTypeBitWidth(),
                                           offset, /*offsetInBytes=*/false));
      Value pointer =
          b.gep(object.getBase().getType(), element, object.getBase(), offset);
      origin = b.ptrtoint(i32_ty, pointer);
    }

    auto dataPack =
        lowerCircularStoreOpHelper(op, adaptor.getSegment(), rewriter, origin);

    uint32_t addrSpace = dataPack.addrSpace;
    if (addrSpace == 1) {
      llvm::report_fatal_error("unimplemented");
    } else if (addrSpace == 3) {
      auto b = TritonLLVMOpBuilder(loc, rewriter);
      unsigned words =
          cast<VectorType>(dataPack.record.getType()).getNumElements();
      // PTX shared stores support at most four i32 values per instruction.
      // Completion of the kernel, not either half-store, publishes the record.
      for (unsigned first = 0; first < words; first += 4) {
        SmallVector<Value> values;
        for (unsigned i = first; i < std::min(first + 4, words); ++i)
          values.push_back(
              b.extract_element(i32_ty, dataPack.record, b.i32_val(i)));
        Value pointer = b.gep(dataPack.ptr.getType(), i32_ty, dataPack.ptr,
                              b.i32_val(first));
        targetInfo.getTritonTargetInfo().storeDShared(
            rewriter, loc, pointer, std::nullopt,
            packLLVector(loc, values, rewriter),
            /*pred=*/dataPack.isWriter);
      }
    } else {
      llvm::report_fatal_error("unsupported address space in circular store");
    }
    rewriter.eraseOp(op);
    return success();
  }

protected:
  const proton::gpu::TargetInfoBase &targetInfo;
};

} // namespace

namespace mlir::triton::proton::gpu::NVIDIA {
void populateProtonGPUOpNvidiaPatterns(LLVMTypeConverter &typeConverter,
                                       RewritePatternSet &patterns,
                                       const TargetInfo &targetInfo,
                                       PatternBenefit benefit) {
  patterns.add<CircularStoreOpConversion>(typeConverter, targetInfo, benefit);
}
} // namespace mlir::triton::proton::gpu::NVIDIA
