# Late NVIDIA timer-to-native-store values (r042)

This delta checks both words from actual full-width SM120 global timer readers
at the original-PTX-bound native STG.E.64 instructions. A bounded backwards
reaching-definition analysis includes all native branch paths, overlapping
MOV.64, predicated writes and matched forward reconvergence regions. Unknown
instructions/control, overwrites, swapped words or a path bypassing the getter
remain unverified. No operator names, shapes, paths or fixed sites/PCs select
rules. The default native boundary diagnostic and public offline derived control
report now include `timer_store_values` and complete called-rule fingerprints.

## Actual evidence

All imports, packaging, numerical tests, negative fixtures and actual Trace
Processor execution ran in existing NVIDIA `chijin-study-pro6000`. Full cached
precommit fixed point and Python AST preservation ran in existing GCU Docker
`flagprism-enflame-dev`. Workstation operations were editing, Git, orchestration
and standard-library inspection/hash audits of retained artifacts.

The first source probe checked 43 of 70 getter endpoints in each retained actual
capture; overly broad reconvergence edges left later endpoints unverified. The
second probe checked actual matched forward reconvergence but retained failures
for a predicate-first scalar output form. The third probe checked all 70. These
partial diagnostics are retained; terminal zero alone was never full passage.
Source contracts then passed in normal and optimized Python, including actual
objects and CPU-only negative control/value fixtures. Fixtures are never run as
unsafe device kernels.

The first independently installed wheel passed 23 default mathematical calls,
four runtime-K GEMM mathematical calls, default fault/recovery, native boundaries,
normal/optimized timer-store contracts and public retained-only offline export
with actual Trace Processor checks. Default hook reports each checked all 70
getters in both real captures. A subsequent self-audit added the called
late-control helper's fingerprint and a coverage test. The final independent
wheel retains the same value/control algorithm and unchanged core/standalone
native source. Its normal/optimized real-object contracts, rule fingerprints,
public offline reports and Trace Processor checks passed using the same raw.
No unchanged device matrix was repeated for this metadata-only supplement.

See `verification.json` for exact archive/wheel/source SHA, negative counts,
process identities and terminal receipts. Sixteen existing isolated trace bytes
remain identical. r041 originals still match their archived SHA map. The archive
retains raw, original IR/PTX/CUBIN, both disassemblies, initial partial probes,
all actual inputs, contracts, installed receipts and SQL results. Native core
r024 and standalone r036 were reused with exact source/executable bridges;
there is no new C++ build or Python overlay claim.

## Limits and remaining work

This proves the timer value arriving at an identified native store. It does
not yet establish that the store address selects the admitted raw slot, verify
payload geometry, prove collective publication, or grant full raw provenance.
It grants no source cost, physical overlap, engine busy or temporal dependency
flows. Existing canonical/renderer semantics are unchanged; no new browser run
is claimed. Full three-backend pipelines, independent qualification and three
fresh final code reviewers remain required. Paper and Study files are untouched.
