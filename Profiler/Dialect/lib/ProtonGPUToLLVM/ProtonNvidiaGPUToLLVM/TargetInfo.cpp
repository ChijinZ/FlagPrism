#include "Conversion/ProtonGPUToLLVM/ProtonNvidiaGPUToLLVM/TargetInfo.h"
#include "Conversion/ProtonGPUToLLVM/Utility.h"
#include "Dialect/ProtonGPU/IR/Dialect.h"
#include "mlir/Dialect/LLVMIR/LLVMDialect.h"
#include "mlir/Dialect/LLVMIR/LLVMTypes.h"
#include "mlir/Dialect/LLVMIR/NVVMDialect.h"
#include "mlir/IR/SymbolTable.h"
#include "third_party/nvidia/include/TritonNVIDIAGPUToLLVM/PTXAsmFormat.h"
#include "third_party/nvidia/lib/TritonNVIDIAGPUToLLVM/Utility.h" // TODO(fywkevin): move Utility.h to include/
#include "llvm/Support/MathExtras.h"

namespace mlir::triton::proton::gpu::NVIDIA {

Value TargetInfo::clock(ConversionPatternRewriter &rewriter, Location loc,
                        bool isClock64) const {
  return clockWithDependencies(rewriter, loc, isClock64, {}, {});
}

Value TargetInfo::clockWithDependencies(ConversionPatternRewriter &rewriter,
                                        Location loc, bool isClock64,
                                        ArrayRef<Value> dependencies,
                                        StringRef marker) const {
  // One PTX read avoids combining words across rollover. Legacy modes keep
  // SM-local cycles. Timeline explicitly selects a different device timer;
  // this does not establish a join to CUPTI/host or certify its resolution.
  auto mod =
      rewriter.getInsertionBlock()->getParentOp()->getParentOfType<ModuleOp>();
  bool timeline = mod->hasAttr("proton.timeline_timer");
  bool selected = mod->hasAttr("proton.selected_programs") ||
                  mod->hasAttr("proton.timeline_storage_version");
  Value predicate;
  if (selected)
    predicate = getProgramCollectionPredicate(mod, loc, rewriter);

  auto emitRead = [&](ArrayRef<Value> inputs, Value collect) -> Value {
    PTXBuilder builder;
    std::string markerText = "// " + marker.str();
    if (!marker.empty()) {
      auto &tag = *builder.create(markerText);
      tag(llvm::ArrayRef<PTXBuilder::Operand *>{});
    }
    auto &mov = builder.create("mov")->o(isClock64 ? "u64" : "u32");
    auto *dest = builder.newOperand(isClock64 ? "=l" : "=r");
    auto *clock = builder.newConstantOperand(
        timeline ? "%globaltimer" : isClock64 ? "%clock64" : "%clock");
    if (collect) {
      builder.create("mov")->o(isClock64 ? "u64" : "u32")(
          dest, builder.newConstantOperand(0));
      mov(dest, clock).predicate(collect);
    } else {
      mov(dest, clock);
    }
    // These are real LLVM inputs, not a claim that PTX comments consume
    // machine registers. The outlined call and final object are separate facts.
    for (Value dependency : inputs) {
      auto width = cast<IntegerType>(dependency.getType()).getWidth();
      auto &consume = *builder.create("// timeline_llvm_counter_dependency");
      consume(builder.newOperand(dependency, width == 64 ? "l" : "r"));
    }
    Value result = builder.launch(rewriter, loc,
        rewriter.getIntegerType(isClock64 ? 64 : 32), true);
    if (timeline && mod->hasAttr("proton.timeline_boundary_version")) {
      auto assembly = cast<LLVM::InlineAsmOp>(result.getDefiningOp());
      assembly->setAttr("constraints", rewriter.getStringAttr(
          assembly.getConstraints().str() + ",~{memory}"));
    }
    return result;
  };

  auto boundary = mod->getAttrOfType<IntegerAttr>(
      "proton.timeline_boundary_version");
  if (!timeline || !boundary || boundary.getInt() != 2)
    return emitRead(dependencies, predicate);
  if (!isClock64 || marker.empty()) {
    emitError(loc, "Outlined timeline counter requires a marked 64-bit read");
    return {};
  }

  // Materialize a real device-call boundary. No logger state, hardware fence,
  // shared memory or hidden launch argument is added to this leaf function.
  SmallVector<Type> parameters{rewriter.getI1Type()};
  std::string name = "__flagprism_counter_v2_" + marker.str() + "_";
  for (Value dependency : dependencies) {
    Type type = dependency.getType();
    if (!type.isInteger(32) && !type.isInteger(64)) {
      emitError(loc, "Unsupported outlined timeline argument type");
      return {};
    }
    parameters.push_back(type);
    name += type.isInteger(32) ? 'a' : 'b';
  }
  auto resultType = rewriter.getI64Type();
  auto functionType = LLVM::LLVMFunctionType::get(resultType, parameters, false);
  auto helper = mod.lookupSymbol<LLVM::LLVMFuncOp>(name);
  if (Operation *existing = SymbolTable::lookupSymbolIn(mod, rewriter.getStringAttr(name))) {
    if (!helper || helper.getFunctionType() != functionType ||
        !helper->hasAttr("proton.timeline_clock_helper")) {
      emitError(loc, "Conflicting outlined timeline helper symbol");
      return {};
    }
  } else {
    OpBuilder::InsertionGuard guard(rewriter);
    rewriter.setInsertionPointToStart(mod.getBody());
    helper = rewriter.create<LLVM::LLVMFuncOp>(
        loc, name, functionType, LLVM::Linkage::Internal);
    helper->setAttr("proton.timeline_clock_helper", rewriter.getUnitAttr());
    SmallVector<Attribute> attributes{
        rewriter.getStringAttr("noinline"), rewriter.getStringAttr("nounwind"),
        rewriter.getStringAttr("convergent")};
    helper->setAttr("passthrough", rewriter.getArrayAttr(attributes));
    Block *entry = helper.addEntryBlock(rewriter);
    rewriter.setInsertionPointToStart(entry);
    SmallVector<Value> inputs;
    for (BlockArgument argument : entry->getArguments().drop_front())
      inputs.push_back(argument);
    Value stamp = emitRead(inputs, entry->getArgument(0));
    rewriter.create<LLVM::ReturnOp>(loc, ValueRange{stamp});
  }
  SmallVector<Value> arguments;
  if (!predicate) {
    auto b = TritonLLVMOpBuilder(loc, rewriter);
    predicate = b.i1_val(true);
  }
  arguments.push_back(predicate);
  arguments.append(dependencies.begin(), dependencies.end());
  auto call = rewriter.create<LLVM::CallOp>(loc, helper, arguments);
  return call->getResult(0);
}

Value TargetInfo::anchorValue(ConversionPatternRewriter &rewriter, Location loc,
                               Value counter, Value bits) const {
  PTXBuilder builder;
  auto width = cast<IntegerType>(bits.getType()).getWidth();
  auto *out = builder.newOperand(width == 64 ? "=l" : "=r");
  auto &mov = builder.create("mov")->o(width == 64 ? "b64" : "b32");
  mov(out, builder.newOperand(bits, width == 64 ? "l" : "r"));
  auto &consume = *builder.create("// timeline_llvm_begin_dependency");
  consume(builder.newOperand(counter, "l"));
  return builder.launch(rewriter, loc, bits.getType(), true);
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
