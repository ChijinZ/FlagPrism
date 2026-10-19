// CPU prototype: DI-only bridge; the vendor SDK remains the final verifier.
#include "mlir/Dialect/LLVMIR/LLVMDialect.h"
#include "mlir/Dialect/LLVMIR/Transforms/Passes.h"
#include "mlir/IR/AsmState.h"
#include "mlir/IR/BuiltinOps.h"
#include "mlir/Parser/Parser.h"
#include "mlir/Pass/PassManager.h"
#include "llvm/Support/MemoryBuffer.h"
#include "llvm/Support/SourceMgr.h"
#include "llvm/Support/raw_ostream.h"
#include <vector>

static std::string coreText(mlir::ModuleOp module) {
  std::string text;
  llvm::raw_string_ostream stream(text);
  mlir::OpPrintingFlags flags;
  flags.printGenericOpForm();
  module.print(stream, flags);
  return text;
}

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  mlir::MLIRContext context;
  context.allowUnregisteredDialects();
  context.getOrLoadDialect<mlir::LLVM::LLVMDialect>();
  auto input = llvm::MemoryBuffer::getFile(argv[1]);
  if (!input)
    return 3;
  llvm::SourceMgr source;
  source.AddNewSourceBuffer(std::move(*input), llvm::SMLoc());
  // Vendor target properties are opaque here, and must be verified by the SDK.
  auto module = mlir::parseSourceFile<mlir::ModuleOp>(
      source, mlir::ParserConfig(&context, false));
  if (!module)
    return 4;
  std::string before = coreText(*module);
  mlir::PassManager manager(&context);
  manager.enableVerifier(false);
  manager.addPass(mlir::LLVM::createDIScopeForLLVMFuncOpPass());
  if (mlir::failed(manager.run(*module)))
    return 5;
  if (coreText(*module) != before) {
    llvm::errs() << "DI scope pass changed non-location IR; refusing output\n";
    return 6;
  }
  // Transfer locations only into a second parse that keeps all LLVM/GPU
  // operations and vendor properties opaque. New LLVM operation printers can
  // otherwise change the SDK's property encoding (e.g. overflow flags).
  std::string locatedText;
  llvm::raw_string_ostream locatedStream(locatedText);
  mlir::OpPrintingFlags locatedFlags;
  locatedFlags.printGenericOpForm();
  locatedFlags.enableDebugInfo();
  locatedFlags.useLocalScope(); // No aliases hidden inside opaque DI attrs.
  module->print(locatedStream, locatedFlags);
  locatedStream.flush();
  mlir::MLIRContext opaqueContext;
  opaqueContext.allowUnregisteredDialects();
  auto originalInput = llvm::MemoryBuffer::getFile(argv[1]);
  if (!originalInput)
    return 7;
  llvm::SourceMgr originalSource;
  originalSource.AddNewSourceBuffer(std::move(*originalInput), llvm::SMLoc());
  auto original = mlir::parseSourceFile<mlir::ModuleOp>(
      originalSource, mlir::ParserConfig(&opaqueContext, false));
  auto located = mlir::parseSourceString<mlir::ModuleOp>(
      locatedText, mlir::ParserConfig(&opaqueContext, false));
  if (!original || !located)
    return 8;
  std::string originalCore = coreText(*original);
  std::vector<mlir::Operation *> originalOps, locatedOps;
  original->walk([&](mlir::Operation *op) { originalOps.push_back(op); });
  located->walk([&](mlir::Operation *op) { locatedOps.push_back(op); });
  if (originalOps.size() != locatedOps.size())
    return 9;
  for (size_t i = 0; i < originalOps.size(); ++i) {
    if (originalOps[i]->getName() != locatedOps[i]->getName())
      return 10;
    originalOps[i]->setLoc(locatedOps[i]->getLoc());
  }
  if (coreText(*original) != originalCore) {
    llvm::errs() << "Location transfer changed opaque SDK IR; refusing output\n";
    return 11;
  }
  std::error_code error;
  llvm::raw_fd_ostream output(argv[2], error);
  if (error)
    return 12;
  original->print(output, locatedFlags);
  output.close();
  if (output.has_error())
    return 13;
  llvm::outs() << "non_location_IR_identical=true; "
                 "opaque_SDK_properties_identical=true; "
                 "SDK_validation_required=true\n";
  return 0;
}
