// LLVM construction plus host execution of the publisher's control paths.
// The device timer is replaced only in this explicit CPU fixture. This does
// not qualify SYS_CNT, device visibility, source boundaries or actor ownership.
#include "../../llvm/AscendTimeline.h"
#include "llvm/ExecutionEngine/ExecutionEngine.h"
#include "llvm/ExecutionEngine/MCJIT.h"
#include "llvm/IR/LLVMContext.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Verifier.h"
#include "llvm/Support/TargetSelect.h"
#include "llvm/Support/raw_ostream.h"
#include <array>
#include <memory>

using namespace llvm;
using namespace flagprism_ascend;
int main() {
  InitializeNativeTarget();
  InitializeNativeTargetAsmPrinter();
  LLVMContext context;
  auto module = std::make_unique<Module>("ascend-timeline-publisher-fixture", context);
  auto *i64 = Type::getInt64Ty(context);
  auto *pointer = PointerType::get(context, 1);
  auto *signature = FunctionType::get(Type::getVoidTy(context),
                                      {pointer, i64, i64, i64, i64}, false);
  auto *function = Function::Create(signature, GlobalValue::ExternalLinkage,
                                    "publish_pair", *module);
  auto *entry = BasicBlock::Create(context, "entry", function);
  IRBuilder<> builder(entry);
  auto *ret = builder.CreateRetVoid();
  auto *start = beginTimeline(ret, function->getArg(0), function->getArg(1),
                              function->getArg(2), function->getArg(3),
                              function->getArg(4), 2);
  endTimeline(ret, function->getArg(0), function->getArg(1), function->getArg(2),
               function->getArg(3), function->getArg(4), start, 2, 13, 1);
  if (verifyModule(*module, &errs())) return 1;

  // Replace exactly the two device readers with an explicit deterministic
  // fixture. Persisted device IR never undergoes this substitution.
  auto *clock = Function::Create(FunctionType::get(i64, false),
                                 GlobalValue::InternalLinkage, "fixture_clock", *module);
  auto *ticks = new GlobalVariable(*module, i64, false,
      GlobalValue::InternalLinkage, ConstantInt::get(i64, 1000), "fixture_ticks");
  IRBuilder<> cb(BasicBlock::Create(context, "entry", clock));
  auto *tick = cb.CreateLoad(i64, ticks);
  cb.CreateStore(cb.CreateAdd(tick, cb.getInt64(7)), ticks);
  cb.CreateRet(tick);
  unsigned readers = 0;
  for (auto &block : *function) for (auto &inst : block)
    if (auto *call = dyn_cast<CallInst>(&inst))
      if (auto *assembly = dyn_cast<InlineAsm>(call->getCalledOperand())) {
        if (assembly->getAsmString() != "MOV $0, SYS_CNT" ||
            !assembly->hasSideEffects()) return 2;
        call->setCalledFunction(clock);
        ++readers;
      }
  if (readers != 2 || verifyModule(*module, &errs())) return 3;
  std::string error;
  std::unique_ptr<ExecutionEngine> engine(EngineBuilder(std::move(module))
      .setEngineKind(EngineKind::JIT).setErrorStr(&error).create());
  if (!engine) { errs() << error; return 4; }
  engine->finalizeObject();
  using Publish = void (*)(uint64_t *, uint64_t, uint64_t, uint64_t, uint64_t);
  auto publish = reinterpret_cast<Publish>(engine->getFunctionAddress("publish_pair"));
  if (!publish) return 5;
  constexpr size_t words = 2 * 3 * (8 + 2 * 8);
  constexpr uint64_t guard = UINT64_C(0x1eafc0de1eafc0de);
  unsigned cases = 0;
  for (uint64_t last : {0, 1, 257})
    for (uint64_t program : {0, 1, 257})
      for (uint64_t actor : {0, 1, 2, 3}) {
        std::array<uint64_t, words + 16> storage{};
        for (size_t i = 0; i < 8; ++i)
          storage[i] = storage[words + 8 + i] = guard;
        auto *raw = storage.data() + 8;
        for (int visit = 0; visit < 3; ++visit)
          publish(raw, program, last, actor, 91);
        const bool selected = (program == 0 || program == last) && actor < 3;
        const size_t base = ((program == 0 ? 0 : 1) * 3 + actor) * 24;
        for (size_t i = 0; i < words; ++i)
          if ((!selected || i < base || i >= base + 24) && raw[i] != 0)
            return 6;
        if (selected) {
          auto *header = raw + base;
          if (header[0] != kTimelineMagic || header[1] != 2 || header[2] != 3 ||
              header[3] != 1 || header[4] != program || header[5] != actor ||
              header[6] != 91 || header[7] != 5) return 7;
          for (size_t n = 0; n < 2; ++n) {
            auto *pair = header + 8 + n * 8;
            const uint64_t descriptor = 13 | (UINT64_C(1) << 32);
            if (pair[0] != descriptor || pair[1] != n || pair[3] - pair[2] != 7 ||
                pair[4] != program || pair[5] != actor || pair[6] != 91 ||
                pair[7] != (kTimelineCommit ^ descriptor ^ n ^ program ^ actor ^ 91))
              return 8;
          }
          header[2] = header[3] = kTimelineMaxCount;
          publish(raw, program, last, actor, 91);
          if (header[2] != kTimelineMaxCount || header[3] != kTimelineMaxCount ||
              header[1] != 2 || header[7] != 7) return 9;
        }
        for (size_t i = 0; i < 8; ++i)
          if (storage[i] != guard || storage[words + 8 + i] != guard) return 10;
        ++cases;
      }
  outs() << "publisher_fixture_cases=" << cases << " verified=1\n";
  return 0;
}
