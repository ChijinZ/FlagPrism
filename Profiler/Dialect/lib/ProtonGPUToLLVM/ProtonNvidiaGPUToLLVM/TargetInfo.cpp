#include "Conversion/ProtonGPUToLLVM/ProtonNvidiaGPUToLLVM/TargetInfo.h"
#include "Conversion/ProtonGPUToLLVM/Utility.h"
#include "Dialect/ProtonGPU/IR/Dialect.h"
#include "mlir/Dialect/ControlFlow/IR/ControlFlowOps.h"
#include "mlir/Dialect/LLVMIR/LLVMDialect.h"
#include "mlir/Dialect/LLVMIR/LLVMTypes.h"
#include "mlir/Dialect/LLVMIR/NVVMDialect.h"
#include "mlir/IR/SymbolTable.h"
#include "third_party/nvidia/include/TritonNVIDIAGPUToLLVM/PTXAsmFormat.h"
#include "third_party/nvidia/lib/TritonNVIDIAGPUToLLVM/Utility.h" // TODO(fywkevin): move Utility.h to include/
#include "llvm/Support/MathExtras.h"

namespace mlir::triton::proton::gpu::NVIDIA {

namespace {
constexpr llvm::StringLiteral runtimeZeroName =
    "__flagprism_timeline_runtime_zero_v3";

// An initialized mutable device global stays opaque to both LLVM and PTXAS.
// It is private profiler state: no instrumentation path writes it. Load once
// per actual function invocation; the value dominates every local boundary.
Value getRuntimeZero(ConversionPatternRewriter &rewriter, Location loc,
                     ModuleOp mod) {
  auto function = rewriter.getInsertionBlock()->getParentOp();
  auto llvmFunction = dyn_cast<LLVM::LLVMFuncOp>(function);
  if (!llvmFunction || llvmFunction.empty()) {
    emitError(loc, "Timeline dependency mask requires an actual LLVM function");
    return {};
  }
  for (Operation &operation : llvmFunction.front())
    if (operation.hasAttr("proton.timeline_runtime_zero_load"))
      return operation.getResult(0);
  auto global = mod.lookupSymbol<LLVM::GlobalOp>(runtimeZeroName);
  if (Operation *existing = SymbolTable::lookupSymbolIn(
          mod, rewriter.getStringAttr(runtimeZeroName))) {
    if (!global || !global->hasAttr("proton.timeline_runtime_zero")) {
      emitError(loc, "Conflicting profiler runtime-zero global");
      return {};
    }
  } else {
    OpBuilder::InsertionGuard guard(rewriter);
    rewriter.setInsertionPointToStart(mod.getBody());
    global = rewriter.create<LLVM::GlobalOp>(
        loc, rewriter.getI32Type(), false, LLVM::Linkage::External,
        runtimeZeroName, rewriter.getI32IntegerAttr(0), 4, 1);
    global->setAttr("proton.timeline_runtime_zero", rewriter.getUnitAttr());
  }
  OpBuilder::InsertionGuard guard(rewriter);
  rewriter.setInsertionPointToStart(&llvmFunction.front());
  auto address = rewriter.create<LLVM::AddressOfOp>(loc, global);
  PTXBuilder builder;
  auto *output = builder.newOperand("=r");
  builder.create("ld")
      ->o("volatile")
      .global()
      .b(32)(output, builder.newAddrOperand(address, "l"));
  auto result = builder.launch(rewriter, loc, rewriter.getI32Type(), true);
  result.getDefiningOp()->setAttr("proton.timeline_runtime_zero_load",
                                  rewriter.getUnitAttr());
  return result;
}

Value guardedClockCall(ConversionPatternRewriter &rewriter, Location loc,
                       LLVM::LLVMFuncOp helper, Value condition) {
  auto b = TritonLLVMOpBuilder(loc, rewriter);
  Value empty = b.i64_val(0);
  Block *before = rewriter.getInsertionBlock();
  Block *after = rewriter.splitBlock(before, rewriter.getInsertionPoint());
  Block *join = rewriter.createBlock(after, {rewriter.getI64Type()}, {loc});
  Block *invoke = rewriter.createBlock(join);
  rewriter.setInsertionPointToEnd(before);
  rewriter.create<cf::CondBranchOp>(loc, condition, invoke, ValueRange{}, join,
                                    ValueRange{empty});
  rewriter.setInsertionPointToStart(invoke);
  auto call = rewriter.create<LLVM::CallOp>(loc, helper, ValueRange{});
  rewriter.create<cf::BranchOp>(loc, join, call.getResults());
  rewriter.setInsertionPointToStart(join);
  rewriter.create<cf::BranchOp>(loc, after);
  rewriter.setInsertionPointToStart(after);
  return join->getArgument(0);
}
} // namespace

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
    auto *clock = builder.newConstantOperand(timeline    ? "%globaltimer"
                                             : isClock64 ? "%clock64"
                                                         : "%clock");
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
    Value result = builder.launch(
        rewriter, loc, rewriter.getIntegerType(isClock64 ? 64 : 32), true);
    if (timeline && mod->hasAttr("proton.timeline_boundary_version")) {
      auto assembly = cast<LLVM::InlineAsmOp>(result.getDefiningOp());
      assembly->setAttr("constraints",
                        rewriter.getStringAttr(assembly.getConstraints().str() +
                                               ",~{memory}"));
    }
    return result;
  };

  auto boundary =
      mod->getAttrOfType<IntegerAttr>("proton.timeline_boundary_version");
  if (timeline && boundary && boundary.getInt() == 3) {
    if (!isClock64 || marker.empty()) {
      emitError(loc, "Gated timeline counter requires a marked 64-bit read");
      return {};
    }
    Value zero = getRuntimeZero(rewriter, loc, mod);
    if (!zero)
      return {};
    auto b = TritonLLVMOpBuilder(loc, rewriter);
    Value combined = b.i32_val(0);
    for (Value dependency : dependencies) {
      auto type = dyn_cast<IntegerType>(dependency.getType());
      if (!type || (type.getWidth() != 32 && type.getWidth() != 64)) {
        emitError(loc, "Unsupported gated timeline dependency type");
        return {};
      }
      Value word = dependency;
      if (type.getWidth() == 64) {
        auto low = rewriter.create<LLVM::TruncOp>(loc, i32_ty, dependency);
        auto shifted = b.lshr(dependency, b.i64_val(32));
        auto high = rewriter.create<LLVM::TruncOp>(loc, i32_ty, shifted);
        word = b.or_(low, high);
      }
      combined = b.or_(combined, word);
    }
    Value ready = b.icmp_eq(b.and_(combined, zero), b.i32_val(0));
    if (predicate)
      ready = b.and_(ready, predicate);
    std::string name = "__flagprism_counter_v3_" + marker.str();
    auto functionType = LLVM::LLVMFunctionType::get(i64_ty, {}, false);
    auto helper = mod.lookupSymbol<LLVM::LLVMFuncOp>(name);
    if (Operation *existing =
            SymbolTable::lookupSymbolIn(mod, rewriter.getStringAttr(name))) {
      if (!helper || helper.getFunctionType() != functionType ||
          !helper->hasAttr("proton.timeline_clock_helper")) {
        emitError(loc, "Conflicting gated timeline helper symbol");
        return {};
      }
    } else {
      OpBuilder::InsertionGuard guard(rewriter);
      rewriter.setInsertionPointToStart(mod.getBody());
      helper = rewriter.create<LLVM::LLVMFuncOp>(loc, name, functionType,
                                                 LLVM::Linkage::Internal);
      helper->setAttr("proton.timeline_clock_helper", rewriter.getUnitAttr());
      helper->setAttr(
          "passthrough",
          rewriter.getArrayAttr({rewriter.getStringAttr("noinline"),
                                 rewriter.getStringAttr("nounwind"),
                                 rewriter.getStringAttr("convergent")}));
      Block *entry = helper.addEntryBlock(rewriter);
      rewriter.setInsertionPointToStart(entry);
      Value stamp = emitRead({}, {});
      rewriter.create<LLVM::ReturnOp>(loc, ValueRange{stamp});
    }
    return guardedClockCall(rewriter, loc, helper, ready);
  }
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
  auto functionType =
      LLVM::LLVMFunctionType::get(resultType, parameters, false);
  auto helper = mod.lookupSymbol<LLVM::LLVMFuncOp>(name);
  if (Operation *existing =
          SymbolTable::lookupSymbolIn(mod, rewriter.getStringAttr(name))) {
    if (!helper || helper.getFunctionType() != functionType ||
        !helper->hasAttr("proton.timeline_clock_helper")) {
      emitError(loc, "Conflicting outlined timeline helper symbol");
      return {};
    }
  } else {
    OpBuilder::InsertionGuard guard(rewriter);
    rewriter.setInsertionPointToStart(mod.getBody());
    helper = rewriter.create<LLVM::LLVMFuncOp>(loc, name, functionType,
                                               LLVM::Linkage::Internal);
    helper->setAttr("proton.timeline_clock_helper", rewriter.getUnitAttr());
    SmallVector<Attribute> attributes{rewriter.getStringAttr("noinline"),
                                      rewriter.getStringAttr("nounwind"),
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
  auto mod =
      rewriter.getInsertionBlock()->getParentOp()->getParentOfType<ModuleOp>();
  auto boundary =
      mod->getAttrOfType<IntegerAttr>("proton.timeline_boundary_version");
  if (boundary && boundary.getInt() == 3) {
    Value zero = getRuntimeZero(rewriter, loc, mod);
    if (!zero)
      return {};
    auto width = cast<IntegerType>(bits.getType()).getWidth();
    PTXBuilder builder;
    auto *out = builder.newOperand(width == 64 ? "=l" : "=r");
    auto *input = builder.newOperand(bits, width == 64 ? "l" : "r");
    auto *stamp = builder.newOperand(counter, "l");
    auto *mask = builder.newOperand(zero, "r");
    std::string assembly;
    if (width == 64)
      assembly = "{ .reg .b64 z, m; mov.b64 z, {$3, $3}; "
                 "and.b64 m, $2, z; xor.b64 $0, $1, m; }";
    else
      assembly = "{ .reg .b32 c, m; cvt.u32.u64 c, $2; "
                 "and.b32 m, c, $3; xor.b32 $0, $1, m; }";
    // Use the builder to establish the four operand constraints, then install
    // the scoped PTX block. Temporaries are PTX-local registers, not extra
    // LLVM output operands.
    builder.create("mov")->b(width)(out, input);
    (*builder.create("// timeline_runtime_mask_inputs"))(stamp, mask);
    Value result = builder.launch(rewriter, loc, bits.getType(), true);
    cast<LLVM::InlineAsmOp>(result.getDefiningOp()).setAsmString(assembly);
    return result;
  }
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
