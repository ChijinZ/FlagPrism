// Isolated late-recording experiment. Not a default backend or qualified ABI.
#include "llvm/ADT/MapVector.h"
#include "llvm/ADT/STLExtras.h"
#include "llvm/ADT/SmallPtrSet.h"
#include "llvm/ADT/SmallVector.h"
#include "llvm/ADT/StringSet.h"
#include "llvm/Analysis/AssumptionCache.h"
#include "llvm/IR/Attributes.h"
#include "llvm/IR/CallingConv.h"
#include "llvm/IR/DebugInfoMetadata.h"
#include "llvm/IR/Dominators.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/InlineAsm.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/LLVMContext.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Verifier.h"
#include "llvm/IRReader/IRReader.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/FormatVariadic.h"
#include "llvm/Support/JSON.h"
#include "llvm/Support/SourceMgr.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"
#include "llvm/Transforms/Utils/PromoteMemToReg.h"
#include <system_error>
using namespace llvm;
static cl::opt<std::string> Input(cl::Positional, cl::Required);
static cl::opt<std::string> Output("output", cl::Required);
static cl::opt<std::string> Manifest("manifest", cl::Required);
static cl::opt<int> ScratchArg("scratch-arg", cl::init(-1));
static cl::opt<unsigned> ProfileABI("flagtree-profile-abi", cl::init(0));
static cl::opt<unsigned> LogicalBudget("max-sites", cl::init(8));
static cl::opt<bool> BatchRecords("batch-records", cl::init(false));
static cl::opt<unsigned> RecordCapacity("capacity", cl::init(512));
static cl::opt<bool> AutoCapacity("auto-capacity", cl::init(false));
static cl::opt<unsigned> ObserverActors("actors", cl::init(0));
static cl::opt<bool> GroupMatrix("group-matrix", cl::init(false));
static cl::opt<bool> CompactPrograms("compact-programs", cl::init(false));
struct Site {
  Instruction *call;
  Instruction *last;
  unsigned id;
  std::string kind;
  bool interval;
  Value *payload;
  unsigned members;
  uint64_t storeBytes;
  SmallVector<Instruction *> origins;
};
struct Stamp {
  unsigned site;
  Value *begin;
  Value *end;
  Value *payload;
};
static bool hasDataUse(Value *value, unsigned budget = 256) {
  SmallVector<Value *> work{value};
  SmallPtrSet<Value *, 32> seen;
  while (!work.empty() && budget--) {
    Value *current = work.pop_back_val();
    if (!seen.insert(current).second)
      continue;
    for (User *user : current->users()) {
      auto *instruction = dyn_cast<Instruction>(user);
      if (!instruction)
        continue;
      if (auto *store = dyn_cast<StoreInst>(instruction)) {
        if (store->getValueOperand() == current)
          return true;
        continue;
      }
      if (isa<GetElementPtrInst, ICmpInst, BranchInst>(instruction) ||
          instruction->getType()->isPointerTy())
        continue;
      if (auto *select = dyn_cast<SelectInst>(instruction)) {
        if (select->getCondition() == current)
          continue;
      }
      if (auto *call = dyn_cast<CallBase>(instruction)) {
        if (auto *callee = call->getCalledFunction())
          if (callee->getName().contains("barrier") ||
              callee->getName().contains("cp.async") ||
              callee->getName().starts_with("llvm.assume"))
            continue;
        return true;
      }
      if (!instruction->getType()->isVoidTy())
        work.push_back(instruction);
    }
  }
  return false;
}
static std::string classify(Instruction &instruction) {
  if (auto *store = dyn_cast<StoreInst>(&instruction)) {
    if (store->getPointerAddressSpace() == 3)
      return "shared_store_after";
    if (store->getPointerAddressSpace() == 1)
      return "global_store_issue_bracket";
    return {};
  }
  if (auto *load = dyn_cast<LoadInst>(&instruction)) {
    if (load->getPointerAddressSpace() == 3)
      return "shared_load_native_bracket";
    if (load->getPointerAddressSpace() == 1)
      return "global_load_issue_bracket";
    return {};
  }
  if (isa<BinaryOperator>(instruction) &&
      (instruction.getType()->isFPOrFPVectorTy() || hasDataUse(&instruction)))
    return "compute_issue_bracket";
  if (auto *atomic = dyn_cast<AtomicRMWInst>(&instruction))
    return atomic->getPointerAddressSpace() == 1
               ? "global_atomic_issue_bracket"
               : "opaque_native_issue_bracket";
  if (auto *atomic = dyn_cast<AtomicCmpXchgInst>(&instruction))
    return atomic->getPointerAddressSpace() == 1
               ? "global_atomic_issue_bracket"
               : "opaque_native_issue_bracket";
  auto *operation = dyn_cast<CallBase>(&instruction);
  if (!operation)
    return {};
  CallBase &call = *operation;
  if (auto *function = call.getCalledFunction()) {
    StringRef name = function->getName();
    if (name == "llvm.nvvm.cp.async.commit.group")
      return "commit_after";
    if (name == "llvm.nvvm.cp.async.wait.group")
      return "wait_bracket";
    if (name == "llvm.nvvm.barrier.cta.sync.aligned.all")
      return "cta_barrier_after";
    if (name == "llvm.nvvm.bar.warp.sync")
      return "warp_sync_issue_bracket";
    if (name.starts_with("llvm.nvvm.ldmatrix.")) {
      if (name == "llvm.nvvm.ldmatrix.sync.aligned.m8n8.x4.b16.p3" ||
          name == "llvm.nvvm.ldmatrix.sync.aligned.m8n8.x4.trans.b16.p3")
        return "shared_load_issue_bracket";
      return "opaque_native_issue_bracket";
    }
    if (name.starts_with("llvm.nvvm.read.ptx.sreg.") ||
        name.starts_with("llvm.assume") || name.starts_with("llvm.lifetime.") ||
        name.starts_with("llvm.dbg."))
      return {};
    if (!function->isIntrinsic() || call.mayReadOrWriteMemory() ||
        call.mayHaveSideEffects())
      return "opaque_native_issue_bracket";
    if (call.getType()->isFPOrFPVectorTy() ||
        name.starts_with("llvm.nvvm.shfl.") ||
        (call.getType()->isIntegerTy() && hasDataUse(&call)))
      return "compute_issue_bracket";
    if (!function->isIntrinsic())
      return "opaque_native_issue_bracket";
  }
  if (auto *assembly = dyn_cast<InlineAsm>(call.getCalledOperand())) {
    StringRef text = assembly->getAsmString();
    if (text == "cp.async.cg.shared.global [ $0 + 0 ], [ $1 + 0 ], 0x10, $2;" ||
        text == "cp.async.ca.shared.global [ $0 + 0 ], [ $1 + 0 ], 0x10, $2;")
      return "copy_submit_after";
    if (text.starts_with("mma.sync.") && text.count(';') == 1)
      return "matrix_issue_bracket";
    if (text.contains(".shared") || text.contains("cp.async"))
      return "opaque_native_issue_bracket";
    if (text.contains("ld.global"))
      return "global_load_issue_bracket";
    if (text.contains("st.global"))
      return "global_store_issue_bracket";
    if (text.contains("atom.global") || text.contains("red.global"))
      return "global_atomic_issue_bracket";
    return "opaque_native_issue_bracket";
  }
  return {};
}
static Value *reg(IRBuilder<> &b, Module &m, StringRef name) {
  return b.CreateCall(
      m.getOrInsertFunction(name, FunctionType::get(b.getInt32Ty(), false)));
}
static Value *clock(IRBuilder<> &b, unsigned site, StringRef phase) {
  std::string text = "// flagprism_late_probe_site_" + std::to_string(site) +
                     "_" + phase.str() + "\n\tmov.u64 $0, %globaltimer;";
  return b.CreateCall(InlineAsm::get(FunctionType::get(b.getInt64Ty(), false),
                                     text, "=l,~{memory}", true));
}
int main(int argc, char **argv) {
  cl::ParseCommandLineOptions(argc, argv);
  LLVMContext context;
  SMDiagnostic diagnostic;
  auto module = parseIRFile(Input, diagnostic, context);
  if (!module) {
    diagnostic.print(argv[0], errs());
    return 1;
  }
  SmallVector<Function *> kernels;
  for (auto &function : *module)
    if (!function.isDeclaration() &&
        function.getCallingConv() == CallingConv::PTX_Kernel)
      kernels.push_back(&function);
  if (kernels.size() != 1) {
    errs() << "Expected one ordinary PTX kernel\n";
    return 2;
  }
  Function &function = *kernels.front();
  if (RecordCapacity < 1 || RecordCapacity > 4096 || LogicalBudget < 1 ||
      LogicalBudget > 128) {
    errs() << "Invalid bounded capture capacity/selection\n";
    return 2;
  }
  StringRef blockText =
      function.getFnAttribute("nvvm.reqntid").getValueAsString();
  SmallVector<StringRef> parts;
  blockText.split(parts, ',');
  uint64_t block[3] = {1, 1, 1};
  if (parts.empty() || parts.size() > 3) {
    errs() << "Missing actual block dimensions\n";
    return 2;
  }
  for (unsigned i = 0; i < parts.size(); ++i)
    if (parts[i].trim().getAsInteger(10, block[i]) || !block[i] ||
        block[i] > 1024) {
      errs() << "Invalid actual block dimensions\n";
      return 2;
    }
  uint64_t blockActors = block[0] * block[1] * block[2];
  if (!blockActors || blockActors > 1024) {
    errs() << "Invalid actual block size\n";
    return 2;
  }
  bool requiresFullFootprint = false;
  for (auto &basicBlock : function)
    for (auto &instruction : basicBlock) {
      std::string kind = classify(instruction);
      requiresFullFootprint |=
          kind == "copy_submit_after" || kind == "matrix_issue_bracket";
    }
  const uint64_t Actors = ObserverActors ? ObserverActors.getValue()
                          : requiresFullFootprint
                              ? blockActors
                              : std::min<uint64_t>(4, blockActors);
  if (!Actors || Actors > blockActors) {
    errs() << "Observer selection exceeds actual block\n";
    return 2;
  }
  const uint64_t HeaderWords = 6;
  // A complete CTA records every participating thread for dependency facts.
  // Use the existing 8 MiB raw ceiling, reserving allocator guard bytes, rather
  // than overflowing ordinary multi-warp loops at an artificial 2 MiB target.
  const uint64_t CaptureBudgetBytes =
      requiresFullFootprint ? 8 * 1024 * 1024 - 128 : 64 * 1024;
  uint64_t Capacity = RecordCapacity;
  if (AutoCapacity) {
    const uint64_t wordsPerActor = CaptureBudgetBytes / (2 * Actors * 8);
    if (!CompactPrograms || wordsPerActor < HeaderWords + 4) {
      errs() << "Automatic record budget cannot hold the selected actors\n";
      return 2;
    }
    Capacity = std::min<uint64_t>(Capacity, (wordsPerActor - HeaderWords) / 4);
  }
  const uint64_t SegmentWords = Actors * (HeaderWords + Capacity * 4);
  int scratchIndex = ScratchArg;
  if (scratchIndex < 0) {
    if (ProfileABI != 1 || function.arg_size() < 2) {
      errs() << "Reserved profile-argument ABI is not declared\n";
      return 2;
    }
    scratchIndex = function.arg_size() - 1;
  }
  if (static_cast<unsigned>(scratchIndex) >= function.arg_size()) {
    errs() << "Scratch argument outside actual signature\n";
    return 2;
  }
  Argument *scratch = function.getArg(scratchIndex);
  if (!scratch->use_empty()) {
    errs()
        << "Ordinary reserved scratch must be unused before instrumentation\n";
    return 2;
  }
  auto *pointer = dyn_cast<PointerType>(scratch->getType());
  if (!pointer || pointer->getAddressSpace() != 1) {
    errs() << "Scratch argument must be actual global pointer\n";
    return 2;
  }
  // The caller must validate this reserved ABI argument. Never infer it by
  // name.
  scratch->removeAttr(Attribute::ReadNone);
  scratch->removeAttr(Attribute::ReadOnly);
  SmallVector<Site> sites;
  json::Array inventory;
  for (auto &block : function)
    for (auto &instruction : block) {
      Instruction *call = &instruction;
      std::string kind = classify(*call);
      if (kind.empty())
        continue;
      if (kind == "unsupported_ldmatrix_geometry") {
        errs() << "Unmodeled native ldmatrix geometry\n";
        return 2;
      }
      unsigned id = sites.size() + 1;
      Value *payload = nullptr;
      uint64_t storeBytes = 0;
      if (auto *store = dyn_cast<StoreInst>(call)) {
        payload = store->getPointerOperand();
        auto bytes = module->getDataLayout().getTypeStoreSize(
            store->getValueOperand()->getType());
        if (bytes.isScalable() || bytes.getFixedValue() > 256) {
          errs() << "Unsupported actual shared store width\n";
          return 2;
        }
        storeBytes = bytes.getFixedValue();
      } else if (auto *load = dyn_cast<LoadInst>(call)) {
        payload = load->getPointerOperand();
        auto bytes = module->getDataLayout().getTypeStoreSize(load->getType());
        if (bytes.isScalable() || bytes.getFixedValue() > 256) {
          errs() << "Unsupported actual shared load width\n";
          return 2;
        }
        storeBytes = bytes.getFixedValue();
      } else if (kind == "copy_submit_after" ||
                 kind == "shared_load_issue_bracket" ||
                 kind == "wait_bracket" || kind == "cta_barrier_after" ||
                 kind == "warp_sync_issue_bracket")
        payload = cast<CallBase>(call)->getArgOperand(0);
      bool interval = kind != "commit_after" && kind != "copy_submit_after" &&
                      kind != "cta_barrier_after" &&
                      kind != "shared_store_after";
      if (!sites.empty() &&
          ((GroupMatrix && kind == "matrix_issue_bracket") ||
           (kind == "compute_issue_bracket" &&
            sites.back().last->getNextNode() == call)) &&
          sites.back().kind == kind &&
          sites.back().call->getParent() == call->getParent()) {
        sites.back().last = call;
        ++sites.back().members;
        sites.back().origins.push_back(call);
        continue;
      }
      sites.push_back(
          {call, call, id, kind, interval, payload, 1, storeBytes, {call}});
    }
  if (sites.empty()) {
    for (auto &block : function)
      if (auto *ret = dyn_cast<ReturnInst>(block.getTerminator()))
        sites.push_back({ret,
                         ret,
                         static_cast<unsigned>(sites.size() + 1),
                         "control_checkpoint",
                         false,
                         nullptr,
                         1,
                         0,
                         {ret}});
  }
  StringSet<> optionalKeys;
  SmallVector<std::string> keys;
  auto optional = [](const Site &site) {
    return StringRef(site.kind).starts_with("global_") ||
           site.kind == "compute_issue_bracket" ||
           site.kind == "opaque_native_issue_bracket";
  };
  auto sourceKey = [](const Site &site) {
    std::string key = site.kind;
    if (auto loc = site.call->getDebugLoc())
      key += ":" + loc->getFilename().str() + ":" +
             std::to_string(loc.getLine()) + ":" + std::to_string(loc.getCol());
    return key;
  };
  for (const Site &site : sites)
    if (optional(site)) {
      std::string key = sourceKey(site);
      if (optionalKeys.insert(key).second)
        keys.push_back(key);
    }
  StringSet<> chosen;
  unsigned keep = std::min<unsigned>(LogicalBudget, keys.size());
  for (unsigned i = 0; i < keep; ++i)
    chosen.insert(keys[keep == 1 ? 0
                                 : static_cast<size_t>(i) * (keys.size() - 1) /
                                       (keep - 1)]);
  SmallVector<Site> selected;
  json::Array unselected;
  for (const Site &site : sites) {
    if (!optional(site) || chosen.contains(sourceKey(site)))
      selected.push_back(site);
    else
      unselected.push_back(json::Object{{"site_id", site.id},
                                        {"kind", site.kind},
                                        {"reason", "logical_site_budget"}});
  }
  sites = std::move(selected);
  for (const Site &site : sites) {
    const Instruction &instruction = *site.call;
    unsigned id = site.id;
    const std::string &kind = site.kind;
    bool interval = site.interval;
    json::Object row{{"site_id", id},
                     {"kind", kind},
                     {"record_semantics", interval
                                              ? "observer_issue_bracket"
                                              : "observer_checkpoint_after"}};
    if (auto location = instruction.getDebugLoc()) {
      row["line"] = location.getLine();
      row["column"] = location.getCol();
      row["file"] = location->getFilename();
      row["directory"] = location->getDirectory();
    }
    row["member_count"] = site.members;
    json::Array members;
    for (Instruction *member : site.origins) {
      json::Object origin;
      if (auto location = member->getDebugLoc()) {
        origin["line"] = location.getLine();
        origin["column"] = location.getCol();
        origin["file"] = location->getFilename();
        origin["directory"] = location->getDirectory();
      }
      if (auto *call = dyn_cast<CallBase>(member)) {
        if (auto *function = call->getCalledFunction())
          origin["native_operation"] = function->getName();
        else if (auto *assembly = dyn_cast<InlineAsm>(call->getCalledOperand()))
          origin["native_operation"] = assembly->getAsmString();
      } else
        origin["native_operation"] = member->getOpcodeName();
      members.push_back(std::move(origin));
    }
    row["members"] = std::move(members);
    if (kind == "copy_submit_after") {
      row["payload_encoding"] =
          Actors == 1 ? "absolute_shared_address_u64"
                      : "absolute_shared_address_u32_source_valid_bytes_u32";
      row["destination_bytes"] = 16;
    }
    if (kind == "shared_store_after" || kind == "shared_load_native_bracket") {
      row["payload_encoding"] = "absolute_shared_address_u32_access_bytes_u32";
      row["access_bytes"] = site.storeBytes;
      row["destination_bytes"] = site.storeBytes;
    }
    inventory.push_back(std::move(row));
  }
  if (sites.empty() || sites.size() > 4096) {
    errs() << "No supported sites or selection budget exceeded\n";
    return 2;
  }
  Instruction *entry = &*function.getEntryBlock().getFirstInsertionPt();
  IRBuilder<> init(entry);
  auto *lost =
      init.CreateAlloca(init.getInt1Ty(), nullptr, "flagprism.late.lost");
  init.CreateStore(init.getFalse(), lost);
  auto *ordinal =
      init.CreateAlloca(init.getInt64Ty(), nullptr, "flagprism.late.ordinal");
  init.CreateStore(init.getInt64(0), ordinal);
  Value *tx = reg(init, *module, "llvm.nvvm.read.ptx.sreg.tid.x");
  Value *ty = reg(init, *module, "llvm.nvvm.read.ptx.sreg.tid.y");
  Value *tz = reg(init, *module, "llvm.nvvm.read.ptx.sreg.tid.z");
  Value *ntx = reg(init, *module, "llvm.nvvm.read.ptx.sreg.ntid.x");
  Value *nty = reg(init, *module, "llvm.nvvm.read.ptx.sreg.ntid.y");
  Value *actorIndex = init.CreateZExt(
      init.CreateAdd(
          tx, init.CreateMul(ntx, init.CreateAdd(ty, init.CreateMul(nty, tz)))),
      init.getInt64Ty());
  Value *actor = init.CreateICmpULT(actorIndex, init.getInt64(Actors));
  Value *x = reg(init, *module, "llvm.nvvm.read.ptx.sreg.ctaid.x"),
        *y = reg(init, *module, "llvm.nvvm.read.ptx.sreg.ctaid.y"),
        *z = reg(init, *module, "llvm.nvvm.read.ptx.sreg.ctaid.z");
  Value *nx = reg(init, *module, "llvm.nvvm.read.ptx.sreg.nctaid.x"),
        *ny = reg(init, *module, "llvm.nvvm.read.ptx.sreg.nctaid.y");
  Value *program = init.CreateAdd(
      init.CreateZExt(x, init.getInt64Ty()),
      init.CreateMul(
          init.CreateZExt(nx, init.getInt64Ty()),
          init.CreateAdd(
              init.CreateZExt(y, init.getInt64Ty()),
              init.CreateMul(init.CreateZExt(ny, init.getInt64Ty()),
                             init.CreateZExt(z, init.getInt64Ty())))));
  auto *sharedSymbol = module->getNamedGlobal("global_smem");
  if ((!sharedSymbol || sharedSymbol->getAddressSpace() != 3) &&
      llvm::any_of(sites, [](const Site &site) {
        return StringRef(site.kind).starts_with("shared_") ||
               site.kind == "copy_submit_after";
      })) {
    errs() << "Missing actual compiler dynamic-shared symbol\n";
    return 2;
  }
  Value *sharedBase = sharedSymbol
                          ? init.CreatePtrToInt(sharedSymbol, init.getInt64Ty())
                          : init.getInt64(0);
  Value *physicalProgram = init.CreateZExt(program, init.getInt64Ty());
  Value *programSelected = init.getTrue();
  if (CompactPrograms) {
    Value *nz = reg(init, *module, "llvm.nvvm.read.ptx.sreg.nctaid.z");
    Value *total =
        init.CreateMul(init.CreateZExt(nx, init.getInt64Ty()),
                       init.CreateMul(init.CreateZExt(ny, init.getInt64Ty()),
                                      init.CreateZExt(nz, init.getInt64Ty())));
    programSelected = init.CreateOr(
        init.CreateICmpEQ(physicalProgram, init.getInt64(0)),
        init.CreateICmpEQ(physicalProgram,
                          init.CreateSub(total, init.getInt64(1))));
    physicalProgram =
        init.CreateSelect(init.CreateICmpEQ(physicalProgram, init.getInt64(0)),
                          init.getInt64(0), init.getInt64(1));
    actor = init.CreateAnd(actor, programSelected);
  }
  Value *base = init.CreateMul(physicalProgram, init.getInt64(SegmentWords));
  auto address = [&](IRBuilder<> &b, Value *offset) {
    return b.CreateGEP(
        b.getInt64Ty(), scratch,
        b.CreateAdd(base, b.CreateAdd(b.CreateMul(offset, b.getInt64(Actors)),
                                      actorIndex)));
  };
  MapVector<BasicBlock *, SmallVector<Stamp>> batches;
  for (Site &site : sites) {
    IRBuilder<> before(site.call);
    Value *begin = site.interval ? clock(before, site.id, "entry") : nullptr;
    Instruction *next = site.kind == "control_checkpoint"
                            ? site.last
                            : site.last->getNextNode();
    if (!next) {
      errs() << "Unsupported terminator call\n";
      return 3;
    }
    IRBuilder<> after(next);
    Value *end = clock(after, site.id, "exit");
    if (!begin)
      begin = end;
    Value *payload = after.getInt64(0);
    if (site.payload) {
      if (site.payload->getType()->isPointerTy())
        payload = after.CreatePtrToInt(site.payload, after.getInt64Ty());
      else if (site.payload->getType()->isIntegerTy())
        payload = after.CreateZExtOrTrunc(site.payload, after.getInt64Ty());
      else {
        errs() << "Unsupported actual site payload\n";
        return 3;
      }
    }
    if (Actors != 1 && site.kind == "copy_submit_after") {
      auto *copy = cast<CallBase>(site.call);
      auto *assembly = dyn_cast<InlineAsm>(copy->getCalledOperand());
      if (!assembly || copy->arg_size() != 3 ||
          !copy->getArgOperand(2)->getType()->isIntegerTy(32) ||
          !StringRef(assembly->getAsmString()).contains(", 0x10, $2;")) {
        errs() << "Unsupported actual copy size/payload form\n";
        return 3;
      }
      payload = after.CreateOr(
          after.CreateAnd(payload, after.getInt64(0xffffffff)),
          after.CreateShl(
              after.CreateZExt(copy->getArgOperand(2), after.getInt64Ty()),
              after.getInt64(32)));
    }
    if (site.kind == "shared_store_after" ||
        site.kind == "shared_load_native_bracket")
      payload =
          after.CreateOr(after.CreateAnd(payload, after.getInt64(0xffffffff)),
                         after.getInt64(site.storeBytes << 32));
    if (BatchRecords) {
      batches[site.call->getParent()].push_back({site.id, begin, end, payload});
      continue;
    }
    Value *count = after.CreateLoad(after.getInt64Ty(), ordinal);
    Value *selected = after.CreateAnd(
        actor, after.CreateICmpULT(count, after.getInt64(Capacity)));
    Value *isOverflow = after.CreateAnd(
        actor, after.CreateICmpUGE(count, after.getInt64(Capacity)));
    Instruction *thenTerm = SplitBlockAndInsertIfThen(selected, next, false);
    IRBuilder<> log(thenTerm);
    Value *offset = log.CreateAdd(log.getInt64(HeaderWords),
                                  log.CreateMul(count, log.getInt64(4)));
    Value *words[] = {log.getInt64(site.id), begin, end, payload};
    for (unsigned i = 0; i < 4; ++i)
      log.CreateStore(words[i],
                      address(log, log.CreateAdd(offset, log.getInt64(i))))
          ->setAlignment(Align(8));
    log.CreateStore(log.CreateAdd(count, log.getInt64(1)), ordinal);
    // Saturation is explicit and never overwrites earlier records.
    Instruction *overflowTerm =
        SplitBlockAndInsertIfThen(isOverflow, next, false);
    IRBuilder<> overflow(overflowTerm);
    overflow.CreateStore(overflow.getInt64(1),
                         address(overflow, overflow.getInt64(1)));
  }
  // Reads stay at the native operations. Publishing at the original block end
  // avoids a control transition and global stores between every pair of ops.
  // Loss stops later batches; published counts never include unwritten holes.
  for (auto &batch : batches) {
    Instruction *terminator = batch.first->getTerminator();
    IRBuilder<> b(terminator);
    Value *count = b.CreateLoad(b.getInt64Ty(), ordinal);
    Value *enabled =
        b.CreateAnd(actor, b.CreateNot(b.CreateLoad(b.getInt1Ty(), lost)));
    Value *fits = b.CreateAnd(
        b.getInt1(batch.second.size() <= Capacity),
        b.CreateICmpULE(count, b.getInt64(Capacity >= batch.second.size()
                                              ? Capacity - batch.second.size()
                                              : 0)));
    Value *selected = b.CreateAnd(enabled, fits);
    Value *overflowed = b.CreateAnd(enabled, b.CreateNot(fits));
    Instruction *thenTerm =
        SplitBlockAndInsertIfThen(selected, terminator, false);
    IRBuilder<> log(thenTerm);
    unsigned index = 0;
    for (const Stamp &stamp : batch.second) {
      Value *offset =
          log.CreateAdd(log.getInt64(HeaderWords),
                        log.CreateMul(log.CreateAdd(count, log.getInt64(index)),
                                      log.getInt64(4)));
      Value *words[] = {log.getInt64(stamp.site), stamp.begin, stamp.end,
                        stamp.payload};
      for (unsigned i = 0; i < 4; ++i)
        log.CreateStore(words[i],
                        address(log, log.CreateAdd(offset, log.getInt64(i))))
            ->setAlignment(Align(8));
      ++index;
    }
    log.CreateStore(log.CreateAdd(count, log.getInt64(index)), ordinal);
    Instruction *overflowTerm =
        SplitBlockAndInsertIfThen(overflowed, terminator, false);
    IRBuilder<> overflow(overflowTerm);
    overflow.CreateStore(overflow.getTrue(), lost);
    overflow.CreateStore(overflow.getInt64(1),
                         address(overflow, overflow.getInt64(1)));
  }
  SmallVector<ReturnInst *> returns;
  for (auto &block : function)
    if (auto *ret = dyn_cast<ReturnInst>(block.getTerminator()))
      returns.push_back(ret);
  for (auto *ret : returns) {
    auto *term = SplitBlockAndInsertIfThen(actor, ret, false);
    IRBuilder<> b(term);
    b.CreateStore(b.CreateLoad(b.getInt64Ty(), ordinal),
                  address(b, b.getInt64(0)));
    b.CreateStore(b.getInt64(0x46504c34), address(b, b.getInt64(2)));
    b.CreateStore(b.CreateZExt(program, b.getInt64Ty()),
                  address(b, b.getInt64(3)));
    b.CreateStore(sharedBase, address(b, b.getInt64(4)));
    b.CreateStore(actorIndex, address(b, b.getInt64(5)));
  }
  DominatorTree dominators(function);
  SmallVector<AllocaInst *> allocas{ordinal, lost};
  PromoteMemToReg(allocas, dominators);
  if (verifyModule(*module, &errs()))
    return 4;
  std::error_code error;
  raw_fd_ostream output(Output, error);
  if (error) {
    errs() << error.message();
    return 5;
  }
  module->print(output, nullptr);
  output.close();
  if (output.has_error()) {
    errs() << "Failed writing complete LLVM output\n";
    return 5;
  }
  raw_fd_ostream manifest(Manifest, error);
  if (error) {
    errs() << error.message();
    return 5;
  }
  manifest << formatv(
      "{0:2}\n",
      json::Value(json::Object{
          {"schema_version", 1},
          {"record_layout_version", 1},
          {"prototype_only", true},
          {"batch_records", BatchRecords.getValue()},
          {"scratch_arg", scratchIndex},
          {"profile_argument_abi", ProfileABI.getValue()},
          {"block_dimensions", json::Array{block[0], block[1], block[2]}},
          {"max_sites", LogicalBudget.getValue()},
          {"unselected_sites", std::move(unselected)},
          {"capacity_per_program", Capacity},
          {"capacity_policy",
           AutoCapacity ? "bounded-actor-bytes-v2" : "explicit-record-count"},
          {"automatic_pair_budget_bytes",
           AutoCapacity ? CaptureBudgetBytes : 0},
          {"requires_full_footprint", requiresFullFootprint},
          {"header_words", HeaderWords},
          {"actors", Actors},
          {"observer_selection",
           "full_cta_for_native_async_matrix_else_first_threads"},
          {"dependency_footprint_complete", Actors == blockActors},
          {"group_matrix", GroupMatrix.getValue()},
          {"compact_programs", CompactPrograms.getValue()},
          {"word_layout", "program/logical_word/actor"},
          {"segment_words", SegmentWords},
          {"observer", "actual flattened CTA thread per program"},
          {"sites", std::move(inventory)},
          {"source_cost_qualified", false},
          {"epoch_qualified", false}}));
  manifest.close();
  if (manifest.has_error()) {
    errs() << "Failed writing complete manifest\n";
    return 5;
  }
  return 0;
}
