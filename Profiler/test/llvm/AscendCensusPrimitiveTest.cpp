// Actual LLVM IR construction/verification for the Ascend census writer.
// Source-coordinate provenance and SDK execution require separate hardware
// tests.
#include "../../llvm/AscendSourceCensus.h"
#include "llvm/IR/LLVMContext.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Verifier.h"
#include "llvm/Support/raw_ostream.h"

int checkLayout(uint64_t columns) {
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
  flagprism_ascend::appendCensus(ret, function->getArg(0), function->getArg(1),
                                 function->getArg(2), columns - 1, columns);
  if (llvm::verifyModule(module, &llvm::errs()))
    return 1;
  unsigned loads = 0, stores = 0;
  for (const auto &block : *function)
    for (const auto &instruction : block) {
      if (auto *load = llvm::dyn_cast<llvm::LoadInst>(&instruction)) {
        if (!load->isVolatile() || load->isAtomic())
          return 2;
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
  module.print(llvm::outs(), nullptr);
  return 0;
}

int main() {
  for (uint64_t columns : {1, 8, 128})
    if (int status = checkLayout(columns))
      return status;
  return 0;
}
