#pragma once

#include "llvm/ADT/StringRef.h"
#include "llvm/Support/Error.h"
#include <cstdint>
#include <string>

namespace mlir::flagtree::debugger {
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
