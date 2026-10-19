// Existing native controls observed by the scalar issuer. These timestamps do
// not certify non-scalar pipe completion, engine activity or cross-actor time.
#pragma once
#include "AscendSourceCensus.h"
#include "AscendTimeline.h"
#include "llvm/ADT/StringExtras.h"
#include "llvm/Support/JSON.h"
#include "llvm/Support/SHA256.h"

namespace flagprism_ascend {
template <typename Marker>
inline llvm::json::Object instrumentNativeTimeline(
    llvm::CallInst &call, const Marker &marker, llvm::Value *pointer,
    llvm::Value *actor, llvm::Value *physicalBlock, uint64_t capacity,
    uint64_t site, const std::string &block, llvm::StringRef sourceBinding) {
  using namespace llvm;
  std::string original;
  raw_string_ostream stream(original);
  call.print(stream);
  stream.flush();
  const auto name = call.getCalledFunction()->getName();
  const bool wait = name == "llvm.hivm.WAIT.FLAG.IMM";
  json::Object result{
      {"original_instructions", original},
      {"original_instructions_sha256",
       toHex(SHA256::hash(arrayRefFromStringRef(original)), true)},
      {"intrinsic", name},
      {"instrumented", false}};
  if ((!wait && name != "llvm.hivm.SET.FLAG.IMM") || call.arg_size() != 3) {
    result["reason"] = "native_primitive_not_bound_by_this_feature_version";
    return result;
  }
  json::Array arguments;
  for (Value *value : call.args()) {
    auto *constant = dyn_cast<ConstantInt>(value);
    if (!constant || constant->getBitWidth() != 64 ||
        constant->getValue().getActiveBits() > 31) {
      result["reason"] = "native_control_arguments_not_static_nonnegative_i64";
      return result;
    }
    arguments.push_back(static_cast<int64_t>(constant->getZExtValue()));
  }
  if (!site || site > UINT32_C(0x7fffffff))
    report_fatal_error("Ascend native timeline site exceeds marker encoding");
  // Capture the immediate successor after any preceding native logger was
  // inserted. The bracket surrounds this original call, never an assumed pipe
  // execution interval. Existing flags/waits are not added or rewritten.
  Instruction *next = call.getNextNode();
  if (!next)
    report_fatal_error("Ascend native control has no original successor");
  IRBuilder<> b(&call);
  Value *program = b.CreateAdd(
      marker.call->getArgOperand(0),
      b.CreateMul(marker.call->getArgOperand(3),
                  b.CreateAdd(marker.call->getArgOperand(1),
                              b.CreateMul(marker.call->getArgOperand(4),
                                          marker.call->getArgOperand(2)))));
  Value *last =
      b.CreateSub(b.CreateMul(marker.call->getArgOperand(3),
                              b.CreateMul(marker.call->getArgOperand(4),
                                          marker.call->getArgOperand(5))),
                  b.getInt64(1));
  const auto entry = timelineClockLocation(call, site, false);
  const auto exit = timelineClockLocation(call, site, true);
  Value *start = beginTimeline(&call, pointer, program, last, actor,
                               physicalBlock, capacity, entry);
  const uint32_t semantic = wait ? 3 : 2;
  endTimeline(next, pointer, program, last, actor, physicalBlock, start,
              capacity, site, semantic, exit);
  result["instrumented"] = true;
  result["site_id"] = static_cast<int64_t>(site);
  result["frontend_column"] = static_cast<int64_t>(marker.column);
  result["public_semantic"] = "source_control_interval";
  result["semantic_code"] = semantic;
  result["operation_class"] = "native_control_scalar_bracket";
  result["boundary_status"] = "unverified";
  result["scope"] = "scalar_issue_of_original_native_control";
  result["original_block"] = block;
  result["native_arguments"] = std::move(arguments);
  result["native_operation"] = wait ? "wait_flag" : "set_flag";
  result["source_binding"] = sourceBinding.str();
  result["completion_status"] = "unverified";
  result["clock_marker"] = json::Object{
      {"version", 1},
      {"file", kTimelineClockFile},
      {"entry_line", entry ? static_cast<int64_t>(entry.getLine()) : 0},
      {"exit_line", exit ? static_cast<int64_t>(exit.getLine()) : 0},
      {"status",
       entry && exit ? "debug_locations_emitted" : "missing_debug_scope"}};
  return result;
}
} // namespace flagprism_ascend
