# Typed final SDK LLVM structure and compiler binding (R094)

Runtime source freeze: `c0575528418292c65eeccab4bd105b68bd000225`.
The standalone native component was genuinely built from the changed source;
its exact executable is reused when assembling the normal wheel. Shared
runtime/core and SDK are unchanged.

- Actual native build and nine CLI tests in normal/optimized modes pass.
  Two unchanged real LLVM inputs yield 93/84 blocks and 1603/1754 operations.
- Independent review found lexical caller aliasing and type-text expansion
  budget bugs. The fixed version rejects those exact examples and mismatched
  forwarded argument types. Tool SHA is
  `a2937f0de72fd2b7f2e031804ab6025a5fe1ba512db46f58e771f796a4d367b9`.
- Normal wheel install verifies packaged member bytes and every recorder source
  against that native build; 117 normal and 117 optimized tests pass, plus
  the nine installed native CLI tests in each mode.
- Fallback link plumbing is tested using actual installed backend function AST
  with mocked SDK calls. Those tests are not device/codegen evidence. They
  check that the actual relinked input replaces the old structure binding.
- Two ordinary and two profiled real math calls pass, including input/tail/
  once-only checks. Captures contain 22/20 internal intervals and automatically
  retain the typed index bound to actual final LLVM, fatbin and ELF.

This index supplies CFG, SSA, types, caller and marker references for the finite
source/tuple/loop rules. Constructing it alone does not complete those rules or
grant source-region/native-scheduling qualification. The whole goal is open.
Existing State, budgets, SQL/UI and operator matrices are not replayed.

The first normal installation transfer timed out before any controller started;
its incomplete input remains retained. The successful fresh input contains only
package/build inputs rather than accumulated evidence history. Full LLVM,
compiled binaries and typed graphs remain in owned root/server artifacts.
