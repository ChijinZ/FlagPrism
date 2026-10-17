#include "Conversion/ProtonGPUToLLVM/ProtonNvidiaGPUToLLVM/TargetInfo.h"
#include "Conversion/ProtonGPUToLLVM/Utility.h"
#include "Dialect/ProtonGPU/IR/Dialect.h"
#include "mlir/Dialect/LLVMIR/LLVMDialect.h"
#include "mlir/Dialect/LLVMIR/LLVMTypes.h"
#include "mlir/Dialect/LLVMIR/NVVMDialect.h"
#include "third_party/nvidia/include/TritonNVIDIAGPUToLLVM/PTXAsmFormat.h"
#include "third_party/nvidia/lib/TritonNVIDIAGPUToLLVM/Utility.h" // TODO(fywkevin): move Utility.h to include/
#include "llvm/Support/MathExtras.h"

namespace mlir::triton::proton::gpu::NVIDIA {

Value TargetInfo::clock(ConversionPatternRewriter &rewriter, Location loc,
                        bool isClock64) const {

  // One PTX read avoids combining words across rollover. Legacy modes keep
  // SM-local cycles. Timeline explicitly selects a different device timer;
  // this does not establish a join to CUPTI/host or certify its resolution.
  auto mod =
      rewriter.getInsertionBlock()->getParentOp()->getParentOfType<ModuleOp>();
  bool timeline = mod->hasAttr("proton.timeline_timer");
  PTXBuilder builder;
  auto &mov = builder.create("mov")->o(isClock64 ? "u64" : "u32");
  auto *dest = builder.newOperand(isClock64 ? "=l" : "=r");
  auto *clock = builder.newConstantOperand(
      timeline ? "%globaltimer" : isClock64 ? "%clock64" : "%clock");
  if (mod->hasAttr("proton.selected_programs")) {
    builder.create("mov")->o(isClock64 ? "u64" : "u32")(
        dest, builder.newConstantOperand(0));
    mov(dest, clock)
        .predicate(getProgramCollectionPredicate(mod, loc, rewriter));
  } else {
    mov(dest, clock);
  }
  return builder.launch(rewriter, loc,
                        rewriter.getIntegerType(isClock64 ? 64 : 32), true);
}

Value TargetInfo::processorId(ConversionPatternRewriter &rewriter,
                              Location loc) const {
  return rewriter.create<NVVM::SmIdOp>(loc, i32_ty);
}

int TargetInfo::getAddressSpace(Attribute addressSpace) const {
  int spaceId = 0;
  if (mlir::isa<triton::gpu::SharedMemorySpaceAttr>(addressSpace)) {
    spaceId = 3;
  } else if (mlir::isa<proton::gpu::GlobalMemorySpaceAttr>(addressSpace)) {
    spaceId = 1;
  } else {
    llvm::report_fatal_error("Only support SharedMemorySpace, "
                             "and GlobalMemorySpace for now");
  }
  return spaceId;
}

int TargetInfo::getIndexPtrAddrSpace() const {
  // Internal buffer index is private to each thread, we use generic address
  // space for NV GPUs. See detail discussion:
  // https://llvm.org/docs/NVPTXUsage.html#address-spaces
  // The reason we don't use address space 5 is due to the downstream compiler
  // generates incorrect `cvta` instruction for %SP/%SPL register that causes
  // IMA when we perform thread-private memory access like `ld.local`.
  return 0;
}

} // namespace mlir::triton::proton::gpu::NVIDIA
