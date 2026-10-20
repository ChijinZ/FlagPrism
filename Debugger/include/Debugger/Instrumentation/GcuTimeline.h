#pragma once

#include "llvm/ADT/ArrayRef.h"
#include "llvm/ADT/StringRef.h"
#include "llvm/Support/Error.h"
#include <cstdint>
#include <string>

namespace mlir {
class ModuleOp;
class Operation;
} // namespace mlir
namespace mlir::flagtree::debugger {
// DI-only serialization bridge. The SDK must verify its output before codegen.
llvm::Expected<std::string> addGcuNativeDebugScopes(llvm::StringRef input);

// Standard DWARF rows for generated markers; no instruction/valueflow rights.
llvm::Expected<std::string> mapGcuNativeLocations(llvm::StringRef input);

// Check the actual before/after GCU IR, including SSA/CFG preservation and the
// permitted observer memory effects. This is not a final native timing proof.
llvm::Expected<std::string>
checkGcuExecutionPreservation(llvm::StringRef input, llvm::StringRef output,
                              uint32_t hiddenArgument, uint32_t capacity,
                              uint32_t maxRegions);

// The original operation identities come from this immutable rewrite session.
llvm::Expected<std::string>
checkGcuObserverTransformation(mlir::ModuleOp before, mlir::ModuleOp after,
                               llvm::ArrayRef<mlir::Operation *> original,
                               uint32_t hiddenArgument);

struct GcuExecutionRewrite {
  std::string ir;
  std::string manifest;
};
// The input is the actual SDK's generic GCU execution IR after ordinary
// lowering. The last formal must be the profiler's already-prepared hidden
// i32 pointer. No source-level mathematical operation is rewritten here.
llvm::Expected<GcuExecutionRewrite>
rewriteGcuExecutionTimeline(llvm::StringRef input, uint32_t hiddenArgument,
                            uint32_t capacity, uint32_t maxRegions = 8);
} // namespace mlir::flagtree::debugger
