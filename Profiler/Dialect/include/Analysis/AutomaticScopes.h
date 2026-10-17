#ifndef FLAGPRISM_AUTOMATIC_SCOPES_H
#define FLAGPRISM_AUTOMATIC_SCOPES_H
#include "mlir/IR/BuiltinOps.h"
#include "mlir/Pass/Pass.h"
namespace mlir::triton::proton {
std::unique_ptr<OperationPass<ModuleOp>>
createAutomaticScopesPass(unsigned maxSites, bool census = false,
                          bool timeline = false);
}
#endif
