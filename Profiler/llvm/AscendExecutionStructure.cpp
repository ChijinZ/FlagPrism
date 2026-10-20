// Read-only upstream LLVM15 indexing of the exact actor input passed to CANN.
// This is structural evidence, not a claim about final native scheduling.
#include "llvm/ADT/DenseMap.h"
#include "llvm/ADT/StringExtras.h"
#include "llvm/Analysis/LoopInfo.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/DebugInfoMetadata.h"
#include "llvm/IR/Dominators.h"
#include "llvm/IR/InlineAsm.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Verifier.h"
#include "llvm/IRReader/IRReader.h"
#include "llvm/Support/JSON.h"
#include "llvm/Support/MemoryBuffer.h"
#include "llvm/Support/SHA256.h"
#include "llvm/Support/SourceMgr.h"
#include "llvm/Support/raw_ostream.h"
#include <stdexcept>

using namespace llvm;
namespace {
constexpr size_t InputLimit = 16 * 1024 * 1024;
constexpr size_t OutputLimit = 32 * 1024 * 1024;
struct Index {
  DenseMap<const Value *, int64_t> ids;
  int64_t next = 1;
  size_t work = 0, textBytes = 0;

  void charge(size_t n = 1) {
    if (n > 1000000 - work)
      throw std::runtime_error("Actor structural work budget exceeded");
    work += n;
  }
  std::string text(StringRef s) {
    if (s.size() > 4096 || s.size() > 8 * 1024 * 1024 - textBytes)
      throw std::runtime_error("Actor structural text budget exceeded");
    textBytes += s.size();
    return s.str();
  }
  int64_t id(const Value *v) {
    auto found = ids.find(v);
    if (found != ids.end())
      return found->second;
    if (next > 300000)
      throw std::runtime_error("Actor SSA value budget exceeded");
    return ids[v] = next++;
  }
  json::Object type(Type *t) {
    // Do not recursively expand named/aggregate types. Rules may only use the
    // explicitly encoded scalar/pointer facts, never a guessed printed type.
    json::Object out{{"kind", static_cast<int64_t>(t->getTypeID())}};
    if (auto *integer = dyn_cast<IntegerType>(t))
      out["integer_bits"] = static_cast<int64_t>(integer->getBitWidth());
    if (auto *pointer = dyn_cast<PointerType>(t))
      out["address_space"] = static_cast<int64_t>(pointer->getAddressSpace());
    return out;
  }
  json::Object value(const Value *v) {
    charge();
    json::Object out{{"id", id(v)}, {"type", type(v->getType())}};
    if (auto *integer = dyn_cast<ConstantInt>(v)) {
      if (integer->getBitWidth() > 64)
        out["constant_status"] = "integer_wider_than_64_bits";
      else {
        out["integer_hex"] = utohexstr(integer->getZExtValue());
        out["integer_bits"] = static_cast<int64_t>(integer->getBitWidth());
      }
    } else if (isa<UndefValue>(v) || isa<PoisonValue>(v)) {
      out["constant_status"] = "undefined_or_poison";
    } else if (isa<Constant>(v)) {
      out["constant_status"] = "other_constant_not_interpreted";
    }
    return out;
  }
  json::Object instruction(Instruction &i) {
    charge();
    json::Object out{{"id", id(&i)},
                     {"opcode", i.getOpcodeName()},
                     {"type", type(i.getType())}};
    json::Array operands;
    for (const Use &operand : i.operands())
      operands.push_back(value(operand.get()));
    out["operands"] = std::move(operands);
    if (auto *compare = dyn_cast<ICmpInst>(&i))
      out["predicate"] = ICmpInst::getPredicateName(compare->getPredicate());
    if (auto *gep = dyn_cast<GetElementPtrInst>(&i)) {
      out["element_type"] = type(gep->getSourceElementType());
      out["inbounds"] = gep->isInBounds();
    }
    if (auto *load = dyn_cast<LoadInst>(&i)) {
      out["volatile"] = load->isVolatile();
      out["atomic"] = load->isAtomic();
    }
    if (auto *store = dyn_cast<StoreInst>(&i)) {
      out["volatile"] = store->isVolatile();
      out["atomic"] = store->isAtomic();
    }
    if (auto *binary = dyn_cast<BinaryOperator>(&i);
        binary && (i.getOpcode() == Instruction::Add ||
                   i.getOpcode() == Instruction::Sub ||
                   i.getOpcode() == Instruction::Mul ||
                   i.getOpcode() == Instruction::Shl)) {
      out["nsw"] = binary->hasNoSignedWrap();
      out["nuw"] = binary->hasNoUnsignedWrap();
    }
    if (auto *call = dyn_cast<CallBase>(&i)) {
      if (auto *callee = call->getCalledFunction())
        out["callee"] = text(callee->getName());
      else if (auto *assembly = dyn_cast<InlineAsm>(call->getCalledOperand())) {
        out["assembly"] = text(assembly->getAsmString());
        out["constraints"] = text(assembly->getConstraintString());
        out["side_effects"] = assembly->hasSideEffects();
      } else
        out["indirect_call"] = true;
    }
    if (auto *phi = dyn_cast<PHINode>(&i)) {
      json::Array incoming;
      for (unsigned n = 0; n < phi->getNumIncomingValues(); ++n) {
        charge();
        incoming.push_back(
            json::Object{{"block", id(phi->getIncomingBlock(n))},
                         {"value", value(phi->getIncomingValue(n))}});
      }
      out["incoming"] = std::move(incoming);
    }
    if (const DebugLoc &loc = i.getDebugLoc()) {
      out["location"] =
          json::Object{{"file", text(loc->getFilename())},
                       {"directory", text(loc->getDirectory())},
                       {"line", static_cast<int64_t>(loc.getLine())},
                       {"column", static_cast<int64_t>(loc.getCol())}};
    }
    return out;
  }
  json::Object loop(Loop &l) {
    charge();
    json::Array blocks, latches, exits;
    for (BasicBlock *b : l.blocks()) {
      charge();
      blocks.push_back(id(b));
    }
    SmallVector<BasicBlock *, 8> latchBlocks, exitBlocks;
    l.getLoopLatches(latchBlocks);
    l.getExitBlocks(exitBlocks);
    for (BasicBlock *b : latchBlocks)
      latches.push_back(id(b));
    for (BasicBlock *b : exitBlocks)
      exits.push_back(id(b));
    // Iterate nested loops outside this function; deeply nested IR must not
    // create an unbounded C++ recursion in the evidence serializer.
    return json::Object{
        {"header", id(l.getHeader())},
        {"parent_header",
         l.getParentLoop() ? id(l.getParentLoop()->getHeader()) : int64_t(0)},
        {"blocks", std::move(blocks)},
        {"latches", std::move(latches)},
        {"exits", std::move(exits)}};
  }
  json::Object function(Function &f) {
    if (f.size() > 8192)
      throw std::runtime_error("Actor basic block budget exceeded");
    json::Array arguments, blocks, loops;
    for (Argument &a : f.args())
      arguments.push_back(value(&a));
    for (BasicBlock &b : f) {
      charge();
      json::Array instructions, successors;
      for (Instruction &i : b)
        instructions.push_back(instruction(i));
      for (unsigned n = 0; n < b.getTerminator()->getNumSuccessors(); ++n)
        successors.push_back(id(b.getTerminator()->getSuccessor(n)));
      blocks.push_back(json::Object{{"id", id(&b)},
                                    {"instructions", std::move(instructions)},
                                    {"successors", std::move(successors)}});
    }
    DominatorTree dom(f);
    LoopInfo info(dom);
    SmallVector<Loop *, 16> pending(info.begin(), info.end());
    while (!pending.empty()) {
      Loop *l = pending.pop_back_val();
      loops.push_back(loop(*l));
      for (Loop *child : l->getSubLoops())
        pending.push_back(child);
    }
    return json::Object{{"name", text(f.getName())},
                        {"entry", id(&f.getEntryBlock())},
                        {"arguments", std::move(arguments)},
                        {"blocks", std::move(blocks)},
                        {"loops", std::move(loops)}};
  }
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 2) {
    errs() << "Usage: flagprism-ascend-structure ACTUAL-ADAPTED-ACTOR.ll\n";
    return 2;
  }
  try {
    auto input = MemoryBuffer::getFile(argv[1]);
    if (!input || (*input)->getBufferSize() > InputLimit)
      throw std::runtime_error("Missing or oversized actor LLVM input");
    LLVMContext context;
    SMDiagnostic error;
    auto module = parseIR((*input)->getMemBufferRef(), error, context);
    if (!module) {
      error.print(argv[0], errs());
      return 1;
    }
    if (verifyModule(*module, &errs()))
      throw std::runtime_error("Actor LLVM input failed verification");
    Index index;
    json::Array functions;
    unsigned count = 0;
    for (Function &f : *module) {
      if (f.isDeclaration())
        continue;
      if (++count > 64)
        throw std::runtime_error("Actor function budget exceeded");
      functions.push_back(index.function(f));
    }
    json::Object result{
        {"schema_version", 1},
        {"model", "ascend.actor_llvm15.structure.v1"},
        {"input_sha256",
         toHex(SHA256::hash(arrayRefFromStringRef((*input)->getBuffer())),
               true)},
        {"target_triple", index.text(module->getTargetTriple())},
        {"functions", std::move(functions)},
        {"native_schedule_qualified", false}};
    std::string bytes;
    raw_string_ostream stream(bytes);
    stream << json::Value(std::move(result));
    stream.flush();
    if (bytes.size() > OutputLimit)
      throw std::runtime_error("Actor structural output budget exceeded");
    outs() << bytes << '\n';
  } catch (const std::exception &error) {
    errs() << error.what() << '\n';
    return 1;
  }
  return 0;
}
