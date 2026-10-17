#include "Analysis/AutomaticScopes.h"
#include "Dialect/Proton/IR/Dialect.h"
#include "mlir/IR/Builders.h"
#include "mlir/IR/BuiltinTypes.h"
#include "mlir/Interfaces/SideEffectInterfaces.h"
#include "mlir/Pass/Pass.h"
#include "triton/Dialect/TritonGPU/IR/Dialect.h"
#include "llvm/ADT/DenseMap.h"
#include "llvm/ADT/SmallPtrSet.h"
#include <functional>

namespace mlir::triton::proton {
// Source-linked checkpoints around compiler operations. This pass does not
// synchronize asynchronous work or claim that an issue interval is engine busy.
class AutomaticScopesPass
    : public PassWrapper<AutomaticScopesPass, OperationPass<ModuleOp>> {
public:
  MLIR_DEFINE_EXPLICIT_INTERNAL_INLINE_TYPE_ID(AutomaticScopesPass)
  AutomaticScopesPass() = default;
  explicit AutomaticScopesPass(unsigned limit, bool census = false,
                               bool timeline = false)
      : siteLimit(limit), census(census), timeline(timeline) {}
  AutomaticScopesPass(const AutomaticScopesPass &other)
      : PassWrapper(other), siteLimit(other.siteLimit), census(other.census),
        timeline(other.timeline) {}
  unsigned siteLimit = 8;
  bool census = false;
  bool timeline = false;
  StringRef getArgument() const final { return "proton-automatic-scopes"; }
  StringRef getDescription() const final {
    return "Insert bounded source-linked internal operation intervals";
  }
  void getDependentDialects(DialectRegistry &registry) const override {
    registry.insert<ProtonDialect>();
  }
  void runOnOperation() override {
    auto module = getOperation();
    if (timeline && census) {
      module.emitError("Timeline timestamps and source census are distinct modes");
      return signalPassFailure();
    }
    if (timeline) {
      // This is an explicit getter/encoding choice, not a certificate of epoch
      // alignment. The producer must retain the final object and clock proof.
      module->setAttr("proton.timeline_timer",
                      StringAttr::get(&getContext(), "nvidia.globaltimer.ns"));
      module->setAttr("proton.timeline_timer_version",
                      IntegerAttr::get(IntegerType::get(&getContext(), 32), 1));
      module->setAttr("proton.timeline_record_version",
                      IntegerAttr::get(IntegerType::get(&getContext(), 32), 2));
    }
    if (census)
      module->setAttr("proton.source_census", UnitAttr::get(&getContext()));
    // Idempotence also keeps advanced manually annotated kernels unchanged.
    bool hasRecords = false;
    module.walk([&](RecordOp) { hasRecords = true; });
    if (hasRecords)
      return;
    // Observe actual scalar control computations even when the selected program
    // takes an empty branch. This records that program's control activity only;
    // it does not claim to have observed tensor work on another program.
    llvm::SmallPtrSet<Operation *, 32> controlSlice;
    SmallVector<Operation *> controls;
    std::function<void(Value)> visitDefinition = [&](Value value) {
      auto *definition = value.getDefiningOp();
      if (!definition || !controlSlice.insert(definition).second)
        return;
      for (Value operand : definition->getOperands())
        visitDefinition(operand);
    };
    module.walk<WalkOrder::PreOrder>([&](Operation *op) {
      auto name = op->getName().getStringRef();
      if (name == "scf.if" || name == "scf.for" || name == "scf.while") {
        controls.push_back(op);
        unsigned conditionOperands = name == "scf.if"    ? 1
                                     : name == "scf.for" ? 3
                                                         : 0;
        for (Value operand : op->getOperands().take_front(conditionOperands))
          visitDefinition(operand);
      }
      // A while condition is defined inside its before region.
      if (name == "scf.condition" && op->getNumOperands())
        visitDefinition(op->getOperand(0));
    });
    SmallVector<Operation *> candidates;
    module.walk<WalkOrder::PreOrder>([&](Operation *op) {
      auto dialect = op->getName().getDialectNamespace();
      if (dialect != "tt" && dialect != "ttg" && dialect != "ttng" &&
          dialect != "arith" && dialect != "math" &&
          !llvm::is_contained(controls, op))
        return;
      // Reduction/scan combiners and other non-control regions must remain
      // pure. Their enclosing tensor operation is observed instead.
      for (auto *parent = op->getParentOp(); parent;
           parent = parent->getParentOp()) {
        auto ns = parent->getName().getDialectNamespace();
        const bool censusPartition =
            census && isa<triton::gpu::WarpSpecializeOp,
                          triton::gpu::WarpSpecializePartitionsOp>(parent);
        if (ns != "scf" && !isa<ModuleOp>(parent) &&
            parent->getName().getStringRef() != "tt.func" && !censusPartition)
          return;
      }
      if (op->hasTrait<OpTrait::ConstantLike>() ||
          op->hasTrait<OpTrait::IsTerminator>())
        return;
      auto name = op->getName().getStringRef();
      // Shape, pointer and layout bookkeeping is not source computation.
      if (name == "tt.func" || name == "tt.addptr" || name == "tt.make_range" ||
          name == "tt.splat" || name == "tt.expand_dims" ||
          name == "tt.broadcast" || name == "ttg.convert_layout")
        return;
      bool tensorResult = llvm::any_of(op->getResultTypes(), [](Type type) {
        return isa<RankedTensorType>(type);
      });
      bool tensorOperand = llvm::any_of(op->getOperandTypes(), [](Type type) {
        return isa<RankedTensorType>(type);
      });
      if (!tensorResult && !tensorOperand && isMemoryEffectFree(op) &&
          !controlSlice.contains(op) && !llvm::is_contained(controls, op))
        return;
      candidates.push_back(op);
    });
    // A compile-time budget limits actual device work, not just report rows.
    const size_t budget = siteLimit;
    size_t selected = std::min(budget, candidates.size());
    module->setAttr("proton.automatic_candidates",
                    IntegerAttr::get(IntegerType::get(&getContext(), 64),
                                     candidates.size()));
    module->setAttr(
        "proton.automatic_selected",
        IntegerAttr::get(IntegerType::get(&getContext(), 64), selected));
    // Prefer frontend-preserved source statements over pointer/mask/layout
    // helper arithmetic. This is compiler metadata, independent of user names
    // and shapes. Fallback candidates keep generated or stripped IR useful.
    SmallVector<size_t> statements, helpers, ordinals;
    for (size_t i = 0; i < candidates.size(); ++i) {
      auto *op = candidates[i];
      (op->hasAttr("flagtree.debug.statement_id") ||
               op->hasAttr("flagtree.debug.triton_statement")
           ? statements
           : helpers)
          .push_back(i);
    }
    SmallVector<std::string> reasons(candidates.size(), "site_budget_excluded");
    auto select = [&](size_t ordinal, StringRef reason) {
      if (ordinals.size() < selected &&
          !llvm::is_contained(ordinals, ordinal)) {
        ordinals.push_back(ordinal);
        reasons[ordinal] = reason.str();
      }
    };
    struct ControlRegion {
      size_t control, region, block;
      bool repeated;
      SmallVector<size_t> direct, descendants;
    };
    SmallVector<ControlRegion> regions;
    for (size_t control = 0; control < controls.size(); ++control) {
      auto *owner = controls[control];
      bool repeated = owner->getName().getStringRef() != "scf.if";
      for (auto [regionIndex, region] : llvm::enumerate(owner->getRegions()))
        for (auto [blockIndex, block] : llvm::enumerate(region)) {
          ControlRegion group{control,  regionIndex, blockIndex,
                              repeated, {},          {}};
          for (size_t i = 0; i < candidates.size(); ++i) {
            auto *op = candidates[i];
            if (op->getBlock() == &block)
              group.direct.push_back(i);
            if (region.isAncestor(op->getParentRegion()))
              group.descendants.push_back(i);
          }
          regions.push_back(std::move(group));
        }
    }
    // Keep entry-block control evidence when the budget can also retain body
    // detail. Otherwise many untaken regions can exhaust the entire default
    // budget before the selected program records any control activity. Narrow
    // one/two-site requests retain their explicit region-priority behavior.
    if (selected >= 3) {
      for (size_t i = 0; i < candidates.size() && ordinals.size() < 2; ++i) {
        auto *op = candidates[i];
        if (!controlSlice.contains(op) && !llvm::is_contained(controls, op))
          continue;
        bool nested = false;
        for (auto *parent = op->getParentOp(); parent;
             parent = parent->getParentOp()) {
          if (parent->getName().getDialectNamespace() == "scf") {
            nested = true;
            break;
          }
        }
        if (!nested)
          select(i, "entry_control_context");
      }
    }
    // Repeating and branch region detail uses the remaining bounded capacity.
    for (bool repeated : {true, false})
      for (auto &group : regions) {
        if (group.repeated != repeated)
          continue;
        auto &pool = group.direct.empty() ? group.descendants : group.direct;
        if (pool.empty() || llvm::any_of(pool, [&](size_t ordinal) {
              return llvm::is_contained(ordinals, ordinal);
            }))
          continue;
        auto best = llvm::find_if(pool, [&](size_t ordinal) {
          return llvm::is_contained(statements, ordinal) &&
                 !llvm::is_contained(controls, candidates[ordinal]);
        });
        select(best == pool.end() ? pool.front() : *best,
               "control_flow_region_representative");
      }
    // Reserve control computation and container intervals. An empty arm still
    // leaves truthful internal condition/control evidence for this program.
    for (size_t i = 0; i < candidates.size(); ++i)
      if (controlSlice.contains(candidates[i]) ||
          llvm::is_contained(controls, candidates[i]))
        select(i, "control_flow_context");
    auto choose = [&](const SmallVector<size_t> &pool, StringRef reason) {
      SmallVector<size_t> remaining;
      for (size_t ordinal : pool)
        if (!llvm::is_contained(ordinals, ordinal))
          remaining.push_back(ordinal);
      size_t count = std::min(selected - ordinals.size(), remaining.size());
      for (size_t i = 0; i < count; ++i)
        select(remaining[count == 1 ? 0
                                    : i * (remaining.size() - 1) / (count - 1)],
               reason);
    };
    if (timeline) {
      // Logical source detail remains bounded. Prefer actual data operations
      // over pointer/mask helpers; required async boundaries are added below
      // under their own finite compiler budget, never silently downsampled.
      SmallVector<size_t> dataOperations;
      for (size_t i = 0; i < candidates.size(); ++i) {
        auto name = candidates[i]->getName().getStringRef();
        if (name == "tt.dot" || name == "tt.load" || name == "tt.store" ||
            name == "tt.reduce" || name == "tt.scan" ||
            name == "ttg.local_load" || name == "ttg.local_store" ||
            candidates[i]->getName().getDialectNamespace() == "math")
          dataOperations.push_back(i);
      }
      choose(dataOperations, "timeline_data_operation");
    }
    choose(statements, "source_statement_priority");
    choose(helpers, "evenly_spaced_internal_operation");
    auto mechanism = [](Operation *op) -> StringRef {
      auto name = op->getName().getStringRef();
      if (name == "ttg.async_copy_global_to_local")
        return "nvidia.cp_async.submit";
      if (name == "ttg.async_commit_group")
        return "nvidia.cp_async.commit";
      if (name == "ttg.async_wait")
        return "nvidia.cp_async.wait";
      return "";
    };
    size_t requiredAsync = 0;
    if (timeline) {
      for (size_t i = 0; i < candidates.size(); ++i) {
        auto role = mechanism(candidates[i]);
        if (role.empty())
          continue;
        if (++requiredAsync > 128) {
          module.emitError("Timeline async boundary set exceeds 128 static sites; "
                           "refusing incomplete mechanism collection");
          return signalPassFailure();
        }
        if (role == "nvidia.cp_async.wait") {
          auto pending = candidates[i]->getAttrOfType<IntegerAttr>("num");
          if (!pending || pending.getInt() < 0 || pending.getInt() > 7) {
            module.emitError("Unsupported cp.async wait coverage attribute");
            return signalPassFailure();
          }
        }
        if (!llvm::is_contained(ordinals, i))
          ordinals.push_back(i);
        reasons[i] = "required_timeline_async_boundary";
      }
      module->setAttr("proton.timeline_plan_version",
                      IntegerAttr::get(IntegerType::get(&getContext(), 32), 1));
      module->setAttr("proton.timeline_async_boundary_count",
                      IntegerAttr::get(IntegerType::get(&getContext(), 32),
                                       requiredAsync));
      module->setAttr("proton.automatic_selected",
                      IntegerAttr::get(IntegerType::get(&getContext(), 64),
                                       ordinals.size()));
    }
    llvm::sort(ordinals);
    OpBuilder builder(&getContext());
    SmallVector<Attribute> inventory;
    for (size_t ordinal = 0; ordinal < candidates.size(); ++ordinal) {
      Operation *op = candidates[ordinal];
      bool chosen = llvm::is_contained(ordinals, ordinal);
      bool statement = op->hasAttr("flagtree.debug.statement_id") ||
                       op->hasAttr("flagtree.debug.triton_statement");
      SmallVector<NamedAttribute> fields{
          builder.getNamedAttr("candidate_ordinal",
                               builder.getI64IntegerAttr(ordinal)),
          builder.getNamedAttr(
              "operation", builder.getStringAttr(op->getName().getStringRef())),
          builder.getNamedAttr("location", op->getLoc()),
          builder.getNamedAttr("selected", builder.getBoolAttr(chosen)),
          builder.getNamedAttr(
              "candidate_class",
              builder.getStringAttr(
                  llvm::is_contained(controls, op) ? "control_region"
                  : controlSlice.contains(op)      ? "control_computation"
                  : statement                      ? "source_statement"
                                                   : "internal_operation")),
          builder.getNamedAttr("selection_reason",
                               builder.getStringAttr(reasons[ordinal]))};
      if (timeline) {
        auto role = mechanism(op);
        fields.push_back(builder.getNamedAttr(
            "timeline_semantic", builder.getStringAttr(
                role == "nvidia.cp_async.wait" ? "wait_bracket"
                : !role.empty()                 ? "issue_interval"
                                                : "observer_region_elapsed")));
        if (!role.empty()) {
          fields.push_back(builder.getNamedAttr("timeline_mechanism",
                                                builder.getStringAttr(role)));
          if (role == "nvidia.cp_async.wait")
            fields.push_back(builder.getNamedAttr(
                "timeline_wait_pending", op->getAttr("num")));
        }
      }
      if (chosen)
        fields.push_back(builder.getNamedAttr(
            "selected_scope_name",
            builder.getStringAttr("auto/" + std::to_string(ordinal) + "/" +
                                  op->getName().getStringRef().str())));
      if (auto text = op->getAttr("flagtree.debug.triton_statement"))
        fields.push_back(builder.getNamedAttr("source_statement", text));
      inventory.push_back(builder.getDictionaryAttr(fields));
    }
    SmallVector<Attribute> regionInventory;
    for (auto &group : regions) {
      auto integers = [&](const SmallVector<size_t> &values) {
        SmallVector<Attribute> attrs;
        for (size_t value : values)
          attrs.push_back(builder.getI64IntegerAttr(value));
        return builder.getArrayAttr(attrs);
      };
      SmallVector<size_t> retained, directRetained;
      for (size_t ordinal : ordinals) {
        if (llvm::is_contained(group.descendants, ordinal))
          retained.push_back(ordinal);
        if (llvm::is_contained(group.direct, ordinal))
          directRetained.push_back(ordinal);
      }
      auto status = group.descendants.empty() ? "no_eligible_operation"
                    : !directRetained.empty() ? "direct_representative"
                    : !retained.empty()       ? "descendant_only"
                                              : "budget_excluded";
      regionInventory.push_back(builder.getDictionaryAttr(
          {builder.getNamedAttr("control_id",
                                builder.getI64IntegerAttr(group.control)),
           builder.getNamedAttr(
               "operation",
               builder.getStringAttr(
                   controls[group.control]->getName().getStringRef())),
           builder.getNamedAttr("location", controls[group.control]->getLoc()),
           builder.getNamedAttr("region_index",
                                builder.getI64IntegerAttr(group.region)),
           builder.getNamedAttr("block_index",
                                builder.getI64IntegerAttr(group.block)),
           builder.getNamedAttr("repeated",
                                builder.getBoolAttr(group.repeated)),
           builder.getNamedAttr("eligible_candidates",
                                integers(group.descendants)),
           builder.getNamedAttr("direct_candidates", integers(group.direct)),
           builder.getNamedAttr("selected_candidates", integers(retained)),
           builder.getNamedAttr("coverage_status",
                                builder.getStringAttr(status))}));
    }
    module->setAttr("proton.automatic_control_regions",
                    builder.getArrayAttr(regionInventory));
    module->setAttr("proton.automatic_inventory_schema",
                    builder.getI32IntegerAttr(2));
    module->setAttr("proton.automatic_inventory",
                    builder.getArrayAttr(inventory));
    for (size_t ordinal : ordinals) {
      Operation *op = candidates[ordinal];
      std::string name = "auto/" + std::to_string(ordinal) + "/" +
                         op->getName().getStringRef().str();
      auto scopeName = builder.getStringAttr(name);
      builder.setInsertionPoint(op);
      auto start = builder.create<RecordOp>(op->getLoc(), true, scopeName);
      const bool primary =
          op->getNumRegions() == 0 && !controlSlice.contains(op);
      if (census)
        start->setAttr("proton.census_role",
                       builder.getStringAttr(primary ? "primary" : "context"));
      start->setAttr("proton.automatic_operation",
                     builder.getStringAttr(op->getName().getStringRef()));
      if (auto statement = op->getAttr("flagtree.debug.triton_statement"))
        start->setAttr("proton.automatic_statement", statement);
      builder.setInsertionPointAfter(op);
      auto end = builder.create<RecordOp>(op->getLoc(), false, scopeName);
      if (census)
        end->setAttr("proton.census_role",
                     builder.getStringAttr(primary ? "primary" : "context"));
      end->setAttr("proton.automatic_operation",
                   builder.getStringAttr(op->getName().getStringRef()));
      if (auto statement = op->getAttr("flagtree.debug.triton_statement"))
        end->setAttr("proton.automatic_statement", statement);
    }
    if (census) {
      llvm::DenseMap<Region *, unsigned> observers;
      module.walk([&](RecordOp record) {
        unsigned observer = 0, threads = 0;
        if (auto partitions = record->getParentOfType<
                              triton::gpu::WarpSpecializePartitionsOp>()) {
          Operation *child = record;
          while (child->getParentOp() != partitions.getOperation())
            child = child->getParentOp();
          Region *region = child->getParentRegion();
          auto inserted = observers.try_emplace(region, observers.size() + 1);
          observer = inserted.first->second;
          threads = triton::gpu::lookupNumWarps(record.getOperation()) * 32;
          record->setAttr("proton.census_partition_region",
                          builder.getI32IntegerAttr(region->getRegionNumber()));
        }
        record->setAttr("proton.census_actor",
                        builder.getI32IntegerAttr(observer));
        record->setAttr("proton.census_observer_threads",
                        builder.getI32IntegerAttr(threads));
      });
    }
  }
};
std::unique_ptr<OperationPass<ModuleOp>>
createAutomaticScopesPass(unsigned maxSites, bool census, bool timeline) {
  return std::make_unique<AutomaticScopesPass>(maxSites, census, timeline);
}
} // namespace mlir::triton::proton
