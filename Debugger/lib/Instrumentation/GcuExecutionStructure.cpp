#include "Debugger/Instrumentation/GcuTimeline.h"
#include "mlir/Dialect/LLVMIR/LLVMDialect.h"
#include "mlir/IR/BuiltinOps.h"
#include "mlir/Interfaces/ControlFlowInterfaces.h"
#include "mlir/Parser/Parser.h"
#include "llvm/ADT/DenseMap.h"
#include "llvm/Support/JSON.h"
#include "llvm/Support/raw_ostream.h"

namespace mlir::flagtree::debugger {
llvm::Expected<std::string> indexGcuExecutionStructure(llvm::StringRef input) {
  auto reject = [](const char *reason) -> llvm::Error {
    return llvm::createStringError(llvm::inconvertibleErrorCode(), reason);
  };
  if (input.size() > 16 * 1024 * 1024)
    return reject("GCU structure input exceeds byte budget");
  MLIRContext context;
  context.allowUnregisteredDialects();
  context.getOrLoadDialect<LLVM::LLVMDialect>();
  auto module =
      parseSourceString<ModuleOp>(input, ParserConfig(&context, false));
  if (!module)
    return reject("Cannot parse final GCU LLVM structure");
  SmallVector<LLVM::LLVMFuncOp> functions, markedFunctions;
  module->walk([&](LLVM::LLVMFuncOp function) {
    if (!function.isExternal()) {
      functions.push_back(function);
      bool hasMarker = false;
      function.walk([&](Operation *op) {
        auto location = op->getLoc()->findInstanceOf<FileLineColLoc>();
        hasMarker |=
            location && location.getFilename() == "__flagprism_gcu_clock_v1__";
      });
      if (hasMarker)
        markedFunctions.push_back(function);
    }
  });
  if (markedFunctions.size() > 1 ||
      (markedFunctions.empty() && functions.size() != 1))
    return reject(
        "GCU structure requires one unambiguous LLVM observation body");
  auto function =
      markedFunctions.empty() ? functions.front() : markedFunctions.front();
  llvm::json::Array callers;
  for (auto caller : functions) {
    caller.walk([&](LLVM::CallOp call) {
      if (call.getCallee() == function.getSymName())
        callers.push_back(caller.getSymName().str());
    });
  }
  if (function.getBody().getBlocks().size() > 8192)
    return reject("GCU structure block budget exceeded");
  llvm::DenseMap<Block *, unsigned> blockIds;
  llvm::DenseMap<Value, unsigned> valueIds;
  unsigned nextValue = 0, operations = 0;
  for (Block &block : function.getBody()) {
    blockIds[&block] = blockIds.size();
    for (auto argument : block.getArguments())
      valueIds[argument] = nextValue++;
    for (Operation &op : block) {
      if (++operations > 100000 || op.getNumRegions())
        return reject("GCU structure requires bounded flat LLVM blocks");
      for (Value result : op.getResults())
        valueIds[result] = nextValue++;
    }
  }
  auto typeText = [](Type type) {
    std::string text;
    llvm::raw_string_ostream stream(text);
    type.print(stream);
    stream.flush();
    return text;
  };
  size_t locationBytes = 0;
  llvm::json::Array blocks;
  for (Block &block : function.getBody()) {
    llvm::json::Array arguments, argumentTypes, rows;
    for (auto argument : block.getArguments()) {
      arguments.push_back(valueIds.lookup(argument));
      argumentTypes.push_back(typeText(argument.getType()));
    }
    for (Operation &op : block) {
      llvm::json::Array operands, results, resultTypes, successors;
      for (Value operand : op.getOperands()) {
        auto found = valueIds.find(operand);
        if (found == valueIds.end())
          return reject("GCU structure operand escapes indexed function");
        operands.push_back(found->second);
      }
      for (Value result : op.getResults()) {
        results.push_back(valueIds.lookup(result));
        resultTypes.push_back(typeText(result.getType()));
      }
      auto branch = dyn_cast<BranchOpInterface>(&op);
      if (op.getNumSuccessors() && !branch)
        return reject("GCU structure successor has no typed branch interface");
      for (unsigned i = 0; i < op.getNumSuccessors(); ++i) {
        Block *target = op.getSuccessor(i);
        auto found = blockIds.find(target);
        if (found == blockIds.end())
          return reject("GCU structure branch escapes indexed function");
        auto incoming = branch.getSuccessorOperands(i);
        if (incoming.getProducedOperandCount() ||
            incoming.size() != target->getNumArguments())
          return reject("GCU structure successor arguments are not forwarded");
        llvm::json::Array forwarded;
        for (Value value : incoming.getForwardedOperands())
          forwarded.push_back(valueIds.lookup(value));
        successors.push_back(llvm::json::Object{
            {"block", found->second}, {"arguments", std::move(forwarded)}});
      }
      llvm::json::Object row{{"operation", op.getName().getStringRef().str()},
                             {"operands", std::move(operands)},
                             {"results", std::move(results)},
                             {"result_types", std::move(resultTypes)},
                             {"successors", std::move(successors)}};
      if (auto call = dyn_cast<LLVM::CallOp>(&op)) {
        if (auto callee = call.getCallee())
          row["callee"] = callee->str();
      }
      if (auto compare = dyn_cast<LLVM::ICmpOp>(&op))
        row["predicate"] =
            LLVM::stringifyICmpPredicate(compare.getPredicate()).str();
      if (auto indices =
              op.getAttrOfType<DenseI32ArrayAttr>("rawConstantIndices")) {
        llvm::json::Array values;
        for (int32_t value : indices.asArrayRef())
          values.push_back(value);
        row["constant_indices"] = std::move(values);
      }
      if (auto element = op.getAttrOfType<TypeAttr>("elem_type"))
        row["element_type"] = typeText(element.getValue());
      if (auto value = op.getAttrOfType<IntegerAttr>("value")) {
        if (value.getValue().getBitWidth() <= 64) {
          row["integer_constant"] = value.getValue().getSExtValue();
          row["integer_width"] = value.getValue().getBitWidth();
        }
      }
      std::string location;
      llvm::raw_string_ostream locationStream(location);
      op.getLoc().print(locationStream);
      locationStream.flush();
      locationBytes += location.size();
      if (location.size() > 4096 || locationBytes > 8 * 1024 * 1024)
        return reject("GCU structure location budget exceeded");
      row["location"] = std::move(location);
      auto marker = op.getLoc()->findInstanceOf<FileLineColLoc>();
      if (marker && marker.getFilename() == "__flagprism_gcu_clock_v1__") {
        row["clock_marker"] = llvm::json::Object{
            {"site", marker.getLine()}, {"column", marker.getColumn()}};
      }
      rows.push_back(std::move(row));
    }
    blocks.push_back(
        llvm::json::Object{{"id", blockIds.lookup(&block)},
                           {"arguments", std::move(arguments)},
                           {"argument_types", std::move(argumentTypes)},
                           {"operations", std::move(rows)}});
  }
  llvm::json::Object report{{"schema_version", 1},
                            {"status", "typed_sdk_llvm_structure_indexed"},
                            {"function", function.getSymName().str()},
                            {"defined_callers", std::move(callers)},
                            {"entry_block", 0},
                            {"value_count", nextValue},
                            {"blocks", std::move(blocks)},
                            {"native_schedule_qualified", false},
                            {"source_region_qualified", false}};
  std::string output;
  llvm::raw_string_ostream stream(output);
  stream << llvm::json::Value(std::move(report));
  stream.flush();
  if (output.size() > 32 * 1024 * 1024)
    return reject("GCU structure output exceeds byte budget");
  return output;
}
} // namespace mlir::flagtree::debugger
