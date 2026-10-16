#include "Debugger/Instrumentation/AscendProgramAnchor.h"
#include "mlir/Dialect/Arith/IR/Arith.h"
#include "mlir/Dialect/LLVMIR/LLVMDialect.h"
#include "mlir/IR/Builders.h"
#include "triton/Dialect/Triton/IR/Dialect.h"

namespace mlir::flagtree::debugger {
llvm::Error prepareAscendProgramAnchors(mlir::ModuleOp module) {
  constexpr const char *version =
      "flagtree.profile.ascend_program_anchor_version";
  if (auto existing = module->getAttrOfType<IntegerAttr>(version)) {
    if (existing.getInt() == 1)
      return llvm::Error::success();
    return llvm::createStringError(
        llvm::inconvertibleErrorCode(),
        "unsupported Ascend source program anchor version");
  }
  SmallVector<triton::FuncOp> entries;
  module.walk([&](triton::FuncOp function) {
    if (function.isPublic() && !function.isExternal())
      entries.push_back(function);
  });
  if (entries.size() != 1)
    return llvm::createStringError(
        llvm::inconvertibleErrorCode(),
        "Ascend source program anchor needs one actual public entry");
  auto function = entries.front();
  module.getContext()->loadDialect<LLVM::LLVMDialect>();
  OpBuilder builder(module.getContext());
  builder.setInsertionPointToStart(&function.getBody().front());
  SmallVector<Value> values;
  auto location = function.getLoc();
  for (unsigned axis = 0; axis < 3; ++axis) {
    auto value = builder.create<triton::GetProgramIdOp>(
        location, static_cast<triton::ProgramIDDim>(axis));
    values.push_back(
        builder.create<arith::ExtSIOp>(location, builder.getI64Type(), value));
  }
  for (unsigned axis = 0; axis < 3; ++axis) {
    auto value = builder.create<triton::GetNumProgramsOp>(
        location, static_cast<triton::ProgramIDDim>(axis));
    values.push_back(
        builder.create<arith::ExtSIOp>(location, builder.getI64Type(), value));
  }
  OperationState state(location, "llvm.inline_asm");
  state.addOperands(values);
  state.addAttribute(
      "asm_string",
      builder.getStringAttr("/* flagprism.source_program_axes.v1 */"));
  state.addAttribute("constraints", builder.getStringAttr("l,l,l,l,l,l"));
  state.addAttribute("has_side_effects", builder.getUnitAttr());
  auto *anchor = builder.create(state);
  anchor->setAttr("flagtree.profile.source_program_axes",
                  builder.getI32IntegerAttr(1));
  module->setAttr(version, builder.getI32IntegerAttr(1));
  return llvm::Error::success();
}
} // namespace mlir::flagtree::debugger

#include "Debugger/Instrumentation/Passes.h"
#include <map>
#include <set>

namespace mlir::flagtree::debugger {
llvm::Expected<uint32_t>
prepareAscendSourceCensusAbi(mlir::ModuleOp module,
                             const std::vector<uint32_t> &selectedSites) {
  auto fail = [](const char *message) {
    return llvm::createStringError(llvm::inconvertibleErrorCode(), message);
  };
  if (selectedSites.empty() || selectedSites.size() > 128)
    return fail("Ascend census needs 1..128 actual compiler selected sites");
  std::set<uint32_t> requested;
  for (uint32_t site : selectedSites)
    if (!site || site > INT32_MAX || !requested.insert(site).second)
      return fail("Ascend census selected site IDs are invalid or duplicated");
  SmallVector<triton::FuncOp> entries;
  module.walk([&](triton::FuncOp function) {
    if (function.isPublic() && !function.isExternal())
      entries.push_back(function);
  });
  if (entries.size() != 1)
    return fail("Ascend census needs one actual public entry");
  auto function = entries.front();
  std::map<uint32_t, Operation *> operations;
  bool duplicate = false;
  function.walk([&](Operation *operation) {
    auto id = operation->getAttrOfType<IntegerAttr>("flagtree.debug.op_id");
    if (id && id.getInt() > 0 && requested.count(id.getInt()))
      if (!operations.emplace(id.getInt(), operation).second)
        duplicate = true;
  });
  if (duplicate || operations.size() != selectedSites.size())
    return fail("Ascend census selected IDs lack unique actual operations");
  if (module->hasAttr("flagtree.profile.ascend_source_census_version"))
    return fail("Ascend census ABI is already prepared; a changed selection "
                "needs a fresh compiler module");
  for (const auto &entry : operations) {
    Operation *operation = entry.second;
    if (operation->hasTrait<OpTrait::IsTerminator>() ||
        operation->getName().getStringRef().starts_with("flagtree_debug."))
      return fail("Ascend census site is a marker or terminator");
  }
  auto hidden = prepareLateObservationAbi(module);
  if (!hidden)
    return hidden.takeError();
  module.getContext()->loadDialect<LLVM::LLVMDialect>();
  OpBuilder builder(module.getContext());
  builder.setInsertionPointToStart(&function.getBody().front());
  SmallVector<Value> coordinates;
  for (unsigned axis = 0; axis < 3; ++axis) {
    auto value = builder.create<triton::GetProgramIdOp>(
        function.getLoc(), static_cast<triton::ProgramIDDim>(axis));
    coordinates.push_back(builder.create<arith::ExtSIOp>(
        function.getLoc(), builder.getI64Type(), value));
  }
  for (unsigned axis = 0; axis < 3; ++axis) {
    auto value = builder.create<triton::GetNumProgramsOp>(
        function.getLoc(), static_cast<triton::ProgramIDDim>(axis));
    coordinates.push_back(builder.create<arith::ExtSIOp>(
        function.getLoc(), builder.getI64Type(), value));
  }
  for (size_t column = 0; column < selectedSites.size(); ++column) {
    const uint32_t id = selectedSites[column];
    Operation *operation = operations.at(id);
    builder.setInsertionPoint(operation);
    OperationState state(operation->getLoc(), "llvm.inline_asm");
    state.addOperands(coordinates);
    state.addAttribute("asm_string",
                       builder.getStringAttr(
                           "/* flagprism.source_census_site.v3:" +
                           std::to_string(id) + ":" + std::to_string(column) +
                           ":" + std::to_string(selectedSites.size()) + " */"));
    state.addAttribute("constraints", builder.getStringAttr("l,l,l,l,l,l"));
    state.addAttribute("has_side_effects", builder.getUnitAttr());
    auto *marker = builder.create(state);
    marker->setAttr("flagtree.profile.source_op_id",
                    builder.getI32IntegerAttr(id));
    marker->setAttr("flagtree.profile.census_column",
                    builder.getI32IntegerAttr(column));
  }
  module->setAttr("flagtree.profile.ascend_program_anchor_version",
                  builder.getI32IntegerAttr(1));
  module->setAttr("flagtree.profile.ascend_source_census_version",
                  builder.getI32IntegerAttr(3));
  module->setAttr("flagtree.debug.record_layout",
                  builder.getStringAttr("ascend_source_census_v3"));
  module->setAttr("flagtree.debug.record_size", builder.getI32IntegerAttr(8));
  module->setAttr("flagtree.debug.records_per_instance",
                  builder.getI32IntegerAttr(3 * selectedSites.size()));
  module->setAttr("flagtree.profile.ascend_source_census_columns",
                  builder.getI32IntegerAttr(selectedSites.size()));
  return *hidden;
}
} // namespace mlir::flagtree::debugger
