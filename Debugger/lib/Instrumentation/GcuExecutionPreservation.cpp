#include "Debugger/Instrumentation/GcuTimeline.h"
#include "mlir/Dialect/Arith/IR/Arith.h"
#include "mlir/Dialect/Func/IR/FuncOps.h"
#include "mlir/Dialect/GPU/IR/GPUDialect.h"
#include "mlir/Dialect/LLVMIR/LLVMDialect.h"
#include "mlir/Dialect/MemRef/IR/MemRef.h"
#include "mlir/Dialect/SCF/IR/SCF.h"
#include "mlir/Dialect/Vector/IR/VectorOps.h"
#include "mlir/IR/BuiltinOps.h"
#include "mlir/IR/SymbolTable.h"
#include "mlir/IR/Verifier.h"
#include "mlir/Parser/Parser.h"
#include "llvm/ADT/DenseMap.h"
#include "llvm/ADT/DenseSet.h"
#include "llvm/ADT/StringSwitch.h"
#include "llvm/Support/FormatVariadic.h"
#include "llvm/Support/JSON.h"
#include "llvm/Support/raw_ostream.h"

using namespace mlir;

namespace {
std::string coreText(ModuleOp module) {
  std::string result;
  llvm::raw_string_ostream stream(result);
  module.print(stream, OpPrintingFlags().printGenericOpForm());
  stream.flush();
  return result;
}

bool pureObserver(StringRef name) {
  return llvm::StringSwitch<bool>(name)
      .Cases("arith.constant", "arith.index_cast", "arith.addi", true)
      .Cases("arith.muli", "arith.subi", "arith.cmpi", true)
      .Cases("arith.select", "arith.andi", "arith.ori", true)
      .Cases("arith.minui", "gpu.block_id", "gpu.grid_dim", true)
      .Cases("gpu.thread_id", "llvm.trunc", "llvm.lshr", true)
      .Cases("llvm.mlir.constant", "scf.if", "scf.for", "scf.yield", true)
      .Cases("memref.extract_aligned_pointer_as_index",
             "memref.extract_strided_metadata", true)
      .Cases("gcu.memref2ptr", "gcu.ptr2int", true)
      .Default(false);
}

bool clockName(StringRef name) {
  return name == "_ZN4tops12global_timerEv" ||
         name == "flagprism_gcu_clock_identity_v1";
}

bool clockDeclaration(LLVM::LLVMFuncOp function) {
  return function && function.isExternal() && clockName(function.getName()) &&
         !function.getFunctionType().isVarArg() &&
         function.getFunctionType().getParams().empty() &&
         function.getFunctionType().getReturnType().isInteger(
             function.getName() == "_ZN4tops12global_timerEv" ? 64 : 32);
}
} // namespace

namespace mlir::flagtree::debugger {
llvm::Expected<std::string>
checkGcuObserverTransformation(ModuleOp before, ModuleOp after,
                               llvm::ArrayRef<Operation *> originalOperations,
                               uint32_t hiddenArgument) {
  auto reject = [](StringRef reason) -> llvm::Error {
    return llvm::createStringError(llvm::inconvertibleErrorCode(),
                                   reason.str());
  };
  if (failed(verify(before)) || failed(verify(after)))
    return reject("Cannot verify GCU preservation modules");
  llvm::DenseSet<Operation *> original(originalOperations.begin(),
                                       originalOperations.end());
  SmallVector<Operation *> current;
  after.walk([&](Operation *op) { current.push_back(op); });
  unsigned present = 0;
  for (Operation *op : current) {
    if (!original.contains(op))
      continue;
    ++present;
    if (op != after.getOperation() && !original.contains(op->getParentOp()))
      return reject("Original GCU operation moved into observer control");
    for (Value operand : op->getOperands()) {
      Operation *owner = operand.getDefiningOp();
      if (!owner)
        owner = cast<BlockArgument>(operand).getOwner()->getParentOp();
      if (!original.contains(owner))
        return reject("Original GCU operand replaced by observer value");
    }
  }
  if (present != original.size())
    return reject("Original GCU operation was erased");
  OwningOpRef<ModuleOp> projection = cast<ModuleOp>(after->clone());
  SmallVector<Operation *> cloned;
  projection->walk([&](Operation *op) { cloned.push_back(op); });
  if (cloned.size() != current.size())
    return reject("GCU projection clone differs");
  llvm::DenseSet<Operation *> extras;
  for (auto [source, clone] : llvm::zip(current, cloned))
    if (!original.contains(source))
      extras.insert(clone);
  // No original op consumes an extra value. Drop all observer-to-observer
  // references before deleting in postorder; original SSA/CFG is then checked
  // as a whole, including block arguments and operation properties.
  for (Operation *op : extras)
    op->dropAllReferences();
  SmallVector<Operation *> erase;
  projection->walk<WalkOrder::PostOrder>([&](Operation *op) {
    if (extras.contains(op))
      erase.push_back(op);
  });
  for (Operation *op : erase)
    op->erase();
  (*projection)->removeAttr("flagprism.gcu_execution_timeline_version");
  if (coreText(*projection) != coreText(before))
    return reject("Original GCU SSA/control program changed");
  SmallVector<func::FuncOp> functions;
  before.walk([&](func::FuncOp f) {
    if (!f.isExternal())
      functions.push_back(f);
  });
  if (functions.size() != 1 ||
      hiddenArgument >= functions.front().getNumArguments() ||
      hiddenArgument != functions.front().getNumArguments() - 1 ||
      !functions.front().getArgument(hiddenArgument).use_empty())
    return reject(
        "GCU hidden output must be the unused last original argument");
  func::FuncOp rewritten;
  after.walk([&](func::FuncOp f) {
    if (!f.isExternal())
      rewritten = f;
  });
  Value hidden = rewritten.getArgument(hiddenArgument);
  llvm::DenseSet<Operation *> fresh;
  SmallVector<Operation *> added;
  after.walk([&](Operation *op) {
    if (!original.contains(op)) {
      added.push_back(op);
      if (isa<memref::AllocOp>(op))
        fresh.insert(op);
    }
  });
  if (added.size() > 200000)
    return reject("GCU observer operation budget exceeded");
  auto freshMemory = [&](Value value) {
    return fresh.contains(value.getDefiningOp());
  };
  auto hiddenView = [&](Value value) {
    Operation *op = value.getDefiningOp();
    return op && !original.contains(op) &&
           op->getName().getStringRef() == "gcu.ptr2memref" &&
           op->getNumOperands() == 1 && op->getOperand(0) == hidden;
  };
  unsigned publications = 0;
  for (Operation *op : added) {
    StringRef name = op->getName().getStringRef();
    if (pureObserver(name))
      continue;
    if (auto alloc = dyn_cast<memref::AllocOp>(op)) {
      auto type = alloc.getType();
      if (type.getRank() == 1 && type.hasStaticShape() &&
          type.getDimSize(0) > 0 && type.getElementType().isInteger(32))
        continue;
    } else if (auto store = dyn_cast<memref::StoreOp>(op)) {
      if (freshMemory(store.getMemref()))
        continue;
    } else if (auto load = dyn_cast<memref::LoadOp>(op)) {
      if (freshMemory(load.getMemref()))
        continue;
    } else if (auto dealloc = dyn_cast<memref::DeallocOp>(op)) {
      if (freshMemory(dealloc.getMemref()))
        continue;
    } else if (auto dma = dyn_cast<memref::DmaStartOp>(op)) {
      if (freshMemory(dma.getSrcMemRef()) && hiddenView(dma.getDstMemRef()) &&
          freshMemory(dma.getTagMemRef()) &&
          dma.getTagMemRef().getDefiningOp()->hasAttr("gcu_private_tag")) {
        ++publications;
        continue;
      }
    } else if (auto wait = dyn_cast<memref::DmaWaitOp>(op)) {
      if (freshMemory(wait.getTagMemRef()))
        continue;
    } else if (auto call = dyn_cast<LLVM::CallOp>(op)) {
      if (!call.getCallee())
        return reject("Unisolated GCU observer indirect call");
      auto declaration = dyn_cast_or_null<LLVM::LLVMFuncOp>(
          SymbolTable::lookupNearestSymbolFrom(op, call.getCalleeAttr()));
      if (call.getCallee() && clockName(*call.getCallee()) &&
          clockDeclaration(declaration) && call.getNumOperands() == 0 &&
          call.getNumResults() == 1 &&
          call.getResult().getType().isInteger(
              *call.getCallee() == "_ZN4tops12global_timerEv" ? 64 : 32))
        continue;
    } else if (auto declaration = dyn_cast<LLVM::LLVMFuncOp>(op)) {
      if (clockDeclaration(declaration))
        continue;
    } else if (name == "gcu.ptr2memref" && op->getNumResults() == 1 &&
               hiddenView(op->getResult(0))) {
      continue;
    }
    return reject("Unisolated GCU observer operation: " + name.str());
  }
  if (fresh.empty() || !publications)
    return reject("GCU rewrite has no isolated storage/publication");
  llvm::json::Object certificate{
      {"schema_version", 1},
      {"boundary", "gcu_execution_ir_before_SDK_lowering"},
      {"original_program_preserved", true},
      {"observer_memory_isolated", true},
      {"original_operations", int64_t(original.size())},
      {"added_operations", int64_t(added.size())},
      {"fresh_allocations", int64_t(fresh.size())},
      {"trace_publications", publications},
      {"allocation_bounds_qualified", false},
      {"SDK_lowering_qualified", false},
      {"native_timing_boundary_qualified", false}};
  return llvm::formatv("{0:2}", llvm::json::Value(std::move(certificate)))
      .str();
}
llvm::Expected<std::string>
checkGcuExecutionPreservation(StringRef input, StringRef output,
                              uint32_t hiddenArgument, uint32_t capacity,
                              uint32_t maxRegions) {
  if (output.size() > 16 * 1024 * 1024)
    return llvm::createStringError(llvm::inconvertibleErrorCode(),
                                   "GCU preservation output exceeds budget");
  auto rewrite =
      rewriteGcuExecutionTimeline(input, hiddenArgument, capacity, maxRegions);
  if (!rewrite)
    return rewrite.takeError();
  bool sameBytes = rewrite->ir == output;
  if (!sameBytes) {
    // Historical producers may differ only in navigation locations. Compare
    // the complete typed IR core, not a guessed SSA correspondence. This
    // qualifies program projection only; debug locations can affect codegen
    // and are never a final native-timing proof.
    DialectRegistry registry;
    registry.insert<arith::ArithDialect, func::FuncDialect, gpu::GPUDialect,
                    LLVM::LLVMDialect, memref::MemRefDialect, scf::SCFDialect,
                    vector::VectorDialect>();
    MLIRContext context(registry);
    context.allowUnregisteredDialects();
    auto expected = parseSourceString<ModuleOp>(rewrite->ir, &context);
    auto actual = parseSourceString<ModuleOp>(output, &context);
    if (!expected || !actual || failed(verify(*actual)) ||
        coreText(*expected) != coreText(*actual))
      return llvm::createStringError(
          llvm::inconvertibleErrorCode(),
          "Actual GCU output differs from checked producer");
  }
  auto manifest = llvm::json::parse(rewrite->manifest);
  if (!manifest)
    return manifest.takeError();
  auto *object = manifest->getAsObject();
  auto *certificate =
      object ? object->get("user_program_preservation") : nullptr;
  if (!certificate)
    return llvm::createStringError(
        llvm::inconvertibleErrorCode(),
        "Checked GCU producer has no preservation result");
  auto *proof = certificate->getAsObject();
  if (!proof)
    return llvm::createStringError(llvm::inconvertibleErrorCode(),
                                   "Invalid GCU preservation result");
  (*proof)["actual_output_bytes_identical"] = sameBytes;
  (*proof)["actual_output_program_core_identical"] = true;
  return llvm::formatv("{0:2}", *certificate).str();
}
} // namespace mlir::flagtree::debugger
