#include "Debugger/Instrumentation/GcuTimeline.h"

#include "mlir/AsmParser/AsmParser.h"
#include "mlir/Dialect/Arith/IR/Arith.h"
#include "mlir/Dialect/Func/IR/FuncOps.h"
#include "mlir/Dialect/GPU/IR/GPUDialect.h"
#include "mlir/Dialect/LLVMIR/LLVMDialect.h"
#include "mlir/Dialect/MemRef/IR/MemRef.h"
#include "mlir/Dialect/SCF/IR/SCF.h"
#include "mlir/Dialect/Vector/IR/VectorOps.h"
#include "mlir/IR/AsmState.h"
#include "mlir/IR/Builders.h"
#include "mlir/IR/SymbolTable.h"
#include "mlir/IR/Verifier.h"
#include "mlir/Parser/Parser.h"
#include "llvm/ADT/DenseMap.h"
#include "llvm/ADT/STLExtras.h"
#include "llvm/Support/FormatVariadic.h"
#include "llvm/Support/JSON.h"
#include "llvm/Support/raw_ostream.h"
#include <algorithm>
#include <optional>

using namespace mlir;
namespace mlir::flagtree::debugger {
namespace {
constexpr uint32_t Words = 32;
constexpr uint32_t Magic = 0x46504733;
constexpr uint32_t SealLow = 0x55543033;
constexpr uint32_t SealHigh = 0x46504743;

enum Kind : uint32_t {
  Submit = 1,
  Wait = 2,
  Compute = 3,
  Barrier = 4,
  Region = 5
};
struct Site {
  Operation *op;
  uint32_t id;
  Kind kind;
  Value queue;
  Value queueIndex;
  Value destination;
  Value source;
  Value secondarySource = {};
  Value thirdSource = {};
  Operation *end = nullptr;
};

llvm::Error error(llvm::Twine message) {
  return llvm::createStringError(llvm::inconvertibleErrorCode(), message);
}
std::string printed(Location location) {
  std::string value;
  llvm::raw_string_ostream out(value);
  location.print(out);
  return value;
}
std::string printed(Type type) {
  std::string value;
  llvm::raw_string_ostream out(value);
  type.print(out);
  return value;
}

// These are actual SDK execution primitives, not source/operator-name lists.
// An unrecognized primitive stays visible in the manifest and cannot silently
// acquire a completion/dependency contract.
std::optional<Site> classify(Operation *op, uint32_t id) {
  StringRef name = op->getName().getStringRef();
  if (auto dma = dyn_cast<memref::DmaStartOp>(op)) {
    if (dma.getTagIndices().size() != 1)
      return std::nullopt;
    return Site{op,
                id,
                Submit,
                dma.getTagMemRef(),
                dma.getTagIndices().front(),
                dma.getDstMemRef(),
                dma.getSrcMemRef()};
  }
  if (name == "memref.dma_wait") {
    if (op->getNumOperands() != 3 ||
        !isa<MemRefType>(op->getOperand(0).getType()) ||
        !op->getOperand(1).getType().isIndex())
      return std::nullopt;
    return Site{op, id, Wait, op->getOperand(0), op->getOperand(1), {}, {}};
  }
  if (name == "memref_ext.slice_start" ||
      name == "memref_ext.slice_pad_start" ||
      name == "memref_ext.slice_deslice_start" ||
      name == "memref_ext.deslice_start" || name == "memref_ext.memset_start" ||
      name == "memref_ext.transpose_start" ||
      name == "memref_ext.broadcast_start") {
    unsigned count = op->getNumOperands();
    if (count < 4 || !isa<MemRefType>(op->getOperand(0).getType()) ||
        !isa<MemRefType>(op->getOperand(count - 2).getType()) ||
        !op->getOperand(count - 1).getType().isIndex())
      return std::nullopt;
    Value source =
        name == "memref_ext.memset_start" ? Value{} : op->getOperand(1);
    if (source && !isa<MemRefType>(source.getType()))
      return std::nullopt;
    return Site{op,
                id,
                Submit,
                op->getOperand(count - 2),
                op->getOperand(count - 1),
                op->getOperand(0),
                source};
  }
  if (name == "gcu.matmul") {
    if (op->getNumOperands() < 3)
      return std::nullopt;
    for (Value value : op->getOperands())
      if (!isa<MemRefType>(value.getType()))
        return std::nullopt;
    // Actual SDK operand order is accumulator/output, left, right. This
    // bracket is not a physical engine-busy or completion measurement.
    return Site{op,
                id,
                Compute,
                {},
                {},
                op->getOperand(0),
                op->getOperand(1),
                op->getOperand(2),
                op->getNumOperands() >= 4 ? op->getOperand(3) : Value{}};
  }
  if (name == "gpu.barrier")
    return Site{op, id, Barrier, {}, {}, {}, {}};
  return std::nullopt;
}

void collectSites(func::FuncOp function, uint32_t maxRegions,
                  SmallVectorImpl<Site> &sites, llvm::json::Array &unknown,
                  llvm::json::Array &unselectedRegions,
                  uint32_t &selectedRegions) {
  function.walk([&](Operation *op) {
    if (auto site = classify(op, sites.size() + 1))
      sites.push_back(*site);
    else {
      StringRef name = op->getName().getStringRef();
      if (name.starts_with("memref_ext.") || name == "memref.dma_start")
        unknown.push_back(llvm::json::Object{
            {"operation", name.str()}, {"location", printed(op->getLoc())}});
    }
  });
  function.walk([&](Operation *op) {
    if (op->getName().getStringRef() != "gcu.border")
      return;
    auto enter = op->getAttrOfType<StringAttr>("enter");
    if (!enter || enter.getValue() != "triton_gcu.elementwise_fusion_region")
      return;
    unsigned depth = 1;
    Operation *end = nullptr;
    for (Operation *next = op->getNextNode(); next;
         next = next->getNextNode()) {
      if (next->getName().getStringRef() != "gcu.border")
        continue;
      if (auto nested = next->getAttrOfType<StringAttr>("enter"))
        if (nested.getValue() == enter.getValue())
          ++depth;
      if (auto leave = next->getAttrOfType<StringAttr>("leave"))
        if (leave.getValue() == enter.getValue() && --depth == 0) {
          end = next;
          break;
        }
    }
    if (!end) {
      unknown.push_back(llvm::json::Object{
          {"operation", "unpaired_elementwise_fusion_region"},
          {"location", printed(op->getLoc())}});
      return;
    }
    if (selectedRegions == maxRegions) {
      unselectedRegions.push_back(printed(op->getLoc()));
      return;
    }
    ++selectedRegions;
    sites.push_back(Site{op,
                         static_cast<uint32_t>(sites.size() + 1),
                         Region,
                         {},
                         {},
                         {},
                         {},
                         {},
                         {},
                         end});
  });
}

llvm::json::Object
sourceMembership(const Site &site,
                 const llvm::DenseMap<Operation *, uint32_t> &original,
                 uint32_t &work, uint64_t &detailBytes) {
  llvm::json::Array members, controls;
  bool exceeded = false;
  StringRef reason = "source_member_budget_exceeded";
  auto escapedSize = [](StringRef value) -> uint64_t {
    uint64_t bytes = 0;
    for (unsigned char byte : value.bytes())
      bytes += byte < 32 ? 6 : (byte == '"' || byte == '\\') ? 2 : 1;
    return bytes;
  };
  auto describe = [&](Operation *op) {
    if (++work > 100000 || members.size() >= 8192) {
      exceeded = true;
      return;
    }
    auto found = original.find(op);
    if (found == original.end())
      return;
    StringRef operation = op->getName().getStringRef();
    auto coordinate = op->getLoc()->findInstanceOf<FileLineColLoc>();
    StringRef filename =
        coordinate ? coordinate.getFilename().getValue() : StringRef();
    if (operation.size() > 1024 || filename.size() > 4096) {
      exceeded = true;
      reason = "source_member_text_budget_exceeded";
      return;
    }
    uint64_t estimate = 256 + escapedSize(operation) + escapedSize(filename);
    if (estimate >
        4 * 1024 * 1024 - std::min<uint64_t>(detailBytes, 4 * 1024 * 1024)) {
      exceeded = true;
      reason = "source_member_text_budget_exceeded";
      return;
    }
    detailBytes += estimate;
    auto opId = op->getAttrOfType<IntegerAttr>("flagtree.debug.op_id");
    auto scope = op->getAttrOfType<IntegerAttr>("flagtree.debug.scope_id");
    auto validId = [](IntegerAttr value) -> int64_t {
      if (!value || value.getValue().getActiveBits() > 31 ||
          value.getValue().isNegative())
        return 0;
      return value.getInt();
    };
    llvm::json::Object item{{"operation_index", found->second},
                            {"operation", operation.str()},
                            {"source_op_id", validId(opId)},
                            {"scope_id", validId(scope)}};
    // Extract one real file coordinate without recursively expanding a fused
    // location DAG. Additional original identities remain explicit members.
    if (coordinate) {
      item["file"] = filename.str();
      item["line"] = coordinate.getLine();
      item["column"] = coordinate.getColumn();
    }
    members.push_back(std::move(item));
  };
  if (site.end) {
    for (Operation *op = site.op->getNextNode(); op && op != site.end;
         op = op->getNextNode()) {
      if (exceeded)
        break;
      op->walk([&](Operation *member) {
        describe(member);
        return exceeded ? WalkResult::interrupt() : WalkResult::advance();
      });
    }
  } else {
    describe(site.op);
  }
  for (Operation *parent = site.op->getParentOp(); parent;
       parent = parent->getParentOp()) {
    if (++work > 100000) {
      exceeded = true;
      break;
    }
    StringRef name = parent->getName().getStringRef();
    if (name != "scf.for" && name != "scf.while" && name != "scf.if")
      continue;
    auto ref = original.find(parent);
    if (ref == original.end() || controls.size() >= 64) {
      exceeded = true;
      break;
    }
    if (detailBytes > 4 * 1024 * 1024 - 128) {
      exceeded = true;
      reason = "source_member_text_budget_exceeded";
      break;
    }
    detailBytes += 128;
    controls.push_back(llvm::json::Object{{"operation_index", ref->second},
                                          {"operation", name.str()}});
  }
  return llvm::json::Object{
      {"schema_version", 1},
      {"status",
       exceeded ? "unverified" : "original_execution_members_indexed"},
      {"reason", exceeded ? reason : StringRef()},
      {"members", std::move(members)},
      {"enclosing_controls", std::move(controls)},
      {"source_exclusive_cost_qualified", false}};
}

struct Recorder {
  OpBuilder b;
  Location loc;
  Value ring, cursor, selected, program, physical;
  uint32_t capacity;

  Value i32(uint32_t value) {
    return b.create<arith::ConstantIntOp>(loc, value, 32);
  }
  Value index(int64_t value) {
    return b.create<arith::ConstantIndexOp>(loc, value);
  }
  Value as32(Value value) {
    if (value.getType().isIndex())
      return b.create<arith::IndexCastOp>(loc, b.getI32Type(), value);
    return value;
  }
  SmallVector<Value, 2> split(Value value) {
    if (value.getType().isIndex())
      value = b.create<arith::IndexCastOp>(loc, b.getI64Type(), value);
    Value low = b.create<LLVM::TruncOp>(loc, b.getI32Type(), value);
    Value shift = b.create<LLVM::ConstantOp>(loc, b.getI64Type(),
                                             b.getI64IntegerAttr(32));
    Value high = b.create<LLVM::LShrOp>(loc, value, shift);
    return {low, b.create<LLVM::TruncOp>(loc, b.getI32Type(), high)};
  }
  SmallVector<Value, 3> clock(uint32_t site, bool atEnd) {
    auto clockLoc = FileLineColLoc::get(
        b.getContext(), "__flagprism_gcu_clock_v1__", site, atEnd ? 2 : 1);
    auto identityLoc = FileLineColLoc::get(
        b.getContext(), "__flagprism_gcu_clock_v1__", site, atEnd ? 4 : 3);
    auto read = b.create<scf::IfOp>(
        loc, TypeRange{b.getI32Type(), b.getI32Type(), b.getI32Type()},
        selected, true);
    OpBuilder::InsertionGuard insertion(b);
    b.setInsertionPointToStart(read.thenBlock());
    Value value =
        b.create<LLVM::CallOp>(clockLoc, TypeRange{b.getI64Type()},
                               "_ZN4tops12global_timerEv", ValueRange{})
            ->getResult(0);
    auto words = split(value);
    Value identity =
        b.create<LLVM::CallOp>(identityLoc, TypeRange{b.getI32Type()},
                               "flagprism_gcu_clock_identity_v1", ValueRange{})
            ->getResult(0);
    b.create<scf::YieldOp>(loc, ValueRange{words[0], words[1], identity});
    b.setInsertionPointToStart(read.elseBlock());
    Value zero = i32(0);
    b.create<scf::YieldOp>(loc, ValueRange{zero, zero, zero});
    return {read->getResult(0), read->getResult(1), read->getResult(2)};
  }
  SmallVector<Value, 2> pointer(Value memref, bool includeOffset) {
    if (!memref)
      return {i32(0), i32(0)};
    auto element = cast<MemRefType>(memref.getType()).getElementType();
    if (!element.isIntOrFloat() || element.getIntOrFloatBitWidth() % 8)
      return {i32(0), i32(0)};
    // Private tag storage becomes !gcu.dte during SDK lowering. Extract its
    // index-sized local identity without creating a typed base-buffer result
    // that would incorrectly retain the original i32 element type.
    if (!includeOffset)
      return split(
          b.create<memref::ExtractAlignedPointerAsIndexOp>(loc, memref));
    // GCU300 has 32-bit index but wider global pointers. Routing a pointer
    // through index silently truncates it (and index_cast sign-extends it).
    // Use the SDK's actual 64-bit pointer conversion on the zero-offset base,
    // then add the descriptor offset without narrowing the pointer itself.
    auto metadata = b.create<memref::ExtractStridedMetadataOp>(loc, memref);
    Type pointerType =
        parseType("!gcu.ptr<" + printed(element) + ">", b.getContext());
    OperationState toPointer(loc, "gcu.memref2ptr");
    toPointer.addOperands(metadata.getBaseBuffer());
    toPointer.addTypes(pointerType);
    Value pointer = b.create(toPointer)->getResult(0);
    OperationState toInteger(loc, "gcu.ptr2int");
    toInteger.addOperands(pointer);
    toInteger.addTypes(b.getI64Type());
    Value base = b.create(toInteger)->getResult(0);
    if (includeOffset) {
      auto type = cast<MemRefType>(memref.getType());
      unsigned bytes = type.getElementType().getIntOrFloatBitWidth() / 8;
      Value offset = b.create<arith::IndexCastOp>(loc, b.getI64Type(),
                                                  metadata.getOffset());
      offset = b.create<arith::MulIOp>(
          loc, offset, b.create<arith::ConstantIntOp>(loc, bytes, 64));
      base = b.create<arith::AddIOp>(loc, base, offset);
    }
    return split(base);
  }
  void store(Value offset, Value value) {
    b.create<memref::StoreOp>(loc, value, ring, ValueRange{offset});
  }
  void field(Value base, uint32_t field, Value value) {
    store(b.create<arith::AddIOp>(loc, base, index(field)), value);
  }
  Value space(Value value) {
    if (!value)
      return i32(0xffffffff);
    auto type = cast<MemRefType>(value.getType());
    auto element = type.getElementType();
    if (!element.isIntOrFloat() || element.getIntOrFloatBitWidth() % 8)
      return i32(0xffffffff);
    Attribute space = type.getMemorySpace();
    if (!space)
      return i32(0);
    if (auto integer = dyn_cast<IntegerAttr>(space))
      return integer.getValue().getActiveBits() <= 32
                 ? i32(static_cast<uint32_t>(integer.getValue().getZExtValue()))
                 : i32(0xffffffff);
    return i32(0xffffffff);
  }
  // No DMA, global load/store, wait or barrier is emitted here. Local writes
  // retain the observation until a single publication at the original return.
  void record(const Site &site, Value beginLow, Value beginHigh,
              Value beginIdentity, Value endLow, Value endHigh,
              Value endIdentity) {
    auto guard = b.create<scf::IfOp>(loc, selected, false);
    OpBuilder::InsertionGuard insertion(b);
    b.setInsertionPointToStart(guard.thenBlock());
    Value sequence =
        b.create<memref::LoadOp>(loc, cursor, ValueRange{index(0)});
    Value saturated = b.create<arith::CmpIOp>(loc, arith::CmpIPredicate::eq,
                                              sequence, i32(0x7fffffff));
    Value next = b.create<arith::SelectOp>(
        loc, saturated, sequence,
        b.create<arith::AddIOp>(loc, sequence, i32(1)));
    b.create<memref::StoreOp>(loc, next, cursor, ValueRange{index(0)});
    Value room = b.create<arith::CmpIOp>(loc, arith::CmpIPredicate::ult,
                                         sequence, i32(capacity));
    auto retain = b.create<scf::IfOp>(loc, room, false);
    b.setInsertionPointToStart(retain.thenBlock());
    Value ordinal =
        b.create<arith::IndexCastOp>(loc, b.getIndexType(), sequence);
    Value base = b.create<arith::AddIOp>(
        loc, b.create<arith::MulIOp>(loc, ordinal, index(Words)), index(8));
    SmallVector<Value> words(Words, i32(0));
    words[0] = i32(Magic);
    words[1] = i32(site.id);
    words[2] = sequence;
    words[3] = i32(site.kind);
    words[4] = beginLow;
    words[5] = beginHigh;
    words[6] = endLow;
    words[7] = endHigh;
    words[8] = endIdentity;
    words[18] = beginIdentity;
    words[19] = endIdentity;
    words[9] = site.queueIndex ? as32(site.queueIndex) : i32(0xffffffff);
    auto queue = pointer(site.queue, false);
    words[10] = queue[0];
    words[11] = queue[1];
    auto destination = pointer(site.destination, true);
    words[12] = destination[0];
    words[13] = destination[1];
    auto source = pointer(site.source, true);
    words[14] = source[0];
    words[15] = source[1];
    auto secondary = pointer(site.secondarySource, true);
    words[16] = secondary[0];
    words[17] = secondary[1];
    words[20] = space(site.destination);
    words[21] = space(site.source);
    words[22] = space(site.secondarySource);
    words[23] = space(site.thirdSource);
    auto third = pointer(site.thirdSource, true);
    words[28] = third[0];
    words[29] = third[1];
    words[24] = i32(0);
    words[25] = as32(program);
    words[26] = i32(3);
    words[30] = i32(SealLow);
    words[31] = i32(SealHigh);
    for (unsigned field = 0; field < Words; ++field)
      this->field(base, field, words[field]);
  }
};
} // namespace

llvm::Expected<std::string> indexGcuExecutionOrigins(StringRef input,
                                                     uint32_t maxRegions) {
  if (input.size() > 16 * 1024 * 1024 || maxRegions > 128)
    return error("GCU origin input/region budget exceeded");
  DialectRegistry registry;
  registry.insert<arith::ArithDialect, func::FuncDialect, gpu::GPUDialect,
                  LLVM::LLVMDialect, memref::MemRefDialect, scf::SCFDialect,
                  vector::VectorDialect>();
  MLIRContext context(registry);
  context.allowUnregisteredDialects();
  context.loadAllAvailableDialects();
  auto module = parseSourceString<ModuleOp>(input, &context);
  if (!module || (*module)->hasAttr("flagprism.gcu_execution_timeline_version"))
    return error("GCU origins require original, uninstrumented execution IR");
  SmallVector<func::FuncOp> functions;
  llvm::DenseMap<Operation *, uint32_t> original;
  module->walk([&](Operation *op) { original[op] = original.size(); });
  if (original.size() > 100000)
    return error("GCU origin operation budget exceeded");
  module->walk([&](func::FuncOp function) {
    if (!function.isExternal())
      functions.push_back(function);
  });
  if (functions.size() != 1)
    return error("GCU origins require one inlined execution function");
  SmallVector<Site> sites;
  llvm::json::Array unknown, unselected;
  uint32_t selected = 0, work = 0;
  uint64_t detailBytes = 0;
  collectSites(functions.front(), maxRegions, sites, unknown, unselected,
               selected);
  if (sites.empty() || sites.size() > 512)
    return error("GCU origin site budget exceeded");
  llvm::json::Array descriptors;
  for (const Site &site : sites)
    descriptors.push_back(llvm::json::Object{
        {"id", site.id},
        {"kind", static_cast<uint32_t>(site.kind)},
        {"operation", site.op->getName().getStringRef().str()},
        {"location", printed(site.op->getLoc())},
        {"source_membership",
         sourceMembership(site, original, work, detailBytes)}});
  llvm::json::Object report{{"schema_version", 1},
                            {"status", "original_execution_sites_indexed"},
                            {"selected_source_regions", selected},
                            {"sites", std::move(descriptors)},
                            {"native_schedule_qualified", false},
                            {"source_exclusive_cost_qualified", false}};
  std::string output =
      llvm::formatv("{0}", llvm::json::Value(std::move(report))).str();
  if (output.size() > 8 * 1024 * 1024)
    return error("GCU origin output budget exceeded");
  return output;
}

llvm::Expected<GcuExecutionRewrite>
rewriteGcuExecutionTimeline(StringRef input, uint32_t hiddenArgument,
                            uint32_t capacity, uint32_t maxRegions) {
  if (!maxRegions || maxRegions > 128)
    return error("GCU source-region budget must be in [1,128]");
  if (input.size() > 16 * 1024 * 1024 || !capacity || capacity > 4096)
    return error("GCU execution input/capacity exceeds its budget");
  DialectRegistry registry;
  registry.insert<arith::ArithDialect, func::FuncDialect, gpu::GPUDialect,
                  LLVM::LLVMDialect, memref::MemRefDialect, scf::SCFDialect,
                  vector::VectorDialect>();
  MLIRContext context(registry);
  context.allowUnregisteredDialects();
  context.loadAllAvailableDialects();
  auto module = parseSourceString<ModuleOp>(input, &context);
  if (!module)
    return error("Cannot parse actual generic GCU execution IR");
  if ((*module)->hasAttr("flagprism.gcu_execution_timeline_version"))
    return error("GCU execution IR is already instrumented");
  OwningOpRef<ModuleOp> originalModule = cast<ModuleOp>((*module)->clone());
  SmallVector<Operation *> originalOperations;
  module->walk([&](Operation *op) { originalOperations.push_back(op); });
  (*module)->setAttr("flagprism.gcu_execution_timeline_version",
                     IntegerAttr::get(IntegerType::get(&context, 32), 1));
  SmallVector<func::FuncOp> functions;
  module->walk([&](func::FuncOp f) {
    if (!f.isExternal())
      functions.push_back(f);
  });
  if (functions.size() != 1)
    return error("GCU late recorder requires one inlined execution function");
  func::FuncOp function = functions.front();
  if (hiddenArgument >= function.getNumArguments() ||
      hiddenArgument != function.getNumArguments() - 1 ||
      printed(function.getArgument(hiddenArgument).getType()) !=
          "!gcu.ptr<i32>")
    return error("GCU late recorder hidden argument identity/type mismatch");
  SmallVector<Site> sites;
  llvm::json::Array unknown, unselectedRegions;
  uint32_t selectedRegions = 0;
  collectSites(function, maxRegions, sites, unknown, unselectedRegions,
               selectedRegions);
  if (sites.empty() || sites.size() > 512)
    return error("GCU late recorder has no observable execution sites or "
                 "exceeds site budget");
  Location loc = function.getLoc();
  Recorder r{OpBuilder(&context), loc, {}, {}, {}, {}, {}, capacity};
  r.b.setInsertionPointToStart(&function.front());
  auto localType =
      MemRefType::get({8 + int64_t(capacity) * Words}, r.b.getI32Type());
  r.ring = r.b.create<memref::AllocOp>(loc, localType);
  r.cursor =
      r.b.create<memref::AllocOp>(loc, MemRefType::get({1}, r.b.getI32Type()));
  r.b.create<memref::StoreOp>(loc, r.i32(0), r.cursor, ValueRange{r.index(0)});
  auto x = r.b.create<gpu::BlockIdOp>(loc, gpu::Dimension::x);
  auto y = r.b.create<gpu::BlockIdOp>(loc, gpu::Dimension::y);
  auto z = r.b.create<gpu::BlockIdOp>(loc, gpu::Dimension::z);
  auto gx = r.b.create<gpu::GridDimOp>(loc, gpu::Dimension::x);
  auto gy = r.b.create<gpu::GridDimOp>(loc, gpu::Dimension::y);
  auto gz = r.b.create<gpu::GridDimOp>(loc, gpu::Dimension::z);
  Value xy = r.b.create<arith::MulIOp>(loc, gx, gy);
  r.program = r.b.create<arith::AddIOp>(
      loc, x,
      r.b.create<arith::AddIOp>(loc, r.b.create<arith::MulIOp>(loc, y, gx),
                                r.b.create<arith::MulIOp>(loc, z, xy)));
  Value last = r.b.create<arith::SubIOp>(
      loc, r.b.create<arith::MulIOp>(loc, xy, gz), r.index(1));
  Value firstProgram = r.b.create<arith::CmpIOp>(loc, arith::CmpIPredicate::eq,
                                                 r.program, r.index(0));
  Value lastProgram =
      r.b.create<arith::CmpIOp>(loc, arith::CmpIPredicate::eq, r.program, last);
  Value actor = r.b.create<gpu::ThreadIdOp>(loc, gpu::Dimension::x);
  Value actorZero = r.b.create<arith::CmpIOp>(loc, arith::CmpIPredicate::eq,
                                              actor, r.index(0));
  r.selected = r.b.create<arith::AndIOp>(
      loc, actorZero, r.b.create<arith::OrIOp>(loc, firstProgram, lastProgram));
  // Declarations live beside the func in the same GPU symbol table.
  {
    OpBuilder::InsertionGuard insertion(r.b);
    r.b.setInsertionPoint(function);
    for (auto [name, type] :
         {std::pair<StringRef, Type>{"_ZN4tops12global_timerEv",
                                     r.b.getI64Type()},
          {"flagprism_gcu_clock_identity_v1", r.b.getI32Type()}}) {
      Operation *existing =
          SymbolTable::lookupSymbolIn(function->getParentOp(), name);
      if (existing) {
        auto declaration = dyn_cast<LLVM::LLVMFuncOp>(existing);
        if (!declaration || !declaration.isExternal() ||
            declaration.getFunctionType().isVarArg() ||
            !declaration.getFunctionType().getParams().empty() ||
            declaration.getFunctionType().getReturnType() != type)
          return error("GCU reserved clock declaration has an incompatible "
                       "definition or signature");
      } else
        r.b.create<LLVM::LLVMFuncOp>(loc, name,
                                     LLVM::LLVMFunctionType::get(type, {}));
    }
  }
  llvm::DenseMap<Operation *, uint32_t> originalIndices;
  for (auto [number, operation] : llvm::enumerate(originalOperations))
    originalIndices[operation] = number;
  uint32_t originWork = 0;
  uint64_t originBytes = 0;
  SmallVector<llvm::json::Object> memberships;
  for (const Site &site : sites)
    memberships.push_back(
        sourceMembership(site, originalIndices, originWork, originBytes));
  size_t sourceIndex = 0;
  llvm::json::Array descriptors;
  for (const Site &site : sites) {
    auto membership = std::move(memberships[sourceIndex++]);
    r.loc = site.op->getLoc();
    r.b.setInsertionPoint(site.op);
    auto begin = r.clock(site.id, false);
    r.b.setInsertionPointAfter(site.end ? site.end : site.op);
    auto end = r.clock(site.id, true);
    r.record(site, begin[0], begin[1], begin[2], end[0], end[1], end[2]);
    descriptors.push_back(llvm::json::Object{
        {"id", site.id},
        {"operation", site.op->getName().getStringRef().str()},
        {"kind", static_cast<uint32_t>(site.kind)},
        {"location", printed(site.op->getLoc())},
        {"source_membership", std::move(membership)},
        {"native_clock_marker",
         llvm::json::Object{{"file", "__flagprism_gcu_clock_v1__"},
                            {"line", site.id},
                            {"begin_column", 1},
                            {"end_column", 2},
                            {"begin_identity_column", 3},
                            {"end_identity_column", 4}}},
        {"buffer_operand_count",
         site.kind == Compute ? site.op->getNumOperands() : 0},
        {"captured_compute_buffer_operands",
         site.kind == Compute ? std::min<unsigned>(4, site.op->getNumOperands())
                              : 0},
        {"engine_busy_verified", false},
        {"source_cost_verified", false}});
  }
  SmallVector<func::ReturnOp> returns;
  function.walk([&](func::ReturnOp op) { returns.push_back(op); });
  for (auto ret : returns) {
    r.loc = ret.getLoc();
    r.b.setInsertionPoint(ret);
    auto publish = r.b.create<scf::IfOp>(r.loc, r.selected, false);
    OpBuilder::InsertionGuard insertion(r.b);
    r.b.setInsertionPointToStart(publish.thenBlock());
    Value attempted =
        r.b.create<memref::LoadOp>(r.loc, r.cursor, ValueRange{r.index(0)});
    Value saturated = r.b.create<arith::CmpIOp>(r.loc, arith::CmpIPredicate::eq,
                                                attempted, r.i32(0x7fffffff));
    Value flags =
        r.b.create<arith::SelectOp>(r.loc, saturated, r.i32(0x30), r.i32(0x20));
    Value written =
        r.b.create<arith::MinUIOp>(r.loc, attempted, r.i32(capacity));
    Value dropped = r.b.create<arith::SubIOp>(r.loc, attempted, written);
    // Every retained word is assigned before this single post-user publication.
    // Unretained capacity bytes are initialized, so no private data leaks.
    Value firstUnused = r.b.create<arith::AddIOp>(
        r.loc,
        r.b.create<arith::MulIOp>(
            r.loc,
            r.b.create<arith::IndexCastOp>(r.loc, r.b.getIndexType(), written),
            r.index(Words)),
        r.index(8));
    auto clear = r.b.create<scf::ForOp>(
        r.loc, firstUnused, r.index(8 + capacity * Words), r.index(1));
    {
      OpBuilder::InsertionGuard inner(r.b);
      r.b.setInsertionPointToStart(clear.getBody());
      r.store(clear.getInductionVar(), r.i32(0));
    }
    SmallVector<Value> header{
        written,   r.i32(capacity),  dropped,
        flags,     r.i32(Words * 4), r.i32(32 + capacity * Words * 4),
        attempted, r.as32(r.program)};
    for (unsigned i = 0; i < header.size(); ++i)
      r.store(r.index(i), header[i]);
    Value slot = r.b.create<arith::SelectOp>(r.loc, firstProgram, r.index(0),
                                             r.index(8 + capacity * Words));
    OperationState conversion(r.loc, "gcu.ptr2memref");
    conversion.addOperands(function.getArgument(hiddenArgument));
    conversion.addTypes(
        MemRefType::get({ShapedType::kDynamic}, r.b.getI32Type()));
    Value output = r.b.create(conversion)->getResult(0);
    auto tag = r.b.create<memref::AllocOp>(
        r.loc, MemRefType::get({1}, r.b.getI32Type()));
    tag->setAttr("gcu_private_tag", r.b.getUnitAttr());
    r.b.create<memref::DmaStartOp>(
        r.loc, r.ring, ValueRange{r.index(0)}, output, ValueRange{slot},
        r.index(8 + capacity * Words), tag, ValueRange{r.index(0)});
    r.b.create<memref::DmaWaitOp>(r.loc, tag, ValueRange{r.index(0)},
                                  r.index(8 + capacity * Words));
    r.b.create<memref::DeallocOp>(r.loc, tag);
  }
  for (auto ret : returns) {
    r.b.setInsertionPoint(ret);
    r.b.create<memref::DeallocOp>(ret.getLoc(), r.cursor);
    r.b.create<memref::DeallocOp>(ret.getLoc(), r.ring);
  }
  if (failed(verify(*module)))
    return error("GCU execution recorder generated invalid IR");
  GcuExecutionRewrite result;
  llvm::raw_string_ostream stream(result.ir);
  module->print(stream,
                OpPrintingFlags().printGenericOpForm().enableDebugInfo());
  stream.flush();
  auto checked = checkGcuObserverTransformation(
      *originalModule, *module, originalOperations, hiddenArgument);
  if (!checked)
    return checked.takeError();
  auto preservation = llvm::json::parse(*checked);
  if (!preservation)
    return preservation.takeError();
  llvm::json::Object manifest{
      {"schema_version", 1},
      {"record_layout", "gcu_execution_timeline_v3"},
      {"hidden_argument_index", hiddenArgument},
      {"record_size", Words * 4},
      {"buffer_arguments_version", 2},
      {"buffer_address_encoding", "gcu_ptr2int_i64_v1"},
      {"queue_address_encoding", "sdk_private_tag_index"},
      {"selected_source_regions", selectedRegions},
      {"unselected_source_regions", std::move(unselectedRegions)},
      {"capacity", capacity},
      {"slot_bytes", 32 + capacity * Words * 4},
      {"observer", "work_item_0_first_last_program"},
      {"publication",
       "local_scalar_records_then_private_tag_DMA_at_original_return"},
      {"user_program_preservation", std::move(*preservation)},
      {"sites", std::move(descriptors)},
      {"unobserved_primitives", std::move(unknown)},
      {"physical_epoch_verified", false},
      {"engine_busy_verified", false}};
  result.manifest =
      llvm::formatv("{0:2}", llvm::json::Value(std::move(manifest))).str();
  return result;
}
} // namespace mlir::flagtree::debugger
