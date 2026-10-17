#include "Analysis/AutomaticScopes.h"
#include "Analysis/ScopeIdAllocation.h"
#include "Conversion/ProtonGPUToLLVM/Passes.h"
#if !defined(FLAGPRISM_BACKEND_ENFLAME) &&                                     \
    !defined(FLAGPRISM_BACKEND_TIANSHU) &&                                     \
    !defined(FLAGPRISM_BACKEND_ASCEND) && !defined(FLAGPRISM_BACKEND_MTHREADS)
#include "Conversion/ProtonGPUToLLVM/ProtonAMDGPUToLLVM/Passes.h"
#include "Conversion/ProtonGPUToLLVM/ProtonNvidiaGPUToLLVM/Passes.h"
#endif
#include "Conversion/ProtonToProtonGPU/Passes.h"
#include "Dialect/Proton/IR/Dialect.h"
#include "Dialect/ProtonGPU/IR/Dialect.h"
#include "Dialect/ProtonGPU/Transforms/Passes.h"
#include "mlir/IR/Builders.h"
#include "mlir/IR/BuiltinAttributes.h"
#include "mlir/IR/Location.h"
#include "mlir/Pass/PassManager.h"
#include "passes.h"
#include "llvm/Support/raw_ostream.h"
#include <functional>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/stl_bind.h>

namespace py = pybind11;
using namespace mlir::triton;

namespace {
py::dict locationOrigin(mlir::Location loc) {
  py::dict result;
  std::string text;
  llvm::raw_string_ostream stream(text);
  loc.print(stream);
  stream.flush();
  result["ir_location"] = text;
  if (auto file = mlir::dyn_cast<mlir::FileLineColLoc>(loc)) {
    result["kind"] = "file_line_column";
    result["file"] = file.getFilename().str();
    result["line"] = file.getLine();
    result["column"] = file.getColumn();
  } else if (auto call = mlir::dyn_cast<mlir::CallSiteLoc>(loc)) {
    result["kind"] = "callsite";
    result["callee"] = locationOrigin(call.getCallee());
    result["caller"] = locationOrigin(call.getCaller());
  } else if (auto fused = mlir::dyn_cast<mlir::FusedLoc>(loc)) {
    result["kind"] = "fused";
    py::list candidates;
    for (auto child : fused.getLocations())
      candidates.append(locationOrigin(child));
    result["candidates"] = candidates;
    if (auto metadata = fused.getMetadata()) {
      std::string metadataText;
      llvm::raw_string_ostream metadataStream(metadataText);
      metadata.print(metadataStream);
      metadataStream.flush();
      result["metadata"] = metadataText;
    }
  } else if (auto name = mlir::dyn_cast<mlir::NameLoc>(loc)) {
    result["kind"] = "named";
    result["descriptive_name"] = name.getName().str();
    result["child"] = locationOrigin(name.getChildLoc());
  } else {
    result["kind"] = "unknown";
  }
  return result;
}
} // namespace

void init_triton_proton(py::module &&m) {
  m.doc() = "Python bindings to the Proton backend";
  m.attr("AUTOMATIC_INVENTORY_VERSION") = 2;
  m.attr("AUTOMATIC_SELECTION_POLICY_VERSION") = 2;
  m.attr("SOURCE_CENSUS_VERSION") = 1;
  m.attr("SOURCE_CENSUS_PARTITION_VERSION") = 2;
  m.attr("TIMELINE_TIMER_VERSION") = 1;
  m.attr("TIMELINE_RECORD_VERSION") = 2;

  // Proton enums
  py::enum_<proton::MetricType>(m, "METRIC_TYPE", py::module_local())
      .value("CYCLE", proton::MetricType::CYCLE)
      .export_values();

  py::enum_<proton::SamplingStrategy>(m, "SAMPLING_STRATEGY",
                                      py::module_local())
      .value("NONE", proton::SamplingStrategy::NONE)
      .value("SELECTIVE", proton::SamplingStrategy::SELECTIVE)
      .export_values();

  // ProtonGPU enums
  py::enum_<proton::gpu::Granularity>(m, "GRANULARITY", py::module_local())
      .value("CTA", proton::gpu::Granularity::CTA)
      .value("WARP", proton::gpu::Granularity::WARP)
      .value("WARP_2", proton::gpu::Granularity::WARP_2)
      .value("WARP_4", proton::gpu::Granularity::WARP_4)
      .value("WARP_8", proton::gpu::Granularity::WARP_8)
      .value("WARP_GROUP", proton::gpu::Granularity::WARP_GROUP)
      .value("WARP_GROUP_2", proton::gpu::Granularity::WARP_GROUP_2)
      .value("WARP_GROUP_4", proton::gpu::Granularity::WARP_GROUP_4)
      .value("WARP_GROUP_8", proton::gpu::Granularity::WARP_GROUP_8)
      .export_values();

  py::enum_<proton::gpu::BufferStrategy>(m, "BUFFER_STRATEGY",
                                         py::module_local())
      .value("CIRCULAR", proton::gpu::BufferStrategy::CIRCULAR)
      .value("FLUSH", proton::gpu::BufferStrategy::FLUSH)
      .export_values();

  py::enum_<proton::gpu::BufferType>(m, "BUFFER_TYPE", py::module_local())
      .value("SHARED", proton::gpu::BufferType::SHARED)
      .value("GLOBAL", proton::gpu::BufferType::GLOBAL)
      .export_values();

  // Load proton dialects
  m.def("load_dialects", [](mlir::MLIRContext &context) {
    mlir::DialectRegistry registry;
    registry.insert<proton::ProtonDialect>();
    registry.insert<proton::gpu::ProtonGPUDialect>();
    context.appendDialectRegistry(registry);
    context.loadAllAvailableDialects();
  });

  m.def("get_scope_id_names", [](mlir::ModuleOp &module) {
    return proton::ModuleScopeIdAllocation(module).getScopeIdNames();
  });

  m.def("get_scope_id_parents", [](mlir::ModuleOp &module) {
    return proton::ModuleScopeIdAllocation(module).getScopeIdParents();
  });

  m.def("get_scope_id_origins", [](mlir::ModuleOp &module) {
    proton::ModuleScopeIdAllocation allocation(module);
    py::dict result;
    module.walk([&](proton::RecordOp record) {
      auto id = allocation.getOpScopeId(record);
      auto key = py::str(std::to_string(id));
      if (!result.contains(key)) {
        py::dict origin;
        origin["scope_id"] = id;
        origin["semantic"] = "source_region_origin";
        origin["basis"] = "scope_id_allocation_and_record_op_location";
        origin["entry"] = py::list();
        origin["exit"] = py::list();
        result[key] = origin;
      }
      auto origin = result[key].cast<py::dict>();
      if (auto role =
              record->getAttrOfType<mlir::StringAttr>("proton.census_role"))
        origin["census_role"] = role.str();
      for (auto field : {"census_actor", "census_observer_threads",
                         "census_partition_region"})
        if (auto value = record->getAttrOfType<mlir::IntegerAttr>(
                std::string("proton.") + field))
          origin[field] = value.getInt();
      if (auto operation = record->getAttrOfType<mlir::StringAttr>(
              "proton.automatic_operation")) {
        origin["automatic"] = true;
        origin["operation"] = operation.str();
        origin["basis"] = "automatic_compiler_operation_boundaries";
        if (auto statement = record->getAttrOfType<mlir::StringAttr>(
                "proton.automatic_statement"))
          origin["source_statement"] = statement.str();
      }
      origin[record.getIsStart() ? "entry" : "exit"].cast<py::list>().append(
          locationOrigin(record.getLoc()));
    });
    return result;
  });

  // Proton operations
  m.def(
      "create_proton_record",
      [](mlir::OpBuilder &opBuilder, bool isStart, const std::string &name,
         std::optional<mlir::Location> location) -> void {
        auto nameAttr = mlir::StringAttr::get(opBuilder.getContext(),
                                              llvm::StringRef(name));
        auto loc = location.value_or(opBuilder.getUnknownLoc());
        opBuilder.create<proton::RecordOp>(loc, isStart, nameAttr);
      },
      py::arg("op_builder"), py::arg("is_start"), py::arg("name"),
      py::arg("location") = py::none());

  m.def(
      "add_automatic_proton_scopes",
      [](mlir::PassManager &pm, unsigned maxSites, bool census, bool timeline) {
        if (maxSites < 1 || maxSites > 128)
          throw std::invalid_argument(
              "Automatic site budget must be between 1 and 128");
        if (census && timeline)
          throw std::invalid_argument(
              "Timeline timestamps cannot use the count-only census ABI");
        pm.addPass(proton::createAutomaticScopesPass(maxSites, census, timeline));
      },
      py::arg("pm"), py::arg("max_sites") = 8, py::arg("census") = false,
      py::arg("timeline") = false);

  m.def("get_automatic_proton_plan", [](mlir::ModuleOp &module) {
    py::dict result;
    if (auto timer = module->getAttrOfType<mlir::StringAttr>(
            "proton.timeline_timer")) {
      auto version = module->getAttrOfType<mlir::IntegerAttr>(
          "proton.timeline_timer_version");
      if (!version || version.getInt() != 1)
        throw std::runtime_error("Missing or unsupported timeline timer version");
      result["timeline_timer"] = timer.str();
      result["timeline_getter_bits"] = 64;
      auto recordVersion = module->getAttrOfType<mlir::IntegerAttr>(
          "proton.timeline_record_version");
      // Timer-only prototype metadata remains explicitly distinguishable.
      if (module->hasAttr("proton.timeline_record_version") &&
          (!recordVersion || recordVersion.getInt() != 2))
        throw std::runtime_error("Unsupported timeline record version");
      result["timeline_record_version"] = recordVersion ? 2 : 1;
      result["timeline_record_bytes"] = recordVersion ? 16 : 8;
      result["timeline_record_clock_bits"] = recordVersion ? 64 : 43;
      result["timeline_timer_version"] = version.getInt();
    }
    for (auto name :
         {"proton.automatic_candidates", "proton.automatic_selected"})
      if (auto value = module->getAttrOfType<mlir::IntegerAttr>(name))
        result[py::str(name)] = value.getInt();
    auto inventory =
        module->getAttrOfType<mlir::ArrayAttr>("proton.automatic_inventory");
    if (auto schema = module->getAttrOfType<mlir::IntegerAttr>(
            "proton.automatic_inventory_schema"))
      result["schema_version"] = schema.getInt();
    if (auto regions = module->getAttrOfType<mlir::ArrayAttr>(
            "proton.automatic_control_regions")) {
      result["selection_policy"] =
          "bounded_control_regions_then_source_statements";
      result["selection_policy_version"] = 2;
      py::list rows;
      for (auto attribute : regions) {
        auto region = mlir::cast<mlir::DictionaryAttr>(attribute);
        py::dict row;
        for (auto key : {"control_id", "region_index", "block_index"})
          row[py::str(key)] = region.getAs<mlir::IntegerAttr>(key).getInt();
        for (auto key : {"operation", "coverage_status"})
          row[py::str(key)] = region.getAs<mlir::StringAttr>(key).str();
        row["location"] = locationOrigin(
            mlir::cast<mlir::LocationAttr>(region.get("location")));
        row["repeated"] = region.getAs<mlir::BoolAttr>("repeated").getValue();
        for (auto key : {"eligible_candidates", "direct_candidates",
                         "selected_candidates"}) {
          py::list ordinals;
          for (auto value : region.getAs<mlir::ArrayAttr>(key))
            ordinals.append(mlir::cast<mlir::IntegerAttr>(value).getInt());
          row[py::str(key)] = ordinals;
        }
        rows.append(row);
      }
      result["control_regions"] = rows;
    }
    if (inventory) {
      llvm::StringMap<size_t> allocatedScopes;
      for (const auto &entry :
           proton::ModuleScopeIdAllocation(module).getScopeIdNames())
        allocatedScopes[entry.second] = entry.first;
      py::list candidates;
      for (auto attribute : inventory) {
        auto candidate = mlir::cast<mlir::DictionaryAttr>(attribute);
        py::dict row;
        row["candidate_ordinal"] =
            candidate.getAs<mlir::IntegerAttr>("candidate_ordinal").getInt();
        row["operation"] = candidate.getAs<mlir::StringAttr>("operation").str();
        row["location"] = locationOrigin(
            mlir::cast<mlir::LocationAttr>(candidate.get("location")));
        row["selected"] =
            candidate.getAs<mlir::BoolAttr>("selected").getValue();
        row["candidate_class"] =
            candidate.getAs<mlir::StringAttr>("candidate_class").str();
        row["selection_reason"] =
            candidate.getAs<mlir::StringAttr>("selection_reason").str();
        row["selected_scope_name"] = py::none();
        row["scope_id"] = py::none();
        if (auto name =
                candidate.getAs<mlir::StringAttr>("selected_scope_name")) {
          row["selected_scope_name"] = name.str();
          auto allocated = allocatedScopes.find(name.getValue());
          if (allocated == allocatedScopes.end())
            throw std::runtime_error(
                "Automatic candidate scope is missing from saved compiler IR");
          row["scope_id"] = allocated->second;
        }
        if (auto text = candidate.getAs<mlir::StringAttr>("source_statement"))
          row["source_statement"] = text.str();
        candidates.append(row);
      }
      result["inventory"] = candidates;
      result["compiler_stage"] = "completed_ttgir_before_proton_lowering";
    }
    return result;
  });

  m.def("add_select_proton_programs", [](mlir::PassManager &pm,
                                         const std::vector<int32_t> &programs) {
    for (int32_t program : programs)
      if (program < 0)
        throw std::invalid_argument("Program identities must be nonnegative");
    pm.addPass(proton::createSelectProtonProgramsPass(programs));
  });

  m.def("add_convert_proton_to_protongpu",
        [](mlir::PassManager &pm, proton::MetricType &metricType,
           proton::SamplingStrategy samplingStrategy,
           const std::string &samplingOptions,
           proton::gpu::Granularity granularity,
           proton::gpu::BufferStrategy bufferStrategy,
           proton::gpu::BufferType bufferType, int32_t bufferSize,
           int32_t maxSharedMemSize, int64_t profileScratchSize,
           int32_t profileScratchAlignment, bool clkExt) {
          pm.addPass(proton::createConvertProtonToProtonGPUPass(
              metricType, samplingStrategy, samplingOptions, granularity,
              bufferStrategy, bufferType, bufferSize, maxSharedMemSize,
              profileScratchSize, profileScratchAlignment, clkExt));
        });

#if !defined(FLAGPRISM_BACKEND_ENFLAME) &&                                     \
    !defined(FLAGPRISM_BACKEND_TIANSHU) &&                                     \
    !defined(FLAGPRISM_BACKEND_ASCEND) && !defined(FLAGPRISM_BACKEND_MTHREADS)
  ADD_PASS_WRAPPER_0("add_convert_proton_nvidia_gpu_to_llvm",
                     proton::gpu::createConvertProtonNvidiaGPUToLLVMPass);
  ADD_PASS_WRAPPER_1("add_convert_proton_amd_gpu_to_llvm",
                     proton::gpu::createConvertProtonAMDGPUToLLVMPass,
                     const std::string &);
#endif
  ADD_PASS_WRAPPER_0("add_allocate_proton_shared_memory",
                     proton::gpu::createAllocateProtonSharedMemoryPass);
  ADD_PASS_WRAPPER_0("add_allocate_proton_global_scratch_buffer",
                     proton::gpu::createAllocateProtonGlobalScratchBufferPass);
  ADD_PASS_WRAPPER_0("add_schedule_buffer_store",
                     proton::gpu::createScheduleBufferStorePass);
#if !defined(FLAGPRISM_BACKEND_ENFLAME) &&                                     \
    !defined(FLAGPRISM_BACKEND_TIANSHU) &&                                     \
    !defined(FLAGPRISM_BACKEND_ASCEND) && !defined(FLAGPRISM_BACKEND_MTHREADS)
  ADD_PASS_WRAPPER_0("add_sched_barriers",
                     proton::gpu::createAddSchedBarriersPass);
#endif
}
