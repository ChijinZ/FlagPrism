# Native record addresses and count updates (r045)

This delta checks final SM120 record addresses relative to their published
count header. Both pointer words must agree. A paired LEA/LEA.HI.X must use the
same shift, corresponding input words and live carry. Inputs cannot change
between the words; the low output cannot overwrite an input still needed by
the high word. Native constant-bank reloads and full-width moves/additions are
compared without equating only the low address word. All-path reaching
definitions and expression caches are bounded; unknown patterns remain
explicitly unverified.

The native count register comes from the actual published header store.
Its complete write inventory must contain zero initialization and the exact
initial assignment or positive append for each complete source batch. Every
batch's stores, address formation and one count update must belong to one
unambiguous single-entry straight native region. Appends read the old count
before its update. This tolerates actual scheduling of an update before the
stores, while rejecting a bypass or address formed from an incremented count.
No fixed operator name, site, instruction PC, source path or batch length
selects the rules.

Default captures add static `record_address_arithmetic` and a separate
invocation-specific `native_record_ordinal_file`. The latter checks complete
actual raw batch sequences and all four field offsets, retaining program,
actor, first ordinal, batch index and count. Public retained-only reexport
adds `native_record_ordinals` to immutable control evidence. Partial batches
are rejected rather than completed from the final count.

All imports, new wheel/install, numerical/device tests, CPU corruption fixtures,
recovery and actual Trace Processor ran in the existing NVIDIA Docker.
Cached full precommit fixed point and Python AST preservation ran in the
existing GCU Docker. The workstation only edited, used Git, orchestrated and
audited retained bytes with the standard library. Exact unchanged native core
r024 and standalone recorder r036 were reused with source/executable receipts;
no new C++ build is claimed. See verification.json for actual installation,
source/archive hashes, terminal processes, negative checks and budget results.

The initial source probe checked header-relative full-width arithmetic and
write inventory. The second probe added joint control and raw batch binding.
Normal/optimized source contracts passed. Self-review then added the low-output
alias and discarded-carry rejection, with an independent overlapping-input
fixture. A further self-review rejects a header base containing a mutable
count epoch. An independent second wheel checks that final constraint in
normal/optimized Python against the same retained actual captures and public
offline Trace Processor. Device mathematics from the first installed version
is not relabeled as a new device run of the second wheel; native producers,
transport and encoder did not change.

One evidence-format launch substituted the version inside the existing GCU
Python path and failed before starting its controller. The original command,
input and observed error are preserved. A new version uses the actual cached
interpreter. This was an orchestration error, not a vendor environment blocker.

This proof is header-relative address/count linkage. Absolute launch allocation
and physical program/thread header origins remain separate requirements. Full
raw provenance, physical overlap, source cost, engine busy and temporal flows
are not granted. Common encoder/canonical/UI code is unchanged and no new
browser run is claimed. Three-backend pipelines, independent mathematical
qualification, controlled cases and three fresh final reviewers remain
required. Paper and Study data were untouched.
