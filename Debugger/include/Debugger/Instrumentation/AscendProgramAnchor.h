#pragma once
#include "mlir/IR/BuiltinOps.h"
#include "llvm/Support/Error.h"
#include <vector>

namespace mlir::flagtree::debugger {
// Ascend-only compiler bridge. No user formal or mathematical value is changed.
// The pinned Ascend AutoBlockify/TritonToLinalg patch must admit and transport
// this exact side-effect marker; an unpatched converter rejects it explicitly.
llvm::Error prepareAscendProgramAnchors(mlir::ModuleOp module);
llvm::Expected<uint32_t> prepareAscendSourceCensusAbi(
    mlir::ModuleOp module, const std::vector<uint32_t> &selectedSites);
}
