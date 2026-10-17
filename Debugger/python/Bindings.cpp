#include "Debugger/Decode/Decoder.h"
#include "Debugger/Decode/Reporter.h"
#include "Debugger/Frontend/Bridge.h"
#include "Debugger/Metadata/TrackedOpTable.h"

#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <limits>
#include <optional>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <stdexcept>
#include <string>
#include <string_view>
#include <variant>
#include <vector>

namespace py = pybind11;

namespace {

using namespace mlir::flagtree::debugger;

std::atomic<uint64_t> nextRunId{1};

py::handle lookup(const py::dict &dict, const char *key) {
  py::str pyKey(key);
  if (!dict.contains(pyKey)) {
    return py::handle();
  }
  py::object value = dict[pyKey];
  return value.is_none() ? py::handle() : value;
}

bool getBoolOr(const py::dict &dict, const char *key, bool fallback) {
  py::handle value = lookup(dict, key);
  return value ? py::cast<bool>(value) : fallback;
}

uint32_t getUInt32Or(const py::dict &dict, const char *key, uint32_t fallback) {
  py::handle value = lookup(dict, key);
  return value ? py::cast<uint32_t>(value) : fallback;
}

uint64_t getUInt64Or(const py::dict &dict, const char *key, uint64_t fallback) {
  py::handle value = lookup(dict, key);
  return value ? py::cast<uint64_t>(value) : fallback;
}

std::string getStringOr(const py::dict &dict, const char *key,
                        std::string_view fallback) {
  py::handle value = lookup(dict, key);
  return value ? py::cast<std::string>(value) : std::string(fallback);
}

std::vector<int64_t> castInt64Vector(py::handle value) {
  if (!value || value.is_none()) {
    return {};
  }
  return py::cast<std::vector<int64_t>>(value);
}

uint32_t getSequenceUInt32(py::handle value, size_t index, uint32_t fallback) {
  if (!value || value.is_none() || !py::isinstance<py::sequence>(value)) {
    return fallback;
  }
  py::sequence sequence = py::reinterpret_borrow<py::sequence>(value);
  if (index >= static_cast<size_t>(sequence.size())) {
    return fallback;
  }
  int64_t dim = py::cast<int64_t>(sequence[index]);
  if (dim <= 0 ||
      static_cast<uint64_t>(dim) > std::numeric_limits<uint32_t>::max()) {
    throw std::invalid_argument(
        "launch grid dimension must be positive and fit uint32_t");
  }
  return static_cast<uint32_t>(dim);
}

std::string toLower(std::string_view input) {
  std::string result;
  result.reserve(input.size());
  for (char ch : input) {
    if (ch >= 'A' && ch <= 'Z') {
      result.push_back(static_cast<char>(ch - 'A' + 'a'));
    } else {
      result.push_back(ch);
    }
  }
  return result;
}

RecordLevel parseRecordLevel(py::handle value) {
  if (!value || value.is_none()) {
    return RecordLevel::LEVEL_SUMMARY;
  }
  if (py::isinstance<py::int_>(value)) {
    int64_t level = py::cast<int64_t>(value);
    if (level == 1)
      return RecordLevel::LEVEL_SUMMARY;
    if (level == 2)
      return RecordLevel::LEVEL_TENSOR_FULL;
    throw py::value_error("debugger record_level must be 1 or 2");
  }
  std::string lowered = toLower(py::cast<std::string>(py::str(value)));
  if (lowered == "level_tensor_full" || lowered == "tensor_full" ||
      lowered == "full" || lowered == "2") {
    return RecordLevel::LEVEL_TENSOR_FULL;
  }
  if (lowered == "level_summary" || lowered == "summary" || lowered == "1")
    return RecordLevel::LEVEL_SUMMARY;
  throw py::value_error("debugger record_level must be 1 or 2");
}

ExportMode parseExportMode(py::handle value) {
  if (!value || value.is_none()) {
    return ExportMode::POST_KERNEL_EXPORT;
  }
  if (py::isinstance<py::int_>(value)) {
    return py::cast<uint32_t>(value) == 2 ? ExportMode::STREAMING_EXPORT
                                          : ExportMode::POST_KERNEL_EXPORT;
  }
  std::string lowered = toLower(py::cast<std::string>(py::str(value)));
  if (lowered == "streaming_export" || lowered == "streaming") {
    return ExportMode::STREAMING_EXPORT;
  }
  return ExportMode::POST_KERNEL_EXPORT;
}

BackendKind parseBackendKind(std::string_view backendName) {
  std::string lowered = toLower(backendName);
  if (lowered == "cuda" || lowered == "nvidia") {
    return BackendKind::CUDA;
  }
  if (lowered == "hip" || lowered == "rocm" || lowered == "amd") {
    return BackendKind::HIP;
  }
  if (lowered == "musa" || lowered == "mthreads") {
    return BackendKind::MUSA;
  }
  if (lowered == "cann" || lowered == "ascend" || lowered == "npu") {
    return BackendKind::CANN;
  }
  if (lowered == "tianshu" || lowered == "corex" || lowered == "iluvatar") {
    return BackendKind::TIANSHU;
  }
  if (lowered == "enflame" || lowered == "gcu" || lowered == "tops") {
    return BackendKind::ENFLAME;
  }
  return BackendKind::UNKNOWN;
}

uint64_t checkedMulU64(uint64_t lhs, uint64_t rhs, const char *what) {
  if (lhs != 0 && rhs > std::numeric_limits<uint64_t>::max() / lhs) {
    throw std::overflow_error(std::string(what) + " overflows uint64_t");
  }
  return lhs * rhs;
}

uint64_t launchGridProduct(const DebugRuntimeMetadata &metadata) {
  if (!metadata.hasLaunchGrid)
    throw std::invalid_argument(
        "level-2 debugger full dump requires launch grid metadata");
  uint64_t product =
      checkedMulU64(metadata.gridX, metadata.gridY, "debug launch grid");
  return checkedMulU64(product, metadata.gridZ, "debug launch grid");
}

BufferRegistrationInfo parseBufferRegistrationInfo(const py::dict &dict) {
  BufferRegistrationInfo info;
  info.bufferId = getUInt32Or(dict, "buffer_id", 0);
  info.bufferName = getStringOr(dict, "buffer_name", "");
  info.baseAddress = getUInt64Or(dict, "base_address", 0);
  info.sizeBytes = getUInt64Or(dict, "size_bytes", 0);
  info.alignment = getUInt32Or(dict, "alignment", 0);
  return info;
}

LaunchTensorInfo parseLaunchTensorInfo(const py::dict &dict) {
  LaunchTensorInfo info;
  info.argumentIndex = getUInt32Or(dict, "argument_index", 0);
  info.logicalName = getStringOr(dict, "logical_name", "");
  info.dtype = getStringOr(dict, "dtype", "");
  info.shape = castInt64Vector(lookup(dict, "shape"));
  info.stride = castInt64Vector(lookup(dict, "stride"));
  info.layout = getStringOr(dict, "layout", "");
  info.bufferId = getUInt32Or(dict, "buffer_id", 0);
  info.baseAddress = getUInt64Or(dict, "base_address", 0);
  info.sizeBytes = getUInt64Or(dict, "size_bytes", 0);
  return info;
}

DebugRecordPlanEntry parseDebugRecordPlanEntry(const py::dict &dict) {
  DebugRecordPlanEntry entry;
  entry.recordIndex = getUInt32Or(dict, "record_index", 0);
  entry.opId = getUInt32Or(dict, "op_id", 0);
  entry.scopeId = getUInt32Or(dict, "scope_id", kInvalidScopeId);
  entry.recordKind =
      static_cast<RecordKind>(getUInt32Or(dict, "record_kind", 0));
  entry.collectorKind =
      static_cast<CollectorKind>(getUInt32Or(dict, "collector_kind", 0));
  entry.resultType =
      static_cast<ResultType>(getUInt32Or(dict, "result_type", 0));
  entry.eventKind =
      static_cast<MemoryEventKind>(getUInt32Or(dict, "event_kind", 0));
  return entry;
}

FullDumpArtifactInfo parseFullDumpArtifactInfo(const py::dict &dict) {
  FullDumpArtifactInfo info;
  info.opId = getUInt32Or(dict, "op_id", 0);
  info.logicalInstanceId = getUInt64Or(dict, "logical_instance_id", 0);
  info.payloadOffset = getUInt32Or(dict, "payload_offset", 0);
  info.payloadLength = getUInt32Or(dict, "payload_length", 0);
  info.kind = getStringOr(dict, "kind", "");
  info.path = getStringOr(dict, "path", "");
  return info;
}

DebugRuntimeMetadata parseRuntimeMetadata(py::handle value) {
  DebugRuntimeMetadata runtimeMetadata;
  if (!value || value.is_none()) {
    return runtimeMetadata;
  }

  py::dict dict = py::cast<py::dict>(value);

  py::handle buffers = lookup(dict, "buffers");
  if (buffers && !buffers.is_none()) {
    for (py::handle item : py::cast<py::list>(buffers)) {
      runtimeMetadata.buffers.push_back(
          parseBufferRegistrationInfo(py::cast<py::dict>(item)));
    }
  }

  py::handle tensors = lookup(dict, "tensors");
  if (tensors && !tensors.is_none()) {
    for (py::handle item : py::cast<py::list>(tensors)) {
      runtimeMetadata.tensors.push_back(
          parseLaunchTensorInfo(py::cast<py::dict>(item)));
    }
  }

  py::handle grid = lookup(dict, "grid");
  if (grid && !grid.is_none()) {
    runtimeMetadata.hasLaunchGrid = true;
    runtimeMetadata.gridX = getSequenceUInt32(grid, 0, 1);
    runtimeMetadata.gridY = getSequenceUInt32(grid, 1, 1);
    runtimeMetadata.gridZ = getSequenceUInt32(grid, 2, 1);
  }
  runtimeMetadata.recordsPerInstance =
      getUInt32Or(dict, "records_per_instance", 0);
  runtimeMetadata.recordLayout = getStringOr(dict, "record_layout", "");
  py::handle inactiveSlots = lookup(dict, "inactive_record_slots");
  if (inactiveSlots && !inactiveSlots.is_none())
    runtimeMetadata.inactiveRecordSlots =
        py::cast<std::vector<uint32_t>>(inactiveSlots);
  py::handle recordPlan = lookup(dict, "record_plan");
  if (recordPlan && !recordPlan.is_none()) {
    for (py::handle item : py::cast<py::list>(recordPlan)) {
      runtimeMetadata.recordPlan.push_back(
          parseDebugRecordPlanEntry(py::cast<py::dict>(item)));
    }
  }
  py::handle fullDumpArtifacts = lookup(dict, "full_dump_artifacts");
  if (fullDumpArtifacts && !fullDumpArtifacts.is_none()) {
    for (py::handle item : py::cast<py::list>(fullDumpArtifacts)) {
      runtimeMetadata.fullDumpArtifacts.push_back(
          parseFullDumpArtifactInfo(py::cast<py::dict>(item)));
    }
  }

  return runtimeMetadata;
}

py::dict toPyBufferMeta(const BufferMeta &meta) {
  py::dict dict;
  dict["run_id"] = meta.runId;
  dict["device_id"] = meta.deviceId;
  dict["kernel_id"] = meta.kernelId;
  dict["protocol_version"] = meta.protocolVer;
  dict["record_level"] = static_cast<uint32_t>(meta.recordLevel);
  dict["export_mode"] = static_cast<uint32_t>(meta.exportMode);
  dict["backend_kind"] = static_cast<uint32_t>(meta.backendKind);
  return dict;
}

BufferMeta parseBufferMeta(const py::dict &dict) {
  BufferMeta meta{};
  meta.runId = getUInt64Or(dict, "run_id", 0);
  meta.deviceId = getUInt32Or(dict, "device_id", 0);
  meta.kernelId = getUInt32Or(dict, "kernel_id", 0);
  meta.protocolVer = static_cast<uint16_t>(
      getUInt32Or(dict, "protocol_version", kProtocolVersion));
  meta.recordLevel = parseRecordLevel(lookup(dict, "record_level"));
  meta.exportMode = parseExportMode(lookup(dict, "export_mode"));
  meta.backendKind =
      static_cast<BackendKind>(getUInt32Or(dict, "backend_kind", 0));
  return meta;
}

py::dict toPyRuntimeMetadata(const DebugRuntimeMetadata &runtimeMetadata) {
  py::dict dict;
  dict["inactive_record_slots"] = runtimeMetadata.inactiveRecordSlots;

  py::list buffers;
  for (const auto &buffer : runtimeMetadata.buffers) {
    py::dict entry;
    entry["buffer_id"] = buffer.bufferId;
    entry["buffer_name"] = buffer.bufferName;
    entry["base_address"] = buffer.baseAddress;
    entry["size_bytes"] = buffer.sizeBytes;
    entry["alignment"] = buffer.alignment;
    buffers.append(entry);
  }
  dict["buffers"] = std::move(buffers);

  py::list tensors;
  for (const auto &tensor : runtimeMetadata.tensors) {
    py::dict entry;
    entry["argument_index"] = tensor.argumentIndex;
    entry["logical_name"] = tensor.logicalName;
    entry["dtype"] = tensor.dtype;
    entry["shape"] = tensor.shape;
    entry["stride"] = tensor.stride;
    entry["layout"] = tensor.layout;
    entry["buffer_id"] = tensor.bufferId;
    entry["base_address"] = tensor.baseAddress;
    entry["size_bytes"] = tensor.sizeBytes;
    tensors.append(entry);
  }
  dict["tensors"] = std::move(tensors);
  if (runtimeMetadata.hasLaunchGrid) {
    dict["grid"] = py::make_tuple(runtimeMetadata.gridX, runtimeMetadata.gridY,
                                  runtimeMetadata.gridZ);
  }
  dict["records_per_instance"] = runtimeMetadata.recordsPerInstance;
  dict["record_layout"] = runtimeMetadata.recordLayout;
  py::list recordPlan;
  for (const auto &entry : runtimeMetadata.recordPlan) {
    py::dict planEntry;
    planEntry["record_index"] = entry.recordIndex;
    planEntry["op_id"] = entry.opId;
    planEntry["scope_id"] = entry.scopeId;
    planEntry["record_kind"] = static_cast<uint32_t>(entry.recordKind);
    planEntry["collector_kind"] = static_cast<uint32_t>(entry.collectorKind);
    planEntry["result_type"] = static_cast<uint32_t>(entry.resultType);
    planEntry["event_kind"] = static_cast<uint32_t>(entry.eventKind);
    recordPlan.append(planEntry);
  }
  dict["record_plan"] = std::move(recordPlan);

  py::list fullDumpArtifacts;
  for (const auto &artifact : runtimeMetadata.fullDumpArtifacts) {
    py::dict entry;
    entry["op_id"] = artifact.opId;
    entry["logical_instance_id"] = artifact.logicalInstanceId;
    entry["payload_offset"] = artifact.payloadOffset;
    entry["payload_length"] = artifact.payloadLength;
    entry["kind"] = artifact.kind;
    entry["path"] = artifact.path;
    fullDumpArtifacts.append(entry);
  }
  dict["full_dump_artifacts"] = std::move(fullDumpArtifacts);

  return dict;
}

py::dict toPyRingBufferHeader(const RingBufferHeader &header) {
  py::dict dict;
  dict["write_idx"] = header.writeIdx;
  dict["capacity"] = header.capacity;
  dict["overflow_count"] = header.overflowCount;
  dict["flags"] = header.flags;
  dict["record_size"] = header.recordSize;
  dict["payload_offset"] = header.payloadOffset;
  dict["reserved0"] = header.reserved0;
  dict["reserved1"] = header.reserved1;
  return dict;
}

py::dict toPyExportedRun(const DebugExportedRun &run) {
  py::dict dict;
  dict["meta"] = toPyBufferMeta(run.meta);
  dict["runtime_metadata"] = toPyRuntimeMetadata(run.runtimeMetadata);
  dict["raw_buffer"] =
      py::bytes(reinterpret_cast<const char *>(run.rawBuffer.data()),
                static_cast<py::ssize_t>(run.rawBuffer.size()));
  return dict;
}

DebugExportedRun parseExportedRun(const py::dict &dict) {
  DebugExportedRun run;
  py::handle meta = lookup(dict, "meta");
  if (meta && !meta.is_none()) {
    run.meta = parseBufferMeta(py::cast<py::dict>(meta));
  }

  py::handle runtimeMetadata = lookup(dict, "runtime_metadata");
  run.runtimeMetadata = parseRuntimeMetadata(runtimeMetadata);

  py::handle rawBuffer = lookup(dict, "raw_buffer");
  if (rawBuffer && !rawBuffer.is_none()) {
    py::bytes bytes = py::cast<py::bytes>(rawBuffer);
    std::string data = bytes;
    run.rawBuffer.assign(data.begin(), data.end());
  }
  return run;
}

void parseReportInputs(const py::dict &exportedRun,
                       const std::string &metadataJson,
                       DecodedDebugRun &decoded,
                       KernelDebugMetadata &metadata) {
  DebugExportedRun run = parseExportedRun(exportedRun);
  std::string errorMessage;
  if (!decodeExportedRun(run, decoded, &errorMessage)) {
    throw py::value_error(errorMessage);
  }
  if (!parseKernelDebugMetadataFromJson(metadataJson, metadata,
                                        &errorMessage)) {
    throw py::value_error(errorMessage);
  }
}

ReportOptions makeStatementReportOptions() {
  ReportOptions options;
  options.includeDynamicRecords = true;
  options.includeStaticMetadata = false;
  options.includeAggregates = false;
  options.includeStatementRecords = true;
  options.includeOpLog = false;
  options.includeReportHeader = false;
  return options;
}

ReportOptions makeOpLogReportOptions() {
  ReportOptions options;
  options.includeDynamicRecords = true;
  options.includeStaticMetadata = true;
  options.includeAggregates = false;
  options.includeStatementRecords = false;
  options.includeOpLog = true;
  options.includeReportHeader = false;
  return options;
}

py::dict toPyDecodedRecord(const DecodedRecord &record) {
  py::dict dict;
  if (const auto *summary = std::get_if<DecodedSummaryRecord>(&record)) {
    const auto &raw = summary->raw;
    dict["record_kind"] = "SUMMARY";
    dict["op_id"] = raw.header.opId;
    dict["logical_instance_id"] = raw.header.logicalInstanceId;
    dict["collector_kind"] = static_cast<uint32_t>(raw.collectorKind);
    dict["result_type"] = static_cast<uint32_t>(raw.resultType);
    dict["u64_value"] = raw.resultData.u64Val;
    dict["f32_value"] = raw.resultData.f32Val;
    dict["f64_value"] = raw.resultData.f64Val;
    return dict;
  }
  if (const auto *bundle =
          std::get_if<DecodedSummaryCountBundleRecord>(&record)) {
    const auto &raw = bundle->raw;
    dict["record_kind"] = "SUMMARY_COUNT_BUNDLE_U64";
    dict["op_id"] = raw.header.opId;
    dict["logical_instance_id"] = raw.header.logicalInstanceId;
    dict["nan_count"] = raw.nanCount;
    dict["inf_count"] = raw.infCount;
    dict["zero_count"] = raw.zeroCount;
    dict["element_count"] = raw.elementCount;
    return dict;
  }
  if (const auto *bundle =
          std::get_if<DecodedSummaryValueBundleRecord>(&record)) {
    const auto &raw = bundle->raw;
    dict["record_kind"] = "SUMMARY_VALUE_BUNDLE_F32";
    dict["op_id"] = raw.header.opId;
    dict["logical_instance_id"] = raw.header.logicalInstanceId;
    dict["mean"] = raw.meanFinite;
    dict["min"] = raw.minFinite;
    dict["max"] = raw.maxFinite;
    dict["l2_norm"] = raw.l2Norm;
    return dict;
  }
  if (const auto *memory = std::get_if<DecodedMemoryEventRecord>(&record)) {
    const auto &raw = memory->raw;
    dict["record_kind"] = "MEMORY_EVENT";
    dict["op_id"] = raw.header.opId;
    dict["logical_instance_id"] = raw.header.logicalInstanceId;
    dict["addr"] = raw.addr;
    dict["event_kind"] = static_cast<uint32_t>(raw.eventKind);
    dict["ext0"] = raw.ext0;
    return dict;
  }
  if (const auto *timeline = std::get_if<DecodedTimelineRecord>(&record)) {
    const auto &raw = timeline->raw;
    dict["record_kind"] = "TIMELINE";
    dict["op_id"] = raw.header.opId;
    dict["logical_instance_id"] = raw.header.logicalInstanceId;
    dict["start_cycle"] = raw.startCycle;
    dict["end_cycle"] = raw.endCycle;
    dict["duration_cycle"] = raw.durationCycle;
    return dict;
  }
  if (const auto *timeline =
          std::get_if<DecodedDynamicTimelineRecord>(&record)) {
    const auto &raw = timeline->raw;
    dict["record_kind"] = "DYNAMIC_TIMELINE";
    dict["op_id"] = raw.header.opId;
    dict["logical_instance_id"] = raw.header.logicalInstanceId;
    dict["start_cycle"] = raw.startCycle;
    dict["end_cycle"] = raw.endCycle;
    dict["duration_cycle"] = raw.durationCycle;
    dict["actor_id"] = raw.actorId;
    dict["sequence"] = raw.sequence;
    dict["attempted_ordinal"] = raw.attemptedOrdinal;
    dict["commit_tag"] = raw.commitTag;
    return dict;
  }
  const auto &raw = std::get<DecodedFullValueRefRecord>(record).raw;
  dict["record_kind"] = "FULL_VALUE";
  dict["op_id"] = raw.header.opId;
  dict["logical_instance_id"] = raw.header.logicalInstanceId;
  dict["payload_offset"] = raw.payloadOffset;
  dict["payload_length"] = raw.payloadLength;
  return dict;
}

py::dict toPyDecodedRun(const DecodedDebugRun &run) {
  py::dict dict;
  dict["meta"] = toPyBufferMeta(run.meta);
  dict["header"] = toPyRingBufferHeader(run.header);
  dict["runtime_metadata"] = toPyRuntimeMetadata(run.runtimeMetadata);

  py::list records;
  for (const auto &record : run.records)
    records.append(toPyDecodedRecord(record));
  dict["records"] = std::move(records);
  return dict;
}

class PreparedLaunchHandle {
public:
  PreparedLaunchHandle(const py::dict &metadata, uint64_t streamHandle,
                       py::handle runtimeMetadataValue, bool initialize = true) {
    auto bridge = createFrontendBridge();

    DebugCompileRequest compileRequest;
    compileRequest.kernelName = getStringOr(metadata, "debug_kernel_name",
                                            getStringOr(metadata, "name", ""));
    compileRequest.backendName =
        getStringOr(metadata, "debug_backend_name",
                    getStringOr(metadata, "backend_name", ""));
    compileRequest.targetName = getStringOr(metadata, "debug_target_name",
                                            getStringOr(metadata, "arch", ""));
    compileRequest.options.enabled = getBoolOr(metadata, "debug_enabled", true);
    compileRequest.options.recordLevel =
        parseRecordLevel(lookup(metadata, "debug_record_level"));
    compileRequest.options.exportMode =
        parseExportMode(lookup(metadata, "debug_export_mode"));
    compileRequest.options.recordCapacity =
        getUInt32Or(metadata, "debug_record_capacity", 1024);
    compileRequest = bridge->normalizeCompileRequest(compileRequest);

    KernelDebugMetadata kernelMetadata;
    kernelMetadata.debugKernelId = getUInt32Or(metadata, "debug_kernel_id", 1);
    kernelMetadata.kernelName = compileRequest.kernelName;
    kernelMetadata.backendName = compileRequest.backendName;
    kernelMetadata.targetName = compileRequest.targetName;

    DebugRuntimeMetadata runtimeMetadata =
        parseRuntimeMetadata(runtimeMetadataValue);
    const auto compiledCensusLayout =
        getStringOr(metadata, "debug_record_layout", "");
    const auto isAscendCensus = [](const std::string &layout) {
      return layout == "ascend_source_census_v1" ||
             layout == "ascend_source_census_v2" ||
             layout == "ascend_source_census_v3";
    };
    if (isAscendCensus(runtimeMetadata.recordLayout) ||
        isAscendCensus(compiledCensusLayout)) {
      const bool aligned = compiledCensusLayout == "ascend_source_census_v3";
      const bool compact = aligned || compiledCensusLayout == "ascend_source_census_v2";
      const uint32_t version = aligned ? 3 : compact ? 2 : 1;
      const uint32_t columns =
          compact ? getUInt32Or(metadata, "debug_census_columns", 0) : 128;
      if (!isAscendCensus(compiledCensusLayout) ||
          runtimeMetadata.recordLayout != compiledCensusLayout || !columns ||
          columns > 128 ||
          getUInt32Or(metadata, "debug_census_version", 0) != version ||
          getUInt32Or(metadata, "debug_record_size", 0) != 8 ||
          getUInt32Or(metadata, "debug_records_per_instance", 0) !=
              3 * columns ||
          runtimeMetadata.recordsPerInstance != 3 * columns ||
          !runtimeMetadata.hasLaunchGrid)
        throw std::invalid_argument("Ascend census requires actual grid and "
                                    "matching compiler physical layout");
      if (compact) {
        if (!metadata.contains("debug_census_columns") ||
            !PyLong_CheckExact(metadata["debug_census_columns"].ptr()) ||
            !metadata.contains("debug_ascend_census_sites") ||
            !py::isinstance<py::list>(metadata["debug_ascend_census_sites"]) ||
            py::len(metadata["debug_ascend_census_sites"]) != columns ||
            !metadata.contains("debug_ascend_census_abi") ||
            !py::isinstance<py::dict>(metadata["debug_ascend_census_abi"]))
          throw std::invalid_argument(
              "Ascend census v2 requires the actual frontend column inventory");
        auto abi = metadata["debug_ascend_census_abi"].cast<py::dict>();
        if (getUInt32Or(abi, "version", 0) != version ||
            getUInt32Or(abi, "site_count", 0) != columns ||
            getUInt32Or(abi, "record_size", 0) != 8 ||
            getUInt32Or(abi, "records_per_instance", 0) != 3 * columns ||
            getStringOr(abi, "record_layout", "") != compiledCensusLayout)
          throw std::invalid_argument("Ascend census v2 native frontend ABI "
                                      "conflicts with compiler metadata");
      }
      const uint64_t actorCells = aligned ? ((columns + 7) / 8) * 8 : columns;
      uint64_t cells = checkedMulU64(launchGridProduct(runtimeMetadata),
                                     3 * actorCells, "Ascend census cells");
      // V3 cell budgets include the complete 64-byte header and all actor
      // padding. The shared runtime allocator contributes its original 32-byte
      // prefix, so reserve four fewer payload cells than the total cell budget.
      if (aligned) {
        if (cells > std::numeric_limits<uint64_t>::max() - 8)
          throw std::invalid_argument("Ascend census header cell overflow");
        cells += 8;
      }
      if (cells > std::numeric_limits<uint32_t>::max())
        throw std::invalid_argument(
            "Ascend census grid exceeds native cell index range");
      uint64_t bytes =
          (aligned ? 0 : 32) + checkedMulU64(cells, 8, "Ascend physical census bytes");
      if (cells > getUInt64Or(metadata, "debug_max_census_cells", 0) ||
          bytes > getUInt64Or(metadata, "debug_max_census_bytes", 0) ||
          bytes > static_cast<uint64_t>(std::numeric_limits<int32_t>::max()))
        throw std::invalid_argument("Ascend census actual grid exceeds "
                                    "physical cell/byte/index budgets");
      compileRequest.options.recordCapacity = static_cast<uint32_t>(aligned ? cells - 4 : cells);
    }
    if (runtimeMetadata.recordLayout == "gcu_site_census_v1" ||
        compiledCensusLayout == "gcu_site_census_v1") {
      if (compiledCensusLayout != "gcu_site_census_v1" ||
          runtimeMetadata.recordLayout != compiledCensusLayout ||
          getUInt32Or(metadata, "debug_census_version", 0) != 1 ||
          getUInt32Or(metadata, "debug_record_size", 0) != 64 ||
          !runtimeMetadata.hasLaunchGrid ||
          runtimeMetadata.recordsPerInstance == 0)
        throw std::invalid_argument(
            "GCU census requires actual grid and matching compiler layout");
      uint32_t compiledSites =
          getUInt32Or(metadata, "debug_records_per_instance", 0);
      py::handle censusSites = lookup(metadata, "debug_census_sites");
      if (compiledSites == 0 || compiledSites > 128 ||
          runtimeMetadata.recordsPerInstance != compiledSites || !censusSites ||
          !py::isinstance<py::list>(censusSites) ||
          py::len(censusSites) != compiledSites)
        throw std::invalid_argument(
            "GCU census runtime stride contradicts actual compiler sites");
      uint64_t programs = launchGridProduct(runtimeMetadata);
      uint64_t cells = checkedMulU64(
          programs, runtimeMetadata.recordsPerInstance, "GCU census cells");
      uint64_t bytes = 32 + checkedMulU64(cells, 64, "GCU census bytes");
      if (programs == 0 || programs > std::numeric_limits<uint32_t>::max() ||
          cells > getUInt64Or(metadata, "debug_max_census_cells", 0) ||
          bytes > getUInt64Or(metadata, "debug_max_census_bytes", 0) ||
          bytes > static_cast<uint64_t>(std::numeric_limits<int32_t>::max()))
        throw std::invalid_argument(
            "GCU census actual grid exceeds cell/byte/index budget");
      compileRequest.options.recordCapacity = static_cast<uint32_t>(cells);
    }
    if (runtimeMetadata.recordLayout == "ascend_actor_dynamic_v1" ||
        getStringOr(metadata, "debug_record_layout", "") ==
            "ascend_actor_dynamic_v1") {
      const uint64_t actorCapacity =
          getUInt64Or(metadata, "flagprism_ascend_trace_capacity", 0);
      if (!actorCapacity ||
          actorCapacity > (std::numeric_limits<uint32_t>::max() - 1) / 3)
        throw std::invalid_argument(
            "Ascend dynamic trace requires a valid per-actor capacity");
      if (getStringOr(metadata, "debug_record_layout", "") !=
              "ascend_actor_dynamic_v1" ||
          runtimeMetadata.recordLayout != "ascend_actor_dynamic_v1")
        throw std::invalid_argument(
            "Ascend dynamic trace layout metadata is inconsistent");
      if (getUInt32Or(metadata, "debug_record_size", 0) != 64)
        throw std::invalid_argument(
            "Ascend dynamic trace requires 64-byte records");
      // TransferEngine allocates a 32-byte ring header plus 64-byte slots.
      // Three actor headers and payload regions need 96 + 192*C bytes:
      // total slot capacity must therefore be exactly 3*C + 1. Validate
      // before any device allocation, even for stale/corrupted cached metadata.
      if (getUInt64Or(metadata, "debug_record_capacity", 0) !=
          3 * actorCapacity + 1)
        throw std::invalid_argument(
            "Ascend dynamic trace allocation capacity must equal "
            "3 * per-actor capacity + 1; rebuild stale kernel metadata");
    }
    if (runtimeMetadata.recordLayout == "selected_dynamic_timeline_v1" ||
        runtimeMetadata.recordLayout == "gcu_first_last_timeline_v2" ||
        runtimeMetadata.recordLayout == "ascend_actor_dynamic_v1") {
      // Legacy snapshots retain their minimum allocation. Dynamic capacity is
      // explicit and must not be silently raised by normalizeCompileRequest.
      compileRequest.options.recordCapacity =
          getUInt32Or(metadata, "debug_record_capacity", 1024);
      if (compileRequest.options.recordCapacity == 0)
        throw std::invalid_argument("dynamic trace capacity must be positive");
    }
    if (getUInt32Or(metadata, "debug_dynamic_index_bits", 0) == 32) {
      // The bounded GCU writer uses signed pointer offsets and unsigned flat
      // program ids. Validate the actual launch before allocating any buffer;
      // compile-time selection alone cannot establish these runtime bounds.
      const bool firstLast = runtimeMetadata.recordLayout == "gcu_first_last_timeline_v2";
      if ((!firstLast && runtimeMetadata.recordLayout != "selected_dynamic_timeline_v1") ||
          getStringOr(metadata, "debug_clock_carrier", "") !=
              "llvm_i64_words" ||
          getUInt32Or(metadata, "debug_record_size", 0) != 64)
        throw std::invalid_argument("bounded dynamic indexing requires "
                                    "selected_dynamic_timeline_v1, 64-byte "
                                    "records and llvm_i64_words clock carrier");
      py::dict runtimeDict = runtimeMetadataValue.is_none()
                                 ? py::dict()
                                 : py::cast<py::dict>(runtimeMetadataValue);
      py::handle grid = lookup(runtimeDict, "grid");
      if (!grid || !py::isinstance<py::sequence>(grid))
        throw std::invalid_argument(
            "bounded dynamic indexing requires actual launch grid metadata");
      auto dimensions = py::reinterpret_borrow<py::sequence>(grid);
      if (dimensions.size() < 1 || dimensions.size() > 3)
        throw std::invalid_argument(
            "bounded dynamic launch grid requires one to three dimensions");
      constexpr uint64_t signedLimit = std::numeric_limits<int32_t>::max();
      if (runtimeMetadata.gridX > signedLimit ||
          runtimeMetadata.gridY > signedLimit ||
          runtimeMetadata.gridZ > signedLimit)
        throw std::invalid_argument(
            "bounded dynamic launch grid dimension exceeds INT32_MAX");
      if (launchGridProduct(runtimeMetadata) >
          std::numeric_limits<uint32_t>::max())
        throw std::invalid_argument(
            "bounded dynamic launch grid product exceeds UINT32_MAX");
      const uint64_t bufferBytes =
          32 + checkedMulU64(compileRequest.options.recordCapacity, 64,
                             "bounded dynamic record area");
      if (bufferBytes > signedLimit)
        throw std::invalid_argument(
            "bounded dynamic trace buffer exceeds INT32_MAX pointer offsets");
      if (firstLast) {
        if (getStringOr(metadata, "debug_dynamic_program_policy", "") != "runtime_first_last" ||
            getUInt32Or(metadata, "debug_dynamic_storage_version", 0) != 2 ||
            getUInt32Or(metadata, "debug_dynamic_slot_bytes", 0) != bufferBytes ||
            !compileRequest.options.recordCapacity || compileRequest.options.recordCapacity > 16384 ||
            launchGridProduct(runtimeMetadata) == 0 || launchGridProduct(runtimeMetadata) > signedLimit)
          throw std::invalid_argument("GCU first/last manifest/storage mismatch");
      } else {
      if (!lookup(metadata, "debug_dynamic_selected_program"))
        throw std::invalid_argument(
            "bounded dynamic indexing requires an explicit selected program");
      if (getUInt64Or(metadata, "debug_dynamic_selected_program", 0) >
          signedLimit)
        throw std::invalid_argument(
            "bounded dynamic selected program exceeds INT32_MAX");
      }
      // A selected id outside the grid intentionally collects no records.
      // Do not reject that supported ablation or silently narrow the id.
    }

    DebugKernelArtifacts artifacts;
    bridge->attachKernelMetadata(compileRequest, artifacts, kernelMetadata);
    artifacts.metadataJson = getStringOr(metadata, "debug_metadata_json", "");
    artifacts.bufferPlan.recordSize = getUInt32Or(
        metadata, "debug_record_size", artifacts.bufferPlan.recordSize);
    if (isAscendCensus(runtimeMetadata.recordLayout))
      artifacts.bufferPlan.recordCapacity =
          compileRequest.options.recordCapacity;
    uint64_t fullDumpPayloadBytesPerInstance =
        getUInt64Or(metadata, "debug_full_dump_payload_bytes_per_instance", 0);
    if (fullDumpPayloadBytesPerInstance != 0) {
      uint64_t gridProduct = launchGridProduct(runtimeMetadata);
      uint64_t requiredRecords =
          checkedMulU64(gridProduct, runtimeMetadata.recordsPerInstance,
                        "level-2 debug record count");
      if (requiredRecords > artifacts.bufferPlan.recordCapacity) {
        throw std::invalid_argument(
            "level-2 debugger full dump requires debug_record_capacity >= "
            "grid_product * records_per_instance");
      }
      uint64_t payloadBytes =
          checkedMulU64(gridProduct, fullDumpPayloadBytesPerInstance,
                        "level-2 debug payload bytes");
      uint64_t totalBytes = static_cast<uint64_t>(sizeof(RingBufferHeader)) +
                            checkedMulU64(artifacts.bufferPlan.recordCapacity,
                                          artifacts.bufferPlan.recordSize,
                                          "debug record area bytes") +
                            payloadBytes;
      if (totalBytes > std::numeric_limits<uint32_t>::max()) {
        throw std::invalid_argument("level-2 debugger full dump buffer must "
                                    "fit 32-bit payload offsets");
      }
      artifacts.bufferPlan.payloadBytes = static_cast<size_t>(payloadBytes);
    }

    BufferMeta bufferMeta{};
    bufferMeta.runId =
        getUInt64Or(metadata, "debug_run_id",
                    nextRunId.fetch_add(1, std::memory_order_relaxed));
    bufferMeta.deviceId = getUInt32Or(metadata, "debug_device_id", 0);
    bufferMeta.kernelId = kernelMetadata.debugKernelId;
    bufferMeta.protocolVer = static_cast<uint16_t>(
        getUInt32Or(metadata, "debug_protocol_version", kProtocolVersion));
    bufferMeta.recordLevel =
        parseRecordLevel(lookup(metadata, "debug_record_level"));
    bufferMeta.exportMode =
        parseExportMode(lookup(metadata, "debug_export_mode"));
    bufferMeta.backendKind = parseBackendKind(compileRequest.backendName);

    prepared_.emplace(bridge->prepareOwnedLaunch(
        artifacts, bufferMeta, runtimeMetadata, streamHandle, initialize));
    initialized_ = initialize;
  }

  ~PreparedLaunchHandle() noexcept {
    try {
      releaseInternal();
    } catch (const std::exception &error) {
      // Python may destroy the handle while another SDK exception is active.
      // Destructors must never replace that exception with std::terminate.
      std::fprintf(stderr, "FlagPrism debugger handle cleanup: %s\n",
                   error.what());
    }
  }

  uint64_t hiddenArgValue() const {
    ensurePrepared();
    return prepared_->request.hiddenArgValue;
  }

  py::dict bufferMeta() const {
    ensurePrepared();
    return toPyBufferMeta(prepared_->request.bufferMeta);
  }

  py::dict runtimeMetadata() const {
    ensurePrepared();
    return toPyRuntimeMetadata(prepared_->request.runtimeMetadata);
  }

  void initialize() {
    ensurePrepared();
    if (initialized_)
      throw py::value_error("debugger launch initialization is not repeatable");
    initialized_ = true; // May submit writes before throwing; owner must retain.
    prepared_->transferEngine->initHeader(prepared_->request.launchContext);
  }

  py::dict readRaw() {
    ensurePrepared();
    if (!initialized_)
      throw py::value_error("debugger launch buffer was not initialized");
    return toPyExportedRun(prepared_->transferEngine->syncExport(
        prepared_->request.launchContext));
  }

  py::dict finish() {
    ensurePrepared();
    py::dict exportedRun = readRaw();
    releaseInternal();
    return exportedRun;
  }

  void release() { releaseInternal(); }

private:
  void ensurePrepared() const {
    if (!prepared_.has_value()) {
      throw py::value_error("debugger launch handle is no longer active");
    }
  }

  void releaseInternal() {
    if (!prepared_.has_value()) {
      return;
    }
    if (prepared_->transferEngine) {
      prepared_->transferEngine->release(prepared_->request.launchContext);
      prepared_->transferEngine.reset();
    }
    prepared_.reset();
  }

  bool initialized_ = false;
  std::optional<PreparedDebugLaunch> prepared_;
};

} // namespace

void init_flagtree_debugger_runtime(py::module &&m) {
  py::class_<PreparedLaunchHandle>(m, "PreparedLaunchHandle")
      .def("initialize", &PreparedLaunchHandle::initialize)
      .def("read_raw", &PreparedLaunchHandle::readRaw)
      .def_property_readonly("hidden_arg_value",
                             &PreparedLaunchHandle::hiddenArgValue)
      .def_property_readonly("buffer_meta", &PreparedLaunchHandle::bufferMeta)
      .def_property_readonly("runtime_metadata",
                             &PreparedLaunchHandle::runtimeMetadata)
      .def("finish", &PreparedLaunchHandle::finish)
      .def("release", &PreparedLaunchHandle::release);

  m.attr("GCU_TIMELINE_STORAGE_VERSION") = 2;
  m.def("allocate_timeline_launch",
      [](py::dict metadata, uint64_t streamHandle, py::object runtimeMetadata) {
        if (getStringOr(metadata, "debug_record_layout", "") != "gcu_first_last_timeline_v2")
          throw py::value_error("Deferred timeline allocation requires GCU storage v2");
        return std::make_unique<PreparedLaunchHandle>(metadata, streamHandle,
                                                      runtimeMetadata, false);
      });
  m.def(
      "prepare_launch",
      [](const py::dict &metadata, uint64_t streamHandle,
         py::object runtimeMetadata) {
        return std::make_unique<PreparedLaunchHandle>(metadata, streamHandle,
                                                      runtimeMetadata);
      },
      py::arg("metadata"), py::arg("stream_handle"),
      py::arg("runtime_metadata") = py::none());

  m.def(
      "decode_exported_run",
      [](const py::dict &exportedRun) {
        DebugExportedRun run = parseExportedRun(exportedRun);
        DecodedDebugRun decoded;
        std::string errorMessage;
        if (!decodeExportedRun(run, decoded, &errorMessage)) {
          throw py::value_error(errorMessage);
        }
        return toPyDecodedRun(decoded);
      },
      py::arg("exported_run"));

  m.def(
      "render_text_report",
      [](const py::dict &exportedRun, const std::string &metadataJson) {
        DecodedDebugRun decoded;
        KernelDebugMetadata metadata;
        parseReportInputs(exportedRun, metadataJson, decoded, metadata);
        return renderTextReport(decoded, metadata);
      },
      py::arg("exported_run"), py::arg("metadata_json"));

  m.def(
      "render_json_report",
      [](const py::dict &exportedRun, const std::string &metadataJson) {
        DecodedDebugRun decoded;
        KernelDebugMetadata metadata;
        parseReportInputs(exportedRun, metadataJson, decoded, metadata);
        return renderJsonReport(decoded, metadata);
      },
      py::arg("exported_run"), py::arg("metadata_json"));

  m.def(
      "render_text_statement_report",
      [](const py::dict &exportedRun, const std::string &metadataJson) {
        DecodedDebugRun decoded;
        KernelDebugMetadata metadata;
        parseReportInputs(exportedRun, metadataJson, decoded, metadata);
        return renderTextReport(decoded, metadata,
                                makeStatementReportOptions());
      },
      py::arg("exported_run"), py::arg("metadata_json"));

  m.def(
      "render_json_statement_report",
      [](const py::dict &exportedRun, const std::string &metadataJson) {
        DecodedDebugRun decoded;
        KernelDebugMetadata metadata;
        parseReportInputs(exportedRun, metadataJson, decoded, metadata);
        return renderJsonReport(decoded, metadata,
                                makeStatementReportOptions());
      },
      py::arg("exported_run"), py::arg("metadata_json"));

  m.def(
      "render_text_op_log_report",
      [](const py::dict &exportedRun, const std::string &metadataJson) {
        DecodedDebugRun decoded;
        KernelDebugMetadata metadata;
        parseReportInputs(exportedRun, metadataJson, decoded, metadata);
        return renderTextReport(decoded, metadata, makeOpLogReportOptions());
      },
      py::arg("exported_run"), py::arg("metadata_json"));

  m.def(
      "render_json_op_log_report",
      [](const py::dict &exportedRun, const std::string &metadataJson) {
        DecodedDebugRun decoded;
        KernelDebugMetadata metadata;
        parseReportInputs(exportedRun, metadataJson, decoded, metadata);
        return renderJsonReport(decoded, metadata, makeOpLogReportOptions());
      },
      py::arg("exported_run"), py::arg("metadata_json"));
}
