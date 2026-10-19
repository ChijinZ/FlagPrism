#include "Debugger/Instrumentation/GcuTimeline.h"
#include "mlir/Dialect/LLVMIR/LLVMDialect.h"
#include "mlir/Dialect/LLVMIR/Transforms/Passes.h"
#include "mlir/IR/AsmState.h"
#include "mlir/IR/BuiltinOps.h"
#include "mlir/Parser/Parser.h"
#include "mlir/Pass/PassManager.h"
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

namespace mlir::flagtree::debugger {
llvm::Expected<std::string> addGcuNativeDebugScopes(llvm::StringRef input) {
  auto reject = [](const char *reason) -> llvm::Error {
    return llvm::createStringError(llvm::inconvertibleErrorCode(), reason);
  };
  mlir::MLIRContext context;
  context.allowUnregisteredDialects();
  context.getOrLoadDialect<mlir::LLVM::LLVMDialect>();
  // Vendor target properties are opaque here, and must be verified by the SDK.
  auto module = mlir::parseSourceString<mlir::ModuleOp>(
      input, mlir::ParserConfig(&context, false));
  if (!module)
    return reject("Cannot parse LLVM IR for GCU debug scopes");
  std::string before = coreText(*module);
  mlir::PassManager manager(&context);
  manager.enableVerifier(false);
  manager.addPass(mlir::LLVM::createDIScopeForLLVMFuncOpPass());
  if (mlir::failed(manager.run(*module)))
    return reject("Cannot add LLVM debug scopes");
  if (coreText(*module) != before) {
    llvm::errs() << "DI scope pass changed non-location IR; refusing output\n";
    return reject("Debug scopes changed non-location IR");
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
  // Parse exactly the same immutable bytes, never reopen the caller's path.
  auto original = mlir::parseSourceString<mlir::ModuleOp>(
      input, mlir::ParserConfig(&opaqueContext, false));
  auto located = mlir::parseSourceString<mlir::ModuleOp>(
      locatedText, mlir::ParserConfig(&opaqueContext, false));
  if (!original || !located)
    return reject("Cannot parse opaque SDK debug scope IR");
  std::string originalCore = coreText(*original);
  std::vector<mlir::Operation *> originalOps, locatedOps;
  original->walk([&](mlir::Operation *op) { originalOps.push_back(op); });
  located->walk([&](mlir::Operation *op) { locatedOps.push_back(op); });
  if (originalOps.size() != locatedOps.size())
    return reject("Debug scope operation count mismatch");
  for (size_t i = 0; i < originalOps.size(); ++i) {
    if (originalOps[i]->getName() != locatedOps[i]->getName())
      return reject("Debug scope operation order mismatch");
    originalOps[i]->setLoc(locatedOps[i]->getLoc());
  }
  if (coreText(*original) != originalCore) {
    llvm::errs()
        << "Location transfer changed opaque SDK IR; refusing output\n";
    return reject("Debug scope transfer changed SDK IR");
  }
  std::string output;
  llvm::raw_string_ostream stream(output);
  original->print(stream, locatedFlags);
  stream.flush();
  return output;
}
} // namespace mlir::flagtree::debugger
