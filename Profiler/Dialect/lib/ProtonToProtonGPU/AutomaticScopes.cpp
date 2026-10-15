#include "Analysis/AutomaticScopes.h"
#include "Dialect/Proton/IR/Dialect.h"
#include "mlir/IR/Builders.h"
#include "mlir/IR/BuiltinTypes.h"
#include "mlir/Interfaces/SideEffectInterfaces.h"
#include "mlir/Pass/Pass.h"

namespace mlir::triton::proton {
// Source-linked checkpoints around compiler operations. This pass does not
// synchronize asynchronous work or claim that an issue interval is engine busy.
class AutomaticScopesPass
    : public PassWrapper<AutomaticScopesPass, OperationPass<ModuleOp>> {
public:
  MLIR_DEFINE_EXPLICIT_INTERNAL_INLINE_TYPE_ID(AutomaticScopesPass)
  AutomaticScopesPass() = default;
  explicit AutomaticScopesPass(unsigned limit) : siteLimit(limit) {}
  AutomaticScopesPass(const AutomaticScopesPass &other)
      : PassWrapper(other), siteLimit(other.siteLimit) {}
  unsigned siteLimit = 8;
  StringRef getArgument() const final { return "proton-automatic-scopes"; }
  StringRef getDescription() const final {
    return "Insert bounded source-linked internal operation intervals";
  }
  void getDependentDialects(DialectRegistry &registry) const override {
    registry.insert<ProtonDialect>();
  }
  void runOnOperation() override {
    auto module = getOperation();
    // Idempotence also keeps advanced manually annotated kernels unchanged.
    bool hasRecords = false;
    module.walk([&](RecordOp) { hasRecords = true; });
    if (hasRecords)
      return;
    SmallVector<Operation *> candidates;
    module.walk<WalkOrder::PreOrder>([&](Operation *op) {
      auto dialect = op->getName().getDialectNamespace();
      if (dialect != "tt" && dialect != "ttg" && dialect != "ttng" &&
          dialect != "arith" && dialect != "math")
        return;
      // Reduction/scan combiners and other non-control regions must remain
      // pure. Their enclosing tensor operation is observed instead.
      for (auto *parent = op->getParentOp(); parent;
           parent = parent->getParentOp()) {
        auto ns = parent->getName().getDialectNamespace();
        if (ns != "scf" && !isa<ModuleOp>(parent) &&
            parent->getName().getStringRef() != "tt.func")
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
      if (!tensorResult && !tensorOperand && isMemoryEffectFree(op))
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
    auto choose = [&](const SmallVector<size_t> &pool, size_t count) {
      for (size_t i = 0; i < count; ++i)
        ordinals.push_back(
            pool[count == 1 ? 0 : i * (pool.size() - 1) / (count - 1)]);
    };
    choose(statements, std::min(selected, statements.size()));
    choose(helpers, selected - ordinals.size());
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
              builder.getStringAttr(statement ? "source_statement"
                                              : "internal_operation")),
          builder.getNamedAttr(
              "selection_reason",
              builder.getStringAttr(
                  chosen ? (statement ? "source_statement_priority"
                                      : "evenly_spaced_internal_operation")
                         : "site_budget_excluded"))};
      if (chosen)
        fields.push_back(builder.getNamedAttr(
            "selected_scope_name",
            builder.getStringAttr("auto/" + std::to_string(ordinal) + "/" +
                                  op->getName().getStringRef().str())));
      if (auto text = op->getAttr("flagtree.debug.triton_statement"))
        fields.push_back(builder.getNamedAttr("source_statement", text));
      inventory.push_back(builder.getDictionaryAttr(fields));
    }
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
      start->setAttr("proton.automatic_operation",
                     builder.getStringAttr(op->getName().getStringRef()));
      if (auto statement = op->getAttr("flagtree.debug.triton_statement"))
        start->setAttr("proton.automatic_statement", statement);
      builder.setInsertionPointAfter(op);
      auto end = builder.create<RecordOp>(op->getLoc(), false, scopeName);
      end->setAttr("proton.automatic_operation",
                   builder.getStringAttr(op->getName().getStringRef()));
      if (auto statement = op->getAttr("flagtree.debug.triton_statement"))
        end->setAttr("proton.automatic_statement", statement);
    }
  }
};
std::unique_ptr<OperationPass<ModuleOp>>
createAutomaticScopesPass(unsigned maxSites) {
  return std::make_unique<AutomaticScopesPass>(maxSites);
}
} // namespace mlir::triton::proton
