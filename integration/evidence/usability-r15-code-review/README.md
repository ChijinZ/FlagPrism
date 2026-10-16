# Additional r15 independent code reviews

Three additional reviewers were explicitly requested with `gpt-6.1-sol`,
`xhigh`, and `fork_turns=none`. The collaboration tool accepted each request;
it does not expose the resolved serving-model version. See the preserved
configuration record for the exact requested configuration and role IDs.
These code reviewers are separate from the independent product qualifiers.

Read each report through its final appended delta. Earlier confirmed failures
and original snapshots are intentionally retained, followed by the precise
fix, validation and closure scope:

- C1: compiler selection, executable identity/cache, actual capability probes,
  both linalg driver paths and fresh installed a829 boundary. The realpath /
  versioned-symlink major defect was reproduced and fixed; independent CPU
  stage and installed checks passed. No full hardware qualification claim.
- C2: SDK write-tiling legality, source/object/dependency/build/resource chain,
  assertion-based fail-open gate reproduced under optimized Python and fixed,
  independent ELF comparison, actual CPU replay/guard ancestry, and final
  public strict12 hardware evidence. The final delta4 independently checks
  actual results, compiler metadata, profile driver/source/output closure,
  terminal ownership cleanup and a finite generated-LLVM sample.
- C3: public source build/install and user instructions, missing templates
  and public baseline materials, portable test interpreter and both accepted
  baseline test routes. Confirmed delivery findings D1–D4 are closed in the
  appended finite source/CPU delivery scope.

Reviewed runtime/source boundaries are recorded individually. Canonical
`cb968eb8d1891bd1ec6ad2574e070747a0f80986` contains the SDK source/test fixes;
`a829a3312af69c1b961919025053829d7096a2b1` is the actual freshly installed
Python package. The subsequent evidence-only commit `118e4b3` changes no
runtime, SDK tool or tested user kernel. Reports never substitute a source
review for fresh numerical/device qualification.

No open confirmed blocker/major remains within these reviewed finite scopes.
This does **not** assert the product has passed final independent qualification.
The original Ascend 42/44 result and its two real State failures remain
historical evidence; the fixed-version original-source qualification is next.
Public strict12 passed separately and is archived next to this directory.
No PRIVATE kernel math/IR or SDK library/bytecode is included here.
