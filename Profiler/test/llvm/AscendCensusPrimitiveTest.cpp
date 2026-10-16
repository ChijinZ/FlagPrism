// Actual LLVM IR construction/verification for the Ascend census writer.
// Source-coordinate provenance and SDK execution require separate hardware
// tests.
#include "../../llvm/AscendSourceCensus.h"
#include "llvm/IR/LLVMContext.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Verifier.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/Operator.h"
#include "llvm/Support/raw_ostream.h"

int checkLayout(uint64_t columns, unsigned version, uint64_t program, uint64_t actor) {
  llvm::LLVMContext context;
  llvm::Module module("ascend-census-primitive-contract", context);
  auto *i64 = llvm::Type::getInt64Ty(context);
  auto *pointer = llvm::PointerType::get(context, 1);
  auto *signature = llvm::FunctionType::get(llvm::Type::getVoidTy(context),
                                            {pointer, i64, i64}, false);
  auto *function = llvm::Function::Create(
      signature, llvm::GlobalValue::ExternalLinkage, "census_contract", module);
  auto *entry = llvm::BasicBlock::Create(context, "entry", function);
  llvm::IRBuilder<> builder(entry);
  auto *ret = builder.CreateRetVoid();
  flagprism_ascend::appendCensus(ret, function->getArg(0), builder.getInt64(program),
                                 builder.getInt64(actor), columns - 1, columns, version);
  if (llvm::verifyModule(module, &llvm::errs()))
    return 1;
  unsigned loads = 0, stores = 0;
  for (const auto &block : *function)
    for (const auto &instruction : block) {
      if (auto *load = llvm::dyn_cast<llvm::LoadInst>(&instruction)) {
        if (!load->isVolatile() || load->isAtomic())
          return 2;
        auto *gep = llvm::dyn_cast<llvm::GEPOperator>(load->getPointerOperand());
        llvm::APInt offset(64, 0);
        if (!gep || !gep->accumulateConstantOffset(module.getDataLayout(), offset))
          return 6;
        const uint64_t stride = version == 3 ? ((columns * 8 + 63) / 64) * 64 : columns * 8;
        const uint64_t expected = (version == 3 ? 64 : 32) +
            (program * 3 + actor) * stride + (columns - 1) * 8 + loads * 4;
        if (offset.getZExtValue() != expected ||
            expected + 4 > (version == 3 ? 64 : 32) + 257 * 3 * stride)
          return 7;
        ++loads;
      }
      if (auto *store = llvm::dyn_cast<llvm::StoreInst>(&instruction)) {
        if (!store->isVolatile() || store->isAtomic())
          return 3;
        ++stores;
      }
      if (llvm::isa<llvm::CallInst>(instruction))
        return 4;
    }
  if (loads != 2 || stores != 2)
    return 5;
  return 0;
}

int main() {
  for (unsigned version : {1, 2, 3})
    for (uint64_t columns : {1, 2, 4, 8, 9, 16, 128})
      for (uint64_t program : {0, 1, 256})
        for (uint64_t actor : {0, 1, 2})
          if (int status = checkLayout(columns, version, program, actor))
            return status;
  return 0;
}
