# Native shared payload words and coalesced operations (r044)

The SM120 mapper now compares actual shared-operation address/size expressions
with their recorded payload words, rather than relying on source proximity.
Loop-mutated registers have distinct epoch inputs; only invariant registers
resolve through the acyclic preheader. Bounded expression caches and immediate
dominators avoid storing a quadratic ancestor matrix. A synthetic 8192-node
control graph tests that implementation boundary.

Actual compiler output merges two adjacent scalar source loads into one
LDS.64. The report retains all source origins, byte suboffsets, coverage and the
first bracket that actually contains the native operation. The later empty
source bracket does not become a second hardware load. Dynamic native groups
are scoped to invocation/program/actor and the first actual record ordinal.
No operator name, shape, fixed site or PC selects these rules.

## Installed evidence

A new wheel and independent environment passed default API numerical tests,
runtime-K GEMM, compiler/derive/copy recovery, prior native wait/boundary/timer/
record contracts and the new shared payload contracts. Normal and optimized
Python each checked all 18 variable sites in two real captures and rejected 48
corrupted/ambiguous cases. Actual raw words, address bounds, valid-byte domains,
coalesced subranges and the collective byte-generation model are checked.
Five LOP3 LUT codes and SEL.64 also ran as real numerical device kernels, each
with 257 inputs and retained PTX/CUBIN/disassembly. These are mechanism tests,
not the independent six-new-mathematics qualification.

The first ALU script failed on a disassembler JSON version-field path; its
corrected second input passed all six cases. Initial formatting rejected a
lambda assignment. Both failures and their original inputs remain retained.
The initial failed formatter collector produced text, whose attempted tar read
also failed; the text and a separate valid failure archive remain in preflight.
The successful ALU source predates whitespace-only formatting; AST preservation
bridges it to the committed test, without claiming a new formatted-source run.

All imports, wheels, device/CPU tests, recovery and actual Trace Processor ran
in the existing NVIDIA Docker. Cached full precommit fixed point and AST
preservation ran in the existing GCU Docker. The workstation only edited,
used Git, orchestrated and audited retained bytes with the standard library.

Three retained-only export processes and real Trace Processor passed; 16
isolated traces stayed byte-identical. The new shared payload report is scoped
to each invocation and added to immutable offline control evidence. Original
r043 captures remain hash-identical. Exact unchanged r024 native core and r036
standalone tool were reused with receipts, not rebuilt. See verification.json
for source/wheel/archive hashes, terminal identities, budgets and checks.

## Scope still outstanding

This establishes native variable-word relations and raw domain/group agreement,
not absolute raw allocation/program/ordinal store provenance. Full raw
provenance, physical overlap, source cost, engine busy and temporal flows remain
unqualified. Common encoder/canonical/UI code is unchanged; no new browser run
is claimed. Full three-backend pipelines, independent mathematical
qualification, controlled cases and the three fresh final reviewers remain
required. No paper or Study data were changed.
