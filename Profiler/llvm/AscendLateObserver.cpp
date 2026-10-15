// An actual upstream LLVM15 pass applied by the compiler driver adapter.
// Capture post-actor lowering evidence before forwarding IR to the SDK.
#include "llvm/ADT/SmallPtrSet.h"
#include "llvm/ADT/StringExtras.h"
#include "llvm/Analysis/LoopInfo.h"
#include "llvm/IR/DebugInfoMetadata.h"
#include "llvm/IR/Dominators.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/InlineAsm.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/PassManager.h"
#include "llvm/Passes/PassBuilder.h"
#include "llvm/Passes/PassPlugin.h"
#include "llvm/Support/FileSystem.h"
#include "llvm/Support/Format.h"
#include "llvm/Support/FormatVariadic.h"
#include "llvm/Support/JSON.h"
#include "llvm/Support/MemoryBuffer.h"
#include "llvm/Support/Path.h"
#include "llvm/Support/SHA256.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"
#include <algorithm>
#include <cstdlib>
#include <functional>
#include <optional>
#include <set>
#include <tuple>

using namespace llvm;
namespace {
std::string printValue(const Value &value) {
  std::string output;
  raw_string_ostream stream(output);
  value.printAsOperand(stream, false);
  return output;
}
std::string digest(StringRef text) {
  const auto hash = SHA256::hash(arrayRefFromStringRef(text));
  return toHex(hash, true);
}
std::string environment(const char *name) {
  const char *value = std::getenv(name);
  return value ? value : "";
}
// Versioned per-actor event log: each actor segment has 4 header words
// (version, committed cursor, attempted, dropped), followed by capacity*8
// record words. Program selection is fixed per compilation; callers allocate
// distinct buffers per invocation. An actor exclusively writes its segment.
static void appendRecord(Instruction *position, Value *pointer, Value *program,
                         Value *actor, Value *start, Value *end,
                         uint64_t capacity, uint64_t site, uint64_t semantic) {
  LLVMContext &context = position->getContext();
  IRBuilder<> builder(position);
  Type *i64 = builder.getInt64Ty();
  Value *base = builder.CreateMul(actor, builder.getInt64(4 + capacity * 8));
  auto address = [&](IRBuilder<> &b, Value *offset) {
    return b.CreateGEP(i64, pointer, offset);
  };
  Value *cursorAddress =
      address(builder, builder.CreateAdd(base, builder.getInt64(1)));
  Value *attemptAddress =
      address(builder, builder.CreateAdd(base, builder.getInt64(2)));
  Value *dropAddress =
      address(builder, builder.CreateAdd(base, builder.getInt64(3)));
  auto *attempt = builder.CreateLoad(i64, attemptAddress);
  attempt->setVolatile(true);
  auto *attemptStore = builder.CreateStore(
      builder.CreateAdd(attempt, builder.getInt64(1)), attemptAddress);
  attemptStore->setVolatile(true);
  auto *cursor = builder.CreateLoad(i64, cursorAddress);
  cursor->setVolatile(true);
  Instruction *thenTerminator = nullptr;
  Instruction *elseTerminator = nullptr;
  SplitBlockAndInsertIfThenElse(
      builder.CreateICmpULT(cursor, builder.getInt64(capacity)), position,
      &thenTerminator, &elseTerminator);
  IRBuilder<> success(thenTerminator);
  Value *offset = success.CreateAdd(
      base, success.CreateAdd(success.getInt64(4),
                              success.CreateMul(cursor, success.getInt64(8))));
  Value *values[] = {success.getInt64(site | (semantic << 32)),
                     attempt,
                     start,
                     end,
                     program,
                     actor,
                     success.getInt64(UINT64_MAX),
                     success.getInt64(UINT64_MAX)};
  for (uint64_t word = 0; word < 8; ++word) {
    auto *store = success.CreateStore(
        values[word],
        address(success, success.CreateAdd(offset, success.getInt64(word))));
    store->setVolatile(true);
  }
  auto *version =
      success.CreateStore(success.getInt64(1), address(success, base));
  version->setVolatile(true);
  auto *commit = success.CreateStore(
      success.CreateAdd(cursor, success.getInt64(1)), cursorAddress);
  commit->setVolatile(true);
  IRBuilder<> overflow(elseTerminator);
  auto *dropped = overflow.CreateLoad(i64, dropAddress);
  dropped->setVolatile(true);
  auto *drop = overflow.CreateStore(
      overflow.CreateAdd(dropped, overflow.getInt64(1)), dropAddress);
  drop->setVolatile(true);
}
static Value *timestamp(IRBuilder<> &builder) {
  FunctionType *type = FunctionType::get(builder.getInt64Ty(), false);
  auto *clock = InlineAsm::get(type, "MOV $0, SYS_CNT", "=l", true);
  return builder.CreateCall(type, clock, {});
}
static void attachSourceOrigin(json::Object &site,
                               const Instruction &instruction) {
  if (MDNode *source = instruction.getMetadata("flagprism.source_op_id"))
    if (source->getNumOperands() && isa<MDString>(source->getOperand(0)))
      site["source_op_id"] = cast<MDString>(source->getOperand(0))->getString();
  if (const DebugLoc &location = instruction.getDebugLoc()) {
    SmallString<256> sourcePath(location->getDirectory());
    if (sys::path::is_absolute(location->getFilename()))
      sourcePath = location->getFilename();
    else
      sys::path::append(sourcePath, location->getFilename());
    site["source_file"] = sourcePath.str().str();
    site["line"] = static_cast<int64_t>(location.getLine());
    site["column"] = static_cast<int64_t>(location.getCol());
    site["debug_line"] = static_cast<int64_t>(location.getLine());
    site["debug_column"] = static_cast<int64_t>(location.getCol());
    site["debug_file"] = location->getFilename();
    site["debug_directory"] = location->getDirectory();
    json::Array chain;
    for (const DILocation *parent = location->getInlinedAt(); parent;
         parent = parent->getInlinedAt())
      chain.push_back(
          json::Object{{"file", parent->getFilename()},
                       {"directory", parent->getDirectory()},
                       {"line", static_cast<int64_t>(parent->getLine())},
                       {"column", static_cast<int64_t>(parent->getColumn())}});
    site["inline_chain"] = std::move(chain);
  }
}
static json::Object describeOperation(Instruction &instruction,
                                      uint64_t siteId) {
  const bool call = isa<CallInst>(instruction);
  const char *kind = call                          ? "compiler_call"
                     : isa<LoadInst>(instruction)  ? "load"
                     : isa<StoreInst>(instruction) ? "store"
                                                   : "compute";
  json::Object site{{"site_id", static_cast<int64_t>(siteId)},
                    {"semantics", "source_operation_checkpoint"},
                    {"public_semantic", "operation_checkpoint"},
                    {"operation_class", kind},
                    {"compiler_opcode", instruction.getOpcodeName()},
                    {"operation", instruction.getOpcodeName()},
                    {"source_op_id", nullptr}};
  if (call) {
    site["callee"] = cast<CallInst>(instruction).getCalledFunction()->getName();
    site["operation"] =
        cast<CallInst>(instruction).getCalledFunction()->getName();
  }
  attachSourceOrigin(site, instruction);
  return site;
}
static uint64_t selectedSemantics() {
  const std::string option = environment("FLAGPRISM_ASCEND_TRACE_SEMANTICS");
  if (option.empty())
    return 7;
  SmallVector<StringRef, 4> names;
  StringRef(option).split(names, ',', -1, false);
  uint64_t mask = 0;
  for (StringRef name : names) {
    uint64_t bit = name == "issue"                  ? 1
                   : name == "wait_bracket"         ? 2
                   : name == "control_checkpoint"   ? 4
                   : name == "operation_checkpoint" ? 8
                                                    : 0;
    if (!bit || (mask & bit))
      report_fatal_error(
          "FlagPrism trace semantics must be unique supported names");
    mask |= bit;
  }
  if (!mask)
    report_fatal_error(
        "FlagPrism trace semantics must be unique supported names");
  return mask;
}
static bool instrumentActor(Function &function, uint64_t argumentIndex,
                            uint64_t capacity, uint64_t selectedProgram,
                            StringRef actorKind, uint64_t semanticMask,
                            json::Array &sites, json::Object &operationPlan,
                            json::Object &controlPlan,
                            json::Object &runtimeActorBinding) {
  if (argumentIndex >= function.arg_size() ||
      !function.getArg(argumentIndex)->getType()->isPointerTy())
    report_fatal_error("FlagPrism trace argument must identify a "
                       "compiler-mapped pointer formal");
  auto *pointerType =
      cast<PointerType>(function.getArg(argumentIndex)->getType());
  if (pointerType->getAddressSpace() != 1)
    report_fatal_error(
        "FlagPrism trace argument must use global address space 1");
  SmallVector<CallInst *, 32> selected;
  for (BasicBlock &block : function)
    for (Instruction &instruction : block)
      if (auto *call = dyn_cast<CallInst>(&instruction))
        if (Function *callee = call->getCalledFunction()) {
          StringRef name = callee->getName();
          if (name == "llvm.hivm.WAIT.FLAG.IMM" ||
              name == "llvm.hivm.WAIT.FLAG.DEV.REG" ||
              name == "llvm.hivm.SET.CROSS.CORE" ||
              name == "llvm.hivm.SET.FLAG.IMM")
            selected.push_back(call);
        }
  // Snapshot original operations before adding the logger. Calls are compiler
  // operations regardless of their generated symbol; source origin is required
  // so allocation/ABI scaffolding without a user location is not presented as a
  // user operation. No operator or source-file allowlist is involved.
  SmallVector<Instruction *, 64> operationCandidates;
  for (BasicBlock &block : function) {
    std::set<std::tuple<const MDNode *, std::string>> regions;
    for (Instruction &instruction : block) {
      const DebugLoc &location = instruction.getDebugLoc();
      if (!location || !location.getLine())
        continue;
      std::string kind;
      if (auto *call = dyn_cast<CallInst>(&instruction)) {
        Function *callee = call->getCalledFunction();
        if (!callee || callee->isIntrinsic())
          continue;
        StringRef name = callee->getName();
        if (name.startswith("llvm.hivm.GET.") ||
            name.startswith("llvm.hivm.SET.") ||
            name.startswith("llvm.hivm.WAIT.") ||
            name.startswith("llvm.hivm.PIPE.") || name.startswith("llvm.dbg."))
          continue;
        kind = "compiler_call";
      } else if (isa<LoadInst>(instruction)) {
        kind = "load";
      } else if (isa<StoreInst>(instruction)) {
        kind = "store";
      } else if (isa<BinaryOperator>(instruction) ||
                 isa<UnaryOperator>(instruction)) {
        kind = "compute";
      } else {
        continue;
      }
      if (regions.emplace(location.get(), kind).second)
        operationCandidates.push_back(&instruction);
    }
  }
  uint64_t maxSites = 32;
  const std::string budget = environment("FLAGPRISM_ASCEND_TRACE_MAX_SITES");
  if (!budget.empty() && (StringRef(budget).getAsInteger(10, maxSites) ||
                          !maxSites || maxSites > 256))
    report_fatal_error("FlagPrism operation site budget must be 1..256");
  SmallVector<Instruction *, 64> operationSites;
  const uint64_t selectedCount =
      std::min<uint64_t>(maxSites, operationCandidates.size());
  for (uint64_t index = 0; index < selectedCount; ++index)
    operationSites.push_back(
        operationCandidates[selectedCount == 1
                                ? 0
                                : index * (operationCandidates.size() - 1) /
                                      (selectedCount - 1)]);
  DominatorTree dominance(function);
  LoopInfo loopInfo(dominance);
  struct OriginalLoopHeader {
    BasicBlock *header;
    Instruction *origin;
    std::string name;
    unsigned depth;
    SmallVector<std::string, 8> blocks;
  };
  SmallVector<OriginalLoopHeader, 16> loopHeaders;
  for (Loop *loop : loopInfo.getLoopsInPreorder()) {
    Instruction *origin = &*loop->getHeader()->getFirstInsertionPt();
    if (!origin->getDebugLoc())
      for (BasicBlock *block : loop->blocks()) {
        for (Instruction &instruction : *block)
          if (instruction.getDebugLoc()) {
            origin = &instruction;
            break;
          }
        if (origin->getDebugLoc())
          break;
      }
    OriginalLoopHeader candidate{loop->getHeader(),
                                 origin,
                                 printValue(*loop->getHeader()),
                                 loop->getLoopDepth(),
                                 {}};
    for (const BasicBlock *block : loop->blocks())
      candidate.blocks.push_back(printValue(*block));
    loopHeaders.push_back(std::move(candidate));
  }
  IRBuilder<> entry(&*function.getEntryBlock().getFirstInsertionPt());
  Type *i64 = entry.getInt64Ty();
  FunctionType *coordinateType = FunctionType::get(i64, false);
  auto blockFunction = function.getParent()->getOrInsertFunction(
      "llvm.hivm.GET.BLOCK.IDX", coordinateType);
  Value *program = entry.CreateCall(blockFunction, {});
  Value *actor = entry.getInt64(0);
  if (actorKind == "AIV") {
    auto subFunction = function.getParent()->getOrInsertFunction(
        "llvm.hivm.GET.SUBBLOCKID", coordinateType);
    actor =
        entry.CreateAdd(entry.CreateCall(subFunction, {}), entry.getInt64(1));
  } else if (actorKind != "AIC") {
    report_fatal_error(
        "FlagPrism trace needs an actual SDK cube/vector target");
  }
  json::Array slots;
  json::Object expression;
  if (actorKind == "AIC") {
    slots.push_back(0);
    expression = json::Object{{"kind", "constant_i64"}, {"value", 0}};
  } else {
    slots.push_back(1);
    slots.push_back(2);
    expression = json::Object{{"kind", "add_i64"},
                              {"call", "llvm.hivm.GET.SUBBLOCKID"},
                              {"constant", 1}};
  }
  runtimeActorBinding = json::Object{
      {"schema_version", 1},
      {"function", function.getName()},
      {"actor_kind", actorKind.str()},
      {"layout", "actor_header4_record8_v1"},
      {"segment_count", 3},
      {"segment_words", static_cast<int64_t>(4 + capacity * 8)},
      {"record_actor_word", 5},
      {"admissible_slots", std::move(slots)},
      {"expression", std::move(expression)},
      {"value_use", "same_emitted_i64_for_segment_offset_and_record_word5"},
      {"basis", "actual_emitted_logger_actor_value"}};
  uint64_t siteNumber = 0, selectedControls = 0;
  json::Array controlInventory;
  for (CallInst *call : selected) {
    const bool wait = call->getCalledFunction()->getName().contains("WAIT");
    const uint64_t siteId = siteNumber++;
    const bool enabled = semanticMask & (wait ? 2 : 1);
    auto describe = [&]() {
      json::Object site{
          {"site_id", static_cast<int64_t>(siteId)},
          {"callee", call->getCalledFunction()->getName()},
          {"operation", call->getCalledFunction()->getName()},
          {"operation_class", "existing_control_primitive"},
          {"public_semantic", wait ? "wait_bracket" : "issue"},
          {"semantics", wait ? "existing_readiness_wait_source_control"
                             : "signal_issue_source_control"},
          {"source_op_id", nullptr}};
      attachSourceOrigin(site, *call);
      return site;
    };
    json::Object item = describe();
    item["selected"] = enabled;
    item["selection_reason"] = enabled ? "requested_existing_control_primitive"
                                       : "semantic_not_requested";
    controlInventory.push_back(std::move(item));
    if (!enabled)
      continue;
    ++selectedControls;
    Instruction *after = call->getNextNode();
    IRBuilder<> beforeBuilder(call);
    Value *start = timestamp(beforeBuilder);
    IRBuilder<> afterBuilder(after);
    Value *end = timestamp(afterBuilder);
    // Only the chosen program touches global log memory. The timestamps are
    // source-control observations around the existing primitive, no new wait.
    auto *selectedTerminator = SplitBlockAndInsertIfThen(
        afterBuilder.CreateICmpEQ(program,
                                  afterBuilder.getInt64(selectedProgram)),
        after, false);
    appendRecord(selectedTerminator, function.getArg(argumentIndex), program,
                 actor, start, end, capacity, siteId, wait ? 2 : 1);
    sites.push_back(describe());
  }
  for (const auto &loopHeader : loopHeaders) {
    const uint64_t siteId = siteNumber++;
    const bool enabled = semanticMask & 4;
    BasicBlock *header = loopHeader.header;
    auto describe = [&]() {
      json::Array blocks;
      for (const std::string &block : loopHeader.blocks)
        blocks.push_back(block);
      json::Object site{{"site_id", static_cast<int64_t>(siteId)},
                        {"block", loopHeader.name},
                        {"block_representation",
                         "original_pre_instrumentation_canonical_llvm"},
                        {"loop_depth", static_cast<int64_t>(loopHeader.depth)},
                        {"loop_blocks", std::move(blocks)},
                        {"semantics", "loop_header_occurrence"},
                        {"public_semantic", "control_checkpoint"},
                        {"operation", "loop_header_occurrence"},
                        {"operation_class", "original_loop_header"},
                        {"iteration_identity", nullptr},
                        {"source_op_id", nullptr},
                        {"origin_semantics", "loop_header_control_checkpoint"}};
      attachSourceOrigin(site, *loopHeader.origin);
      return site;
    };
    json::Object site = describe();
    json::Object item = describe();
    item["selected"] = enabled;
    item["selection_reason"] = enabled ? "all_requested_original_loop_headers"
                                       : "semantic_not_requested";
    controlInventory.push_back(std::move(item));
    if (!enabled)
      continue;
    ++selectedControls;
    Instruction *position = &*header->getFirstInsertionPt();
    IRBuilder<> builder(position);
    Value *tick = timestamp(builder);
    auto *terminator = SplitBlockAndInsertIfThen(
        builder.CreateICmpEQ(program, builder.getInt64(selectedProgram)),
        position, false);
    appendRecord(terminator, function.getArg(argumentIndex), program, actor,
                 tick, tick, capacity, siteId, 3);
    sites.push_back(std::move(site));
  }
  controlPlan["plan_kind"] = "control";
  controlPlan["policy"] = "all_requested_original_control_sites";
  controlPlan["budget_scope"] = "existing_primitives_and_original_loop_headers";
  controlPlan["max_sites"] = nullptr;
  controlPlan["operation_max_sites_applies"] = false;
  controlPlan["record_capacity_per_actor"] = static_cast<int64_t>(capacity);
  controlPlan["candidate_count"] =
      static_cast<int64_t>(selected.size() + loopHeaders.size());
  controlPlan["selected_count"] = static_cast<int64_t>(selectedControls);
  controlPlan["inventory"] = std::move(controlInventory);
  if (semanticMask & 8) {
    json::Array inventory;
    for (uint64_t index = 0; index < operationCandidates.size(); ++index) {
      Instruction *candidate = operationCandidates[index];
      json::Object item = describeOperation(*candidate, siteNumber + index);
      const bool selected =
          std::find(operationSites.begin(), operationSites.end(), candidate) !=
          operationSites.end();
      item["selected"] = selected;
      item["selection_reason"] = selected
                                     ? "source_location_class_evenly_spaced"
                                     : "static_site_budget";
      inventory.push_back(std::move(item));
    }
    operationPlan["plan_kind"] = "operation";
    operationPlan["budget_scope"] = "source_operation_candidates_only";
    operationPlan["control_sites_included"] = false;
    operationPlan["policy"] =
        "source_location_class_per_original_block_evenly_spaced";
    operationPlan["max_sites"] = static_cast<int64_t>(maxSites);
    operationPlan["candidate_count"] =
        static_cast<int64_t>(operationCandidates.size());
    operationPlan["selected_count"] = static_cast<int64_t>(selectedCount);
    operationPlan["inventory"] = std::move(inventory);
    for (Instruction *position : operationSites) {
      const uint64_t siteId =
          siteNumber +
          std::distance(operationCandidates.begin(),
                        std::find(operationCandidates.begin(),
                                  operationCandidates.end(), position));
      json::Object site = describeOperation(*position, siteId);
      site["candidate_count"] =
          static_cast<int64_t>(operationCandidates.size());
      site["selected_count"] = static_cast<int64_t>(selectedCount);
      site["selection_policy"] =
          "source_location_class_per_original_block_evenly_spaced";
      IRBuilder<> builder(position);
      Value *tick = timestamp(builder);
      auto *terminator = SplitBlockAndInsertIfThen(
          builder.CreateICmpEQ(program, builder.getInt64(selectedProgram)),
          position, false);
      appendRecord(terminator, function.getArg(argumentIndex), program, actor,
                   tick, tick, capacity, siteId, 4);
      sites.push_back(std::move(site));
    }
  }
  return true; // Program/actor coordinate calls were added even for zero
               // selected sites.
}
class AscendLateObserver : public PassInfoMixin<AscendLateObserver> {
public:
  PreservedAnalyses run(Module &module, ModuleAnalysisManager &analysis) {
    const auto output = environment("FLAGPRISM_ASCEND_COMPILER_OUTPUT");
    if (output.empty())
      return PreservedAnalyses::all();
    NamedMDNode *annotations = module.getNamedMetadata("hivm.annotations");
    if (!annotations)
      return PreservedAnalyses::all();
    SmallPtrSet<Function *, 4> kernelEntries;
    for (MDNode *annotation : annotations->operands()) {
      if (annotation->getNumOperands() < 2)
        continue;
      auto *tag = dyn_cast<MDString>(annotation->getOperand(1));
      auto *metadata = dyn_cast<ValueAsMetadata>(annotation->getOperand(0));
      if (!tag || tag->getString() != "kernel" || !metadata)
        continue;
      auto *function = dyn_cast<Function>(metadata->getValue());
      if (function && !function->isDeclaration())
        kernelEntries.insert(function);
    }
    if (kernelEntries.size() > 1)
      report_fatal_error("FlagPrism actor module has multiple kernel entries; "
                         "actor/site identity is ambiguous");
    std::string ir;
    raw_string_ostream irStream(ir);
    module.print(irStream, nullptr);
    irStream.flush();
    const auto moduleHash = digest(ir);
    json::Array actors;
    json::Array dynamicSites;
    json::Object operationPlan, controlPlan, runtimeActorBinding;
    bool changed = false;
    SmallPtrSet<Function *, 4> processedEntries;
    auto &functions =
        analysis.getResult<FunctionAnalysisManagerModuleProxy>(module)
            .getManager();
    for (MDNode *annotation : annotations->operands()) {
      if (annotation->getNumOperands() < 2)
        continue;
      auto *tag = dyn_cast<MDString>(annotation->getOperand(1));
      auto *metadata = dyn_cast<ValueAsMetadata>(annotation->getOperand(0));
      if (!tag || tag->getString() != "kernel" || !metadata)
        continue;
      auto *function = dyn_cast<Function>(metadata->getValue());
      if (!function || function->isDeclaration())
        continue;
      if (!processedEntries.insert(function).second)
        continue;
      json::Array arguments, sites, loops;
      for (const Argument &argument : function->args()) {
        json::Object item{
            {"position", static_cast<int64_t>(argument.getArgNo())},
            {"ssa", printValue(argument)}};
        if (auto *pointer = dyn_cast<PointerType>(argument.getType()))
          item["address_space"] =
              static_cast<int64_t>(pointer->getAddressSpace());
        item["role"] = nullptr;
        arguments.push_back(std::move(item));
      }
      size_t siteNumber = 0;
      for (BasicBlock &block : *function) {
        for (Instruction &instruction : block) {
          auto *call = dyn_cast<CallBase>(&instruction);
          if (!call || !call->getCalledFunction())
            continue;
          StringRef callee = call->getCalledFunction()->getName();
          if (!callee.startswith("llvm.hivm."))
            continue;
          json::Array operands;
          for (const Use &operand : call->args())
            operands.push_back(printValue(*operand.get()));
          json::Object site{{"id", static_cast<int64_t>(siteNumber++)},
                            {"block", printValue(block)},
                            {"callee", callee},
                            {"operands", std::move(operands)},
                            {"source_op_id", nullptr}};
          if (MDNode *source =
                  instruction.getMetadata("flagprism.source_op_id"))
            if (source->getNumOperands() &&
                isa<MDString>(source->getOperand(0)))
              site["source_op_id"] =
                  cast<MDString>(source->getOperand(0))->getString();
          if (const DebugLoc &location = instruction.getDebugLoc()) {
            site["debug_line"] = static_cast<int64_t>(location.getLine());
            site["debug_column"] = static_cast<int64_t>(location.getCol());
            site["debug_file"] = location->getFilename();
            site["debug_directory"] = location->getDirectory();
            json::Array inlineChain;
            for (const DILocation *parent = location->getInlinedAt(); parent;
                 parent = parent->getInlinedAt())
              inlineChain.push_back(json::Object{
                  {"file", parent->getFilename()},
                  {"directory", parent->getDirectory()},
                  {"line", static_cast<int64_t>(parent->getLine())},
                  {"column", static_cast<int64_t>(parent->getColumn())}});
            site["inline_chain"] = std::move(inlineChain);
          }
          sites.push_back(std::move(site));
        }
      }
      const auto &loopInfo = functions.getResult<LoopAnalysis>(*function);
      std::function<void(const Loop *)> addLoop = [&](const Loop *loop) {
        json::Array blocks;
        for (const BasicBlock *block : loop->blocks())
          blocks.push_back(printValue(*block));
        loops.push_back(
            json::Object{{"header", printValue(*loop->getHeader())},
                         {"depth", static_cast<int64_t>(loop->getLoopDepth())},
                         {"blocks", std::move(blocks)},
                         {"dynamic_iterations", nullptr}});
        for (const Loop *nested : loop->getSubLoops())
          addLoop(nested);
      };
      for (const Loop *loop : loopInfo)
        addLoop(loop);
      std::optional<uint64_t> mappedTraceArgument;
      json::Array argumentRoles;
      const auto sourceAbiPath = environment("FLAGPRISM_ASCEND_SOURCE_ABI");
      if (!sourceAbiPath.empty()) {
        auto sourceBuffer = MemoryBuffer::getFile(sourceAbiPath);
        if (!sourceBuffer)
          report_fatal_error("FlagPrism cannot read compiler source ABI");
        auto sourceValue = json::parse((*sourceBuffer)->getBuffer());
        if (!sourceValue)
          report_fatal_error("FlagPrism compiler source ABI JSON is invalid");
        auto *sourceObject = sourceValue->getAsObject();
        auto *formals =
            sourceObject ? sourceObject->getArray("formals") : nullptr;
        if (!formals)
          report_fatal_error("FlagPrism compiler source ABI requires formals");
        std::optional<uint64_t> fftsArgument;
        for (BasicBlock &block : *function)
          for (Instruction &instruction : block)
            if (auto *call = dyn_cast<CallBase>(&instruction))
              if (Function *callee = call->getCalledFunction())
                if (callee->getName() == "llvm.hivm.SET.FFTS.BASE.ADDR" &&
                    call->arg_size() == 1)
                  if (auto *argument =
                          dyn_cast<Argument>(call->getArgOperand(0)))
                    fftsArgument = argument->getArgNo();
        const auto declaredFfts =
            sourceObject->getBoolean("ffts_control_present");
        if (!declaredFfts)
          report_fatal_error("FlagPrism source ABI requires actual runtime "
                             "FFTS configuration");
        const uint64_t prefix = *declaredFfts ? 1 : 0;
        if (prefix && (!function->arg_size() ||
                       !function->getArg(0)->getType()->isIntegerTy(64)))
          report_fatal_error("FlagPrism final FFTS control formal type does "
                             "not match runtime ABI");
        if (fftsArgument && !prefix)
          report_fatal_error(
              "FlagPrism LLVM FFTS use contradicts runtime launch ABI");
        size_t pointerPrefix = 0;
        for (size_t index = 0; index < formals->size(); ++index)
          if (auto *formal = (*formals)[index].getAsObject())
            if (formal->getString("kind") == StringRef("global_pointer"))
              pointerPrefix = index + 1;
        // CANN removes implicit program-coordinate scalar tail arguments.
        // Verify the complete prefix through the last global pointer; trailing
        // scalar/launch-coordinate mapping remains partial and unclaimed.
        if ((fftsArgument && *fftsArgument != 0) ||
            function->arg_size() < pointerPrefix + prefix)
          report_fatal_error("FlagPrism source/final pointer ABI relation is "
                             "unsupported or ambiguous");
        if (prefix)
          argumentRoles.push_back(json::Object{
              {"final_formal_index", 0},
              {"role", "ffts_control"},
              {"basis",
               "actual_runtime_launch_ABI_and_optional_FFTS_operand"}});
        for (size_t index = 0; index < pointerPrefix; ++index) {
          auto *formal = (*formals)[index].getAsObject();
          if (!formal)
            report_fatal_error("FlagPrism compiler formal is not an object");
          const auto kind = formal->getString("kind");
          if (!kind)
            report_fatal_error("FlagPrism source ABI formal kind is missing");
          Type *type = function->getArg(index + prefix)->getType();
          const bool pointerMatch =
              *kind == "global_pointer" && type->isPointerTy() &&
              cast<PointerType>(type)->getAddressSpace() == 1;
          bool scalarMatch = false;
          if (kind->startswith("i")) {
            unsigned width = 0;
            if (!kind->drop_front().getAsInteger(10, width))
              scalarMatch = type->isIntegerTy(width);
          } else if (*kind == "index") {
            scalarMatch = type->isIntegerTy(64);
          } else if (*kind == "f32") {
            scalarMatch = type->isFloatTy();
          } else if (*kind == "f64") {
            scalarMatch = type->isDoubleTy();
          }
          if (!pointerMatch && !scalarMatch) {
            std::string finalType;
            raw_string_ostream typeStream(finalType);
            type->print(typeStream);
            report_fatal_error(
                Twine("FlagPrism source/final formal types do not match at ") +
                Twine(index) + ": source=" + *kind + ", final=" + finalType);
          }
          json::Object role{
              {"source_formal_index", static_cast<int64_t>(index)},
              {"final_formal_index", static_cast<int64_t>(index + prefix)},
              {"basis", "compiler_signature_verified_bare_pointer_prefix_abi"},
              {"role", nullptr}};
          if (auto name = formal->getString("role")) {
            role["role"] = name->str();
            if (*name == "dynamic_trace")
              mappedTraceArgument = index + prefix;
          }
          if (auto sourceIndex = formal->getInteger("source_argument_index"))
            role["source_argument_index"] = *sourceIndex;
          argumentRoles.push_back(std::move(role));
        }
      }
      const auto traceArgument =
          mappedTraceArgument
              ? std::to_string(*mappedTraceArgument)
              : environment("FLAGPRISM_ASCEND_TRACE_ARGUMENT_INDEX");
      if (!traceArgument.empty()) {
        uint64_t argumentIndex = 0, capacity = 0, selectedProgram = 0;
        if (StringRef(traceArgument).getAsInteger(10, argumentIndex) ||
            StringRef(environment("FLAGPRISM_ASCEND_TRACE_CAPACITY"))
                .getAsInteger(10, capacity) ||
            !capacity || capacity > 1'000'000)
          report_fatal_error("FlagPrism trace argument/capacity must be "
                             "explicit positive integers");
        const auto programOption =
            environment("FLAGPRISM_ASCEND_TRACE_PROGRAM");
        if (!programOption.empty() &&
            StringRef(programOption).getAsInteger(10, selectedProgram))
          report_fatal_error("FlagPrism selected program must be an integer");
        changed |= instrumentActor(
            *function, argumentIndex, capacity, selectedProgram,
            environment("FLAGPRISM_ASCEND_ACTOR_KIND"), selectedSemantics(),
            dynamicSites, operationPlan, controlPlan, runtimeActorBinding);
      }
      const auto targetCpu =
          function->getFnAttribute("target-cpu").getValueAsString();
      actors.push_back(json::Object{
          {"dynamic_observation_prepared", !traceArgument.empty()},
          {"argument_roles", std::move(argumentRoles)},
          {"function", function->getName()},
          {"target_cpu", targetCpu},
          {"actor_kind", environment("FLAGPRISM_ASCEND_ACTOR_KIND")},
          {"arguments", std::move(arguments)},
          {"sites", std::move(sites)},
          {"loops", std::move(loops)}});
    }
    if (actors.empty())
      return PreservedAnalyses::all();
    std::error_code error = sys::fs::create_directories(output);
    if (error)
      report_fatal_error(
          Twine("FlagPrism cannot create compiler artifact output: ") +
          error.message());
    SmallString<256> base(output);
    sys::path::append(base, moduleHash);
    std::error_code fileError;
    raw_fd_ostream llvmFile((base + ".ll").str(), fileError, sys::fs::OF_None);
    if (fileError)
      report_fatal_error("FlagPrism cannot retain final actor LLVM");
    llvmFile << ir;
    llvmFile.close();
    json::Array effectiveSemantics;
    const uint64_t semanticMask = selectedSemantics();
    if (semanticMask & 1)
      effectiveSemantics.push_back("issue");
    if (semanticMask & 2)
      effectiveSemantics.push_back("wait_bracket");
    if (semanticMask & 4)
      effectiveSemantics.push_back("control_checkpoint");
    if (semanticMask & 8)
      effectiveSemantics.push_back("operation_checkpoint");
    if (!runtimeActorBinding.empty()) {
      runtimeActorBinding["module_sha256"] = moduleHash;
      runtimeActorBinding["compile_id"] =
          environment("FLAGPRISM_ASCEND_COMPILE_ID");
    }
    json::Object manifest{
        {"effective_semantics", std::move(effectiveSemantics)},
        {"semantic_selection_stage",
         "compile_time_before_timestamp_and_record"},
        {"dynamic_clock", json::Object{{"domain", "ascend.SYS_CNT"},
                                       {"scope", "actor_local"},
                                       {"unit", "ticks"},
                                       {"tick_ns", nullptr},
                                       {"alignment", "unverified"}}},
        {"dynamic_record_layout", "actor_header4_record8_v1"},
        {"dynamic_sites", std::move(dynamicSites)},
        {"runtime_actor_binding", std::move(runtimeActorBinding)},
        {"operation_plan", std::move(operationPlan)},
        {"control_plan", std::move(controlPlan)},
        {"observation_plan_version", 2},
        {"instrumented", changed},
        {"schema_version", 1},
        {"backend", "ascend"},
        {"phase", "post_actor_lowering_pre_scalar_optimization"},
        {"module_sha256", moduleHash},
        {"module_identifier", module.getModuleIdentifier()},
        {"target_triple", module.getTargetTriple()},
        {"compile_id", environment("FLAGPRISM_ASCEND_COMPILE_ID")},
        {"source_association",
         "surviving_source_metadata_and_full_debug_locations"},
        {"actors", std::move(actors)}};
    raw_fd_ostream jsonFile((base + ".json").str(), fileError,
                            sys::fs::OF_None);
    if (fileError)
      report_fatal_error("FlagPrism cannot retain compiler manifest");
    jsonFile << formatv("{0:2}", json::Value(std::move(manifest)));
    return changed ? PreservedAnalyses::none() : PreservedAnalyses::all();
  }
};
} // namespace
extern "C" LLVM_ATTRIBUTE_WEAK PassPluginLibraryInfo llvmGetPassPluginInfo() {
  return {LLVM_PLUGIN_API_VERSION, "FlagPrismAscendLateObserver", "1",
          [](PassBuilder &builder) {
            builder.registerPipelineStartEPCallback(
                [](ModulePassManager &manager, OptimizationLevel) {
                  manager.addPass(AscendLateObserver());
                });
            builder.registerPipelineParsingCallback(
                [](StringRef name, ModulePassManager &manager,
                   ArrayRef<PassBuilder::PipelineElement>) {
                  if (name != "flagprism-ascend-late-observer")
                    return false;
                  manager.addPass(AscendLateObserver());
                  return true;
                });
          }};
}
