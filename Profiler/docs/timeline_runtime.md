# Timeline invocation ownership

The public hook/API/CLI collect source-linked raw internal timestamps. Captures
remain explicitly `partial_clock_unverified`. NVIDIA automatic timeline now uses
late instrumentation after ordinary LLVM O3, with a separately packaged matching
LLVM recorder and `optimized-llvm.patch`. On the inspected SM120 target, the late
layout now also maps actual marked PTX/CUBIN readers and exports standard
observer-relative counter-ns Perfetto files. These show observer issue brackets,
wait brackets and checkpoints. The qualified dependency path described below
also joins observed dynamic dependencies within a proved invocation/program
counter epoch. Neither path establishes precise source costs, hardware busy
time or physical engine completion instants.

The inspected SM120 late path publishes `observed_dependency_exports` when
its native, storage, collective-byte and clock evidence jointly qualify.
Otherwise it attempts `shared_counter_exports` with `shared_counter_status`.
These are alternative shared views, rather than duplicate default exports. Each shared file uses one raw
counter origin and one counter epoch for selected threads of the same actual
invocation/program. Full-CTA recordings select up to four actual lane-zero
threads from distinct compiled warps (for four warps: 0, 32, 64, 96). A
single-warp full-CTA recording selects actual threads 0 through 3; a recorder
that only captured its first four threads cannot supply other warp data.
The common trace has compact per-thread operation tracks and preserves native
event labels, raw references, source navigation and lifecycle coverage. The
index labels these entries as shared counter groups.

The epoch provider requires the actual SM120 full-width marked machine getter,
complete raw/manifest binding, a completed single-CTA invocation and an
independent host completion window. It combines those inputs with NVIDIA's
[documented device clock semantics](https://nvidia.github.io/cccl/unstable/libcudacxx/standard_api/time_library.html),
whose retained excerpt and digest are part of the provider's evidence. It does
not use a cached qualification flag or infer alignment from equal counts.
Every raw tick uses `(tick - common_origin) * period`; observers are never
individually zeroed. Proof scopes do not authorize comparisons between files,
independent calls, native CTAs or GPUs.

`shared_counter_epoch_precision_unverified` means a common nominal counter
coordinate, with read precision still unknown. It does not certify physical
source-operation times, hardware overlap, engine busy or time arrows. These
rights remain false, and the original isolated exports remain available.
The public offline reexport adds `shared_exports` through the same provider,
without replaying an application or replacing old canonical/trace artifacts.
Missing or mismatched inputs retain an explicit shared-counter diagnostic.

Qualified dependency files contain the same observed internal intervals plus
an `Observed dependency checkpoints` track per actual observer. Selecting a
checkpoint in Perfetto reveals its incoming/outgoing flows, actual generation,
source locations, raw record offset and full-width tick. The arrows connect
observed submission, commit, wait return, barrier instruction, consumer issue
and reuse checkpoints. They do not locate an unobserved engine completion.
A barrier instruction checkpoint is not a synthetic collective-ready timestamp.
Coalesced source loads share their actual native observation witness.

`observed_dependency_status.time_arrows_verified` qualifies these logical
observed relations only. Read precision, physical overlap, source costs and
engine busy remain unqualified. All recorded CTA actors feed the byte model;
the four displayed observers do not replace that participation evidence.
A missing mechanism witness produces an explicit `unavailable` reason and
retains the raw data and any independently qualified counter-only view.
The offline command returns `observed_dependency_exports` and
`observed_dependency_reason` using freshly derived evidence without application
replay. Pure shared-counter exports remain available as the fallback and via
their existing writer API.

Re-export preserves existing immutable receipts. When every canonical, view
and trace byte and export descriptor is identical, the store may reuse an old
revision after validating its receipt, recording the current validation inputs
in `derived/revalidations/`. Returned rows identify that evidence through
`revalidation_file`. A changed view or trace gets a new revision; a current
rule identity never overwrites the original producer identity. The 16 MiB
session trace budget still applies; revalidation records have separate bounded
count and byte limits.

Current dependency qualification has been exercised with the four-warp
runtime-K GEMM and its one-warp variant, each with three and seven reduction
tiles. Fresh runs pass numerical, complete-record, collective-byte and native
dependency checks. All eight dependency traces pass independent raw/SQL checks
and standard Perfetto UI opening, wait-checkpoint selection and flow details.
These are finite development cases, not general-kernel or three-backend
qualification. Read precision, hardware busy and physical overlap remain
unverified.

The earlier spill/literal/address, record-overflow, oversized-bundle and browser
selection failures remain in the development evidence. Lossless interned strings
keep rich trace annotations within the 16 MiB session trace budget. Canonical
JSON is decoded afresh from raw; a producer can reference a committed canonical
file only if its complete serialized bytes match. `events_file` remains the
actual JSON path; `events_storage` identifies a verified
`committed_canonical_alias_v1` or the `standalone_json_v1` fallback. Do not infer
this path from an invocation-name suffix. The offline decoder keeps its own
revision inputs and receipt, and can reuse the same exact canonical bytes.
Historical files are not deleted or overwritten by this policy.

In the exercised one-warp case, the original bundle is 63,253,653 bytes and the
bundle after three independent offline exports is 64,928,584 bytes, both below
64 MiB; retained traces total 15,340,117 bytes. The old 73,061,831-byte bundle
remains an acceptance failure. These measurements establish the finite cases'
storage bounds, not an overhead or exclusive-GPU performance certification.

Default record capacity is now chosen from the actual recorded actor count.
A complete-CTA recording uses a power-of-two physical allowance of 2, 4 or
8 MiB for the first/last program pair, reserving 128 bytes for allocation
guards before calculating record capacity. It rounds down the allowance
needed for a 512-record target, so header overhead cannot make two nominal
4 MiB calls exceed the unchanged 8 MiB session limit. Actual capacities for
32/64/128/256 recorded threads are 1022/510/510/510 records per thread.
Larger footprints can consume the whole session allowance in one call;
unbounded repeated capture is not promised. A sampled
recording targets the full 4096 records for its at most four recorded threads,
using 1,048,960 bytes for a first/last pair with four threads. Each actor has six header words and four
64-bit words per record, with at most 4096 records. The compiler manifest
records `bounded-actor-bytes-v4`, the automatic pair byte budget, the footprint decision and the resulting
capacity; the Python adapter independently recomputes and checks them. An
explicit record-count request keeps its original meaning. The existing 8 MiB
session raw, 16 MiB trace and 64 MiB bundle limits remain in force. The old
one-warp seven-tile capture overflowed at the previous fixed 256-record limit;
that failure is retained. Fresh runs with the actor-byte capacity policy
record both reduction lengths without loss. Later independent 256-thread
cases overflowed the v1 policy's 126 records per actor; those original failures
remain retained. The v2 policy admits 510 records per actor for that geometry,
without raising the 8 MiB raw ceiling. This does not imply arbitrary
loop lengths fit the bounded buffer.
The subsequent independent sampled-loop case overflowed v2's 254-record limit;
v3 removes that artificial small-buffer target while keeping the same record
layout and 8 MiB raw ceiling. The original overflow remains an acceptance failure.

NVPTX lowering can remove complete static sites from constant libdevice
branches after late-LLVM instrumentation. The machine map lists these as
`not_emitted_static_sites`; this is not a claim about their source cost or
reachability. Every emitted site must retain all of its expected phases, and
every actual raw endpoint must have its corresponding inspected machine
getter before nanosecond export. Legacy marker mapping remains strict.

The recorder also preserves warp-synchronization brackets and their actual
member masks. A full-mask synchronization can publish for the whole actual
block only when that block fits within a single native warp. Partial or
multiple-warp scopes are not promoted to a CTA publication fence. A source
warp fence may have no physical instruction after code generation; its
counter bracket does not imply hardware engine activity.

Previously qualified NVIDIA early-recorder captures retain their isolated
observer-relative ns exports through the legacy reader. Ascend 910B c220-vector
captures also have counter-unit-only exports. Neither these legacy exports nor
the new raw default complete P01 or the full three-backend timeline.

```bash
python -m flagtree.profiler.cli --detail timeline --device 0 -n trace-run my_script.py
```

The equivalent API is `start("trace-run", detail="timeline")`, followed by the
ordinary workload and `finalize(session)`. Open `trace-run/timeline/index.json`
to locate original raw records, decoded timestamps, logical async facts,
source/compiled artifacts and per-invocation metadata. No kernel scope or site
annotation is required. When target-specific counter-unit evidence is available,
`trace-run/timeline/index.html` links the standard `.pftrace` files. They contain
counter brackets, not certified source-operation costs or engine busy. Raw ticks
without unit evidence remain raw; separate observers must not be compared as a
shared epoch. The index does not upload data.
Automatic timeline selection defaults to eight logical sites plus required
asynchronous mechanism sites. To compare observation density without changing
kernel code, use `start("trace-run", detail="timeline", timeline_max_sites=4)`
or CLI `--detail timeline --timeline-max-sites 4`. The integer budget is 1..128;
it is rejected outside timeline mode. It is not a total event/site cap: mandatory
async boundaries remain selected. A smaller budget can omit source/consumer
detail, so inspect the actual compiler inventory and capture coverage. Changing
density does not certify schedule preservation or low overhead.

NVIDIA's late layout is `nvidia-late-1`, not the historical Proton raw3
layout. Default selection uses the actual first/last logical programs and the
first four actual threads for ordinary non-async/matrix code. Native asynchronous
copy or matrix operations retain the complete actual CTA participant footprint;
partial coverage never acquires collective dependency eligibility. Each actor
has bounded records and explicit arrival/overflow. Arrived-empty and divergent
streams remain valid raw outcomes even when a dependency model cannot use them.

The existing CUDA stream/event transport retains a 128-byte allocation guard.
Completed owners can be read back and durably retained before later admissions;
no device-wide synchronization or application replay is inserted. Pending bytes
and cumulative admitted raw bytes have separate 8MiB limits. Original optimized
LLVM is carried through the compiler cache, so a warm binary does not depend on
a prior capture's temporary directory. The hook reconstructs the producer layout
with the bound native executable before authorizing allocation, rather than
trusting cached scratch dimensions alone. Raw, guard, compiler/source artifacts
and per-invocation identity are saved before releasing completed device storage.

Late captures retain the decoded report named by `decoded_file` (plain JSON or
explicitly tagged gzip JSON), canonical JSON named by `events_file`, and
`.late-async.json`. The canonical time view explicitly selects up to four actual
threads per program after validating the whole captured raw. Complete CTA raw
remains available for other views and dependency footprints; this display
selection does not lower instrumentation work or hide loss in other threads.
Backend-provided display groups collect related native sites into readable
tracks, retaining every event, its actual coordinates and raw references.

A consistent
byte model reports observed submit/commit/wait/publication/consumer and reused
buffer generations, with no verified time arrows. Opaque side effects or
incomplete/divergent collective participation leave raw data available and
explain why this particular model cannot be used. This is not a hardware busy
or source-cost measurement. Final acceptance still requires the full clock,
dynamic time-flow, source-boundary and three-backend evidence in the goal.

The byte lifecycle model `nvidia.late.shared_byte_lifecycle.v2` retains each
program-local generation's producer ordinals, commit ordinal, first covering
wait return, first publication barrier and consumer ordinals. Its shared ranges
are exact `[offset_from_actual_shared_base, length_bytes]` pairs; gaps are not
filled. Each submission retains its own ranges separately from the complete
generation ranges (`generation_shared_ranges` in event coverage). Reuse ranges describe current byte ownership when the new producer
writes, rather than the previous generation's historical footprint. A commit
group may span several ranges; it is not an assumed fixed hardware buffer slot.

Selected canonical events carry these conditional roles under
`coverage["nvidia.dynamic_dependencies"]`, alongside the actual native ordinal,
payload offsets and raw endpoint references. Standard Perfetto slice details
therefore identify the generation and physical byte ranges of the observed
submission, commit, completion observation, publication, consumer or reuse.
Completion observation means a recorded native wait/barrier return, not an
engine's physical completion instant. Roles are derived from the full captured
CTA before view selection; an incomplete or ineligible collective model adds
none. They do not create duration spans, align observers or authorize flows.
Offline upgrades derive a new canonical revision without replacing historical
canonical events or traces; newly enriched trace bytes intentionally differ
from earlier revisions. Legacy raw protocols remain readable.

`compiler-attempts/index.json` in the final timeline directory identifies retained
ordinary/instrumented LLVM, manifests, stdout/stderr and actual compiler process
receipts. Raw owner salvage precedes this retention, so a derived/copy failure
cannot prevent other completed calls from preserving original data. A public
`finalize` failure wraps the original exception as its cause and reports internal
staging; finalized session IDs are no-ops. In-process ownership recovery uses the
retained hook and the original staging base; fully retained captures can then be
re-exported with the public offline command. Compiler receipts survive copying
the recovered timeline and removal of owned temporary staging.

The current public raw paths support NVIDIA, Enflame GCU and Ascend CANN,
eager and one host thread per session. All three have actual multiple-stream
ownership evidence; nested sessions are explicitly rejected. Ascend now uses
its own stream/event transport with the shared owner and canonical schema 2.
Its full source-region, read-precision, cross-observer and async qualification
remain incomplete. Ascend counter-unit exports are described below; raw success
or unit-only Perfetto files are not full P01 acceptance.

For Ascend, select the runtime device before the API session and use
`backend="cann"`, or run:

```bash
python -m flagtree.profiler.cli --backend cann --detail timeline --device 4 \
  -n trace-run my_script.py
```

Use the matching [Ascend build](../../integration/patches/ascend/README.md),
including the version 3 source-coordinate carrier and the new LLVM15 paired
producer. `TRITON_ASCEND_COMPILER` must name a compatible SDK; the actual
installation receipt identifies the tested replacement. The collector binds the
real loaded binary, actual logical grid and original NPU stream. It initializes
compact storage with two 64-byte allocation guards on that stream and records
a completion event; it does not insert a per-launch global synchronization.
Readback happens during finalization, after the event reports completion.

Ascend selects first/last logical programs and reserves AIC/AIV actor segments.
New timeline compilations also seal each available actor object into the
compiler handoff as `compiled_object`, checking its receipt hash/length and a
32 MiB per-object bound. This survives compiler scratch cleanup and permits
later offline inspection. A missing object is explicit; old captures remain
readable. Retaining object bytes grants no counter-unit, source-boundary or
shared-clock qualification.

On the inspected Ascend910B c220-vector installation, default finalization uses
`llvm-dwarfdump-15` (or `llvm-dwarfdump`) to retain exact private clock-marker
rows from the actual loaded ELF. `FLAGPRISM_ASCEND_DWARFDUMP` can select an
absolute executable. Missing tools or an unsupported machine mapping leave raw
captures available with an explicit diagnostic. The matching new LLVM plugin
must emit clock-marker version 1; old captures remain readable.

New source-timeline compilations also declare `native_control_version=1`
in the actor binding. The late pass automatically brackets existing
`llvm.hivm.SET.FLAG.IMM` and `llvm.hivm.WAIT.FLAG.IMM` calls with static,
nonnegative i64 pipe/event arguments. It adds no native flag or wait. These
records use semantic codes 2/3 in the existing paired physical layout; source
fragments retain code 1. The decoder requires the feature version and the exact
original intrinsic/arguments. Old code-1-only captures remain readable.

Coordinates come from the original containing fragment, or from six actual
carrier operands that all dominate the native control. The latter binding is
explicitly coordinate-only; it does not identify the control with the carrier's
source operation. Native debug locations are retained separately for navigation.
Unbound controls, unsupported primitives and nonconstant arguments have explicit
unobserved reasons in the compiler control plan.

Native track names describe **scalar control brackets**, with pipe/event
arguments in their details. They do not certify destination-pipe completion,
engine activity, buffer generations or dynamic dependencies. In the real r048
runtime-K recurrence and Softmax development captures, each invocation retained
20 native brackets. The recurrence recordings had 36/44 total intervals as K
changed; the native count stayed 20 because additional iterations did not require
additional flags. All 20 native brackets in this Softmax capture had equal start
and end ticks. Zero-width brackets remain unchanged, rather than receiving an
invented duration. The source fragments still contained multiple positive
intervals. These finite observations do not qualify the asynchronous pipeline
required by the three-backend goal.

With native-control feature version 2, the producer also marks each existing
native instruction separately from its two counter readers. The inspected
c220-vector mapper checks the actual loaded ELF, retained DWARF, exact compiled
flag-word references, all instruction clones and getter brackets. Unknown words,
unmapped clones or unobserved native controls prevent dependency qualification.

The public path now writes `observed_dependency_exports` when these checks and a
complete actual scalar record stream succeed. Each file has
`clock_scope_kind=single_observer`; other actors keep their original unobserved
or incomplete status. The default multi-observer counter proof still requires
at least two observers and complete captured input. No inter-observer epoch is
granted by the single-observer path.

Native flag generations follow complete scalar issuer order for the actual
source pipe, destination pipe and event ID. SET-to-WAIT arrows describe that
queued generation. A WAIT targeting PIPE_S supplies a scalar readiness
observation at its exit. Other WAIT exits only observe enqueueing. These are
not physical completion instants or engine busy intervals. Source containment
arrows require both the compiler's original fragment binding and actual dynamic
record/tick enclosure; they do not assert a buffer dependency or source cost.

Open the resulting standard Perfetto trace from `timeline/index.json`.
Native checkpoint details include channel/generation relations, raw offsets and
ticks, user source navigation, final instruction candidates and getter ranges
in `backend_evidence`. Compiler-generated instruction clones remain distinct
candidates; they are not counted as additional dynamic executions. Historical
feature-1 recordings remain readable through the counter-unit path.

The final-image mapper distinguishes the inspected c220 vector executable
(`e_flags=0x930000`, AIV job) from the mixed executable (`e_flags=0x940000`,
AIC cube and AIV vector jobs). The mixed path checks both actual compiler jobs,
actor functions and exact SYS_CNT marker locations. A small reference compiled
with the actual cube driver command matches the vector SYS_CNT encodings;
this does not establish a shared AIC/AIV epoch or hardware engine activity.
Unknown executable kinds or mismatched jobs retain raw data with an explicit
unavailable mapping reason.

The Ascend unit provider binds the actual runtime model/device, loaded binary,
SYS_CNT instruction locations, original raw records and a bounded host window.
For the documented A2 counter, one tick is 20 ns. This does not apply to other
Ascend generations. New real recurrence and Softmax captures generated six
standard observer-relative traces; fresh public/normal/optimized re-export
preserved originals without application replay or NPU initialization. Offline
re-export rechecks retained ELF/DWARF without running a compiler or tool. No
runtime model is reconstructed for old captures that lack its snapshot.

These files show **counter brackets** with unknown read precision and source
boundaries. SYS_CNT reads do not insert pipeline completion barriers; a bracket
must not be interpreted as another engine's activity. Separate observers have
separate files and no verified time flows. Full pipeline qualification remains
pending. See [Ascend counter-unit evidence](../../integration/evidence/timeline-ascend-counter-unit-r031/README.md).

An unwritten admissible segment remains explicitly unobserved unless the new
versioned `runtime_participation` publisher proves it was not selected. On the
supported c220 vector target, this publisher records the actual device
`GET.SUBBLOCKDIM` in header flags bits 8–9; cube actors publish one. A reported
single vector participant excludes reserved AIV slot 2 only after checking the
entire excluded segment is zero. Missing expected actors, conflicting counts,
unsupported counts, or data in an excluded slot remain errors or incomplete
captures. Old logs without this feature retain their original unknown slots;
the decoder never infers participation from empty bytes or an operator name.
This feature requires matching rebuilt late-plugin and Python decoder inputs;
its new device qualification is recorded separately from earlier captures.
Current real recurrence and Softmax probes use
`enable_auto_blockify=False`; broader lowering, multi-function and exclusive
writer coverage still require qualification. Do not infer general matrix
support from these examples. The legacy debugger allocator rejects the new
layout; the dedicated timeline collector handles it explicitly.

The r020 checkpoint covers actual API and CLI math, two-stream collection,
exact raw endpoint offsets and retained guards, fresh-process public/normal/
optimized offline re-export, and controlled host decode/guard faults. On a
failed API finalization, intermediates remain in the reported session staging
directory; use its actual `capture.timeline` path for recovery rather than
assuming the requested output bundle was completed. See
[Ascend public raw evidence](../../integration/evidence/timeline-ascend-public-r020/README.md).

For GCU, use the same API with `backend="enflame"` (or allow backend detection),
or the CLI with `--backend enflame --device 0`. The normal
[Enflame build recipe](../../integration/patches/enflame/README.md) must build
matching compiler/runtime `GCU_TIMELINE_STORAGE_VERSION=2` and
`GCU_TIMELINE_PUBLISHER_VERSION=2`; an old beta publisher is rejected. The public
collector selects real first/last programs using compact physical rings, records
completion events on the original GCU stream and defers readback until
finalization. It retains the native initialization handle, including host staging,
until completion and durable retention. Legacy advanced mode keeps its historical
completion behavior. An arrived-but-empty ring is distinct from a host-initialized
ring whose selected writer never arrived.

Real API cold/warm, standard CLI and two-stream decoder-failure recovery evidence
is indexed in [GCU owner evidence](../../integration/evidence/timeline-gcu-owner-r016/README.md).
Those older results establish raw collection. The newer GCU300 time views
below add a per-physical-counter empirical scale and actual Perfetto checks.
That stage did not qualify shared epochs, final source boundaries or DTE
dependencies; the late execution path below separately adds observed tag relations.

Build with the matching `preallocation-admission.patch` v2: it passes the actual
launch stream before either scratch allocation and exposes admission ABI 2.
An old launcher is rejected before hook activation. Compiler and launcher/hook/
runtime file fingerprints enter timeline JIT cache identity before lookup;
per-capture epoch qualification is separate. Count/native modes keep their
existing meaning.

### GCU per-physical-counter time views

The GCU300 default first/last publisher now requires matching runtime/compiler
`GCU_TIMELINE_CLOCK_IDENTITY_VERSION=1`. Each compact record retains the full
`llvm.dtu.movs.sipinfo` identity of the actual counter observer in its identity
word. The selected logical work-item is still 0; the identity word is not its
logical work-item number. Old append layouts and compact captures without this
feature retain their previous decoding rules.

The SDK's masked SIP identity aliases actual identities 0 and 544 on the tested
device. Its `global_timer` getter also has different observed counter origins
across those identities. Neither the getter name nor equal tick rates authorizes
a shared epoch. The producer and a separate profiler-owned 64-program sampler
link the same owned full-identity helper. The maintained source build creates
and installs the new publisher; no user-kernel annotation is needed.

Before user profiling, four independent host-enclosed samples freeze a rational
scale interval for each observed physical identity. After all original user raw
buffers are safely retained, four held-out samples close that session window.
The offline provider verifies retained raw words, executable/helper/SDK digests,
identity association, training seal, host/raw enclosure, and held-out consistency.
It never estimates frequency from user-kernel runtime, widens the training fit to
include a failed held-out sample, or merges identities with a similar rate.

A successful capture reports
`counter_ns_status.status=empirical_counter_unit_for_enclosed_window` and has
standard observer-relative `counter_ns_exports`. The raw canonical clock and
source-boundary status remain unverified: this derivative grants a finite-window
empirical scale, not a common epoch, hardware read precision, exact source cost,
physical engine busy, or asynchronous completion timing. The view exposes the
rational rate uncertainty separately through `conversion_scale_error_ns` and
`endpoint_conversion_scale_error_ns`; these are not hardware precision bounds.
Missing physical-domain samples or inconsistent windows preserve originals and
an explicit unavailable-unit reason rather than a fabricated nanosecond trace.

A [finite audit of an existing GCU300 ELF](../../integration/evidence/timeline-gcu-clock-helpers-r066/README.md)
corroborates the SDK getter's 46-bit returned-value ceiling and the unmasked
SIPINFO identity helper. It does not establish the physical counter's exact
width, bind every inlined reader to raw records, or authorize a shared epoch.

Use the normal source-build recipe and public CLI:

```bash
"$FLAGPRISM_BUILD_DIR/venv/bin/python" -I -m flagtree.profiler.cli \
  --backend enflame --detail timeline --device 0 -n /tmp/my-timeline my_script.py
"$FLAGPRISM_BUILD_DIR/venv/bin/python" -I -m flagtree.profiler.timeline_reexport \
  /tmp/my-timeline/timeline
```

For `detail="timeline"`, `report/index.html` provides compact links to the
actual exported traces and their clock qualifications. `report/execution.html`
links the retained execution JSON and source-linked view. These pages avoid
embedding duplicate machine-readable metadata; raw data, compiler artifacts,
JSON and Perfetto files remain retained. Exact duplicate compiler metadata in
`ai/binaries.json` and `report/report.json` can reference the unchanged
`ai/execution.json`. `ai/metadata_refs.json` registers the reference locations,
file hashes and logical value hashes. A reference is not missing metadata.
Read a complete logical view with the common, device-independent reader:

```python
from flagtree.profiler.bundle_metadata import load_bundle_json
report = load_bundle_json("/tmp/my-timeline", "report/report.json")
binaries = load_bundle_json("/tmp/my-timeline", "ai/binaries.json")
```

The reader checks hashes and bounded RFC 6901 pointers, rejects cycles and paths
outside the bundle, and reads legacy views without a catalog normally. It does
not execute the application or access its compiler cache. The catalog applies
only to registered locations, so similarly named fields in user metadata remain
literal values. Other detail modes keep their existing embedded reports. Compact HTML reduces output size but is not, by itself, a
hard admission bound on an arbitrary application's complete capture bundle.

Open the bundle's `timeline/index.html` to find the `.pftrace` files, then load a
file in standard Perfetto. Each file has its own time origin. Do not align those
origins to compare different programs, calls or physical identities. Raw data,
clock anchors and original compiler evidence remain in the bundle; re-export
requires the matching installed decoder but does not run the SDK or workload.
Legacy captures without the retained full-identity window remain raw-only.

The [run-050 evidence](../../integration/evidence/timeline-gcu-physical-clock-r050/README.md)
covers a clean native/source build, installed normal/optimized API cold/warm,
20 exact raw/SQL-checked traces and all 20 actual Perfetto views. Fresh-process
public and guarded normal/optimized re-export reproduce their original bytes.
These finite cases do not complete GCU DTE dependency or general-kernel acceptance.

### GCU late execution recorder and observed tag dependencies

On matching GCU300 installations, automatic first/last requests use
`gcu_execution_timeline_v3` and `GCU_EXECUTION_TIMELINE_VERSION=1`. The normal
build packages the `gcu-timeline` native tool. It observes actual SDK execution
primitives after ordinary lowering, rather than inserting a source-level DMA
logger between the application's transfers. Selected work-item 0 retains
128-byte records in a local ring and publishes it through one private-tag DMA
at the original return. Legacy compact/append captures keep their readers.

Records retain paired device timestamps, full physical counter identities,
actual tag-storage/index values, and buffer descriptor addresses and IR memory
spaces. `gcu_ptr2int_i64_v1` preserves full-width device addresses: GCU300's
32-bit `index` is not a safe carrier for global pointers. These addresses also
differ from a Tensor's host-side `data_ptr()`; TOPS translates the latter before
device use. Tag-storage identities are local to the recorded issuer. They do
not identify a globally shared hardware queue.

The backend matches a submission to its same-tag wait return and advances the
tag generation after that return. Qualified captures publish
`observed_dependency_exports`. In Perfetto, select an observed dependency
checkpoint to inspect tag generation, source/destination descriptor addresses,
raw offsets and source navigation. The same file retains actual issue/wait and
region intervals. An initially idle wait has no invented producer; ambiguous
tag reuse, unobserved primitives or incomplete records retain a diagnostic and
the independently available interval data.

Each dependency file covers one actual observer and its own counter origin.
The empirical period uncertainty remains visible on slices and checkpoints;
hardware read precision is unknown. Do not align different files to infer
parallelism. A wait-return observation is not the precise hardware completion
instant. Descriptor write generations do not certify byte coverage, absence of
aliasing, or readiness for an unobserved consumer. These views grant neither
engine-busy measurements nor exact source-operation costs.

The maintained `tests/timeline/p01_enflame_native_arguments.py` runs two ordinary
runtime-K GEMMs through the public API and compares recorded global addresses
with actual per-launch TOPS translations. The complementary
`p01_enflame_observed_dependencies.py --timeline BUNDLE/timeline --output OUT`
checks retained real tag generations and exports without replaying the workload.
These development cases do not replace the independent mathematical matrix,
controlled perturbation cases or final three-backend acceptance.

### Legacy early NVIDIA recorder and retained captures

The earlier automatic timeline compiler requires native
`TIMELINE_BOUNDARY_VERSION=3`. Its plan reports
`timeline_boundary_strategy="runtime_zero_gated_calls_pending_region_audit"`.

The shared-view candidate additionally requires `TIMELINE_RECORD_VERSION=3`;
it is under device qualification and is not a full timeline acceptance result.
Its 32-byte records preserve the complete timestamp/sequence and carry the
runtime shared-memory view origin for automatically selected asynchronous copy
destinations and local-load sources. The origin includes the converted stage
base, affine slice offset and layout padding; it is not inferred from site IDs
or occurrence counts. Complete histories can associate committed attempts and
wait-covered same-origin loads. Masks may suppress byte movement, equal origins
do not establish equal footprints or safe reuse, and no clock/boundary or engine
activity certificate follows. Existing 16-byte v2 originals remain readable;
their missing shared-view information is never reconstructed from ordinals.

A reserved mutable module global is initialized to zero and loaded once per
function with a volatile device read. Begin timestamps feed bit-preserving
XOR anchors masked by that runtime value; end dependencies control a branch to
an explicit zero-argument noinline clock helper. No user kernel argument is
added. The global has no instrumentation writer; actual development probes also
read its four bytes through the CUDA module API after checking the real math.
Helpers return 64-bit timestamps and retain native site/phase markers. NVIDIA getter inline asm
also declares an LLVM memory clobber, constraining memory motion without emitting
a GPU completion barrier. The helper call ABI is target-specific, not a required
backend-neutral hardware interface.
Explicit version-2 IR retains its historical lowering; the automatic public
path requires version 3. Compiler/cache identity includes this implementation
and declares the matching version in its instrumentation-mode key. Unsupported boundary
versions are rejected in plan extraction and lowering; old native plugins are
rejected before public hook activation.

These are compiler constraints, not certified machine boundaries. PTXAS may
schedule beyond LLVM dependencies, and issue/wait/native engine semantics still
need their own evidence. Tokens and memory descriptors are not reinterpreted as
ordinary register values. Legacy interval/count paths do not acquire the new
operand forwarding. Raw `boundary_status` stays `unverified`; no ns or hardware
completion claim follows from the version flag or the memory clobber.

The compiler also requires `TIMELINE_MARKER_VERSION=1`. With a compatible
`nvdisasm` installed in the current product prefix, on `PATH`, or supplied as an
absolute executable path through `FLAGTREE_NVDISASM`, finalization optionally
binds every selected site/entry/exit marker to actual cubin PTX-debug lines and
SASS PCs. It retains tool version/hash, original text/JSON disassembly, command
receipts and `machine/<binary_id>/counter-map.json`; each capture refers to this
through `machine_counter_mapping`. Exact function symbols also bind helpers in
the parent code section at nonzero offsets; each map retains function ranges,
code section, section-relative PC and function-relative PC. Actual instruction
bodies cannot overlap or exceed executable ELF section extents. These fields
locate reads and do not certify the caller region. Maps also retain
`static_model_version=1`, `call_sites`, `counter_call_sites` and
`synchronization_sites`. Direct calls require exact text/JSON target agreement;
unknown targets stay unresolved. Synchronization operands are checked too.
Multiple readers/callers remain explicit; inline readers can have no direct
caller. Expanded counter/caller references are capped at 65,536; exceeding this
budget preserves raw data with mapping unavailable. Static inventories cannot
establish dynamic counts, preserved scheduling, native busy or clock alignment.
Tool absence or a failed mapping preserves
raw data with an explicit unavailable reason. No application replay or network
download is performed. Postprocessing is bounded by the shared export deadline.

For late inline readers on the inspected SM120 target, finalization writes
`machine/<binary_id>/late-wait-control.json`, referenced by each capture's
`native_wait_control_file`. Model `nvidia.cp_async.late_wait_control.v1`
revalidates the two disassemblies and checks that each matching inline reader
pair encloses one native wait with its actual pending-group limit. External
branches/reconvergence cannot enter after the entry reader; paths between the
readers must execute the unpredicated wait. Missing or duplicated reader PCs,
unknown control and ambiguous waits retain an explicit unverified diagnostic.
The public offline reexport derives the same report under a new control revision.
Its shared helper-rule digest is included. These are native control-order facts;
raw-value provenance, participation, precision, shared epochs and time flows
remain separate. No device instructions or barriers are added by this check.

On the inspected sm_120 leaf-call pattern, finalization also writes
`machine/<binary_id>/wait-control.json`. This separately binds branch labels,
predicates, helper bodies and native wait operands across the two disassemblies,
then checks bounded forward paths between the matching counter calls. A
`wait_control_order_checked` site establishes only native wait control order.
Record-value provenance, source-region timing, participation, clock precision
and hardware overlap remain unqualified. Unknown paths retain a specific reason.
This analysis adds no device instruction or synchronization.

Model `nvidia.cp_async.wait_control.v2` also reports
`endpoint_store_value_flows`: the full timer pair through helper/caller moves
into the tag/low/high words of a shared vector store. Word swaps, clobbers,
changed predicate generations and unknown writing opcodes lose this fact.
`counter_to_shared_store_values_checked` is conditional on executing that call
and store; it does not establish call dominance, raw-buffer addressing or full
record provenance. Those flags remain false. Original v1 reports are retained.

`counter_mapping_complete_region_unverified` means the static counter PCs are
located, not that the observed operation stayed inside their machine boundaries.
Line matching permits only erased `.loc`/`.file` and typed DWARF data in explicit
debug sections; executable tokens, line positions and actual text/JSON getters
must agree. Duplicated static PCs remain candidates, not exact per-occurrence PC
attribution. Read suppression, source-region ordering, completion and clock
qualification still require separate proof; raw event status stays unverified.

On the inspected sm_120 objects, exact marked PTX `mov.u64 %globaltimer` reads
lower to both `CS2R Rn,SR_GLOBALTIMERLO` and `CS2UR URn,SR_GLOBALTIMERLO`.
The mapper checks the matching opcode/register bank and original debug/object
binding; a uniform register is not a different timing qualification. Wrong banks,
32-bit/HI variants and unknown opcodes do not inherit the unit proof.
Actual version-3 runtime-K and GEMM math/raw/maps work, but the GEMM ordinary
control has 12 static HMMA instructions and the observed loop has 4, with changed
static synchronization structure. This candidate has not established preservation
of the ordinary pipeline or automatic source-region boundaries; neither counts
nor positive durations remove that qualification gap.
The actual source/build/install, original-failure recovery and compiler-stage
comparison are recorded in the [v3 engineering checkpoint](../../integration/evidence/timeline-boundary-v3-r022/README.md).


`timeline_runtime.TimelineOwnerPool` owns one independent record allocation per
invocation. `timeline_cuda_runtime.CudaTimelineTransport` supplies the actual
CUDA allocation, stream-local initialization, completion event and readback.
The common owner layer delegates physical storage planning to the transport;
it does not parse CUDA instructions or assume a warp/SM topology.

The collector binds the compiler plan to the actual loaded binary and function,
then calls `prepare` with the actual launch grid/device/stream. Both the single
allocation requirement and all pending physical bytes (including guard bytes)
must fit before allocation. `allocate` hands back the hidden launch buffer.
Immediately before invoking the launcher, `mark_submitting` conservatively
records that work may be submitted. After it returns, `finish_submission`
records a completion event on that invocation's stream. It does not wait.

Only after submissions does the collector call `read`, validate/decode/persist
the returned immutable raw bytes, then `release` that owner. The live owner
snapshots the plan, selection, binary, grid and stream, so later invocations do
not overwrite its metadata. Separate CUDA streams and many pending invocations
are supported by the timeline path; its pool is restricted to the creating host
Thread object. The legacy count/native shared-buffer hook retains its existing
concurrency restrictions.

Initialization may itself submit writes. Consequently, `abort` can immediately
remove an admitted owner without an allocation, but an armed or possibly
submitted owner first needs a stream completion proof. A timeout retains the
same handle and resource for a later poll; it does not mean the writer stopped.
Completion-query/recording errors quarantine the owner. Readback failures retain
the allocation and allow `retry_read` without executing the application again.
An active-owner registry prevents loss of the caller's Python reference from
silently freeing pending buffers; `retained_owner_statuses()` reports retained
pools. This retention is deliberate and may hold memory until explicit recovery
or process/context teardown; `close` reports an error while owners remain.

The `read` timeout bounds completion polling. A blocking driver/D2H operation
still needs the enclosing owned process deadline; Python cannot safely reclaim
that memory by cancelling a thread. CUDA graph capture is rejected before this
component allocates. The CUDA transport must run on the declared current device
and uses the actual launch stream for both initialization and completion.

Tests: `tests/timeline/test_timeline_runtime.py` covers safety contracts with a
fake transport (not device evidence). `p01_nvidia_deferred_owners.py` runs real
ordinary recurrence math, six interleaved launches on two CUDA streams with no
collector wait/read between them, reverse-order readback, budget rejection and
recovery. It checks numerical outputs, original side-effect counts, separate
in-flight allocations, canaries and decoded raw identity. This development test
does not certify physical clock/epoch, final machine timing boundaries,
hardware overlap, public profiler integration or complete P01.

## Clock arithmetic and current calibration boundary

`timeline_clock.bound_causal_offset` intersects four-read causal constraints
(A publish, B receive, B respond, A receive) without assuming symmetric delays.
It accepts explicit endpoint uncertainty, rejects inconsistent or locally reversed
observations, and keeps exact integer arithmetic. Inputs must already share a
fixed unit and coordinate origins; callers separately bind domain/epoch, prove
ordering and exclude reset/wrap. A raw-tick offset interval is not ns or a clock
certificate.

The dedicated two-CTA producer/consumer probe exercises this shared function
with real math and retained binaries; its current SMID-pair constraints and
training/held-out checks are [development evidence](../../integration/evidence/timeline-clock-causal-r011/README.md).
They do not qualify all SMs, absolute endpoint error, source-region boundaries
or public timeline/Perfetto. Raw event ABI/status and existing count behavior
are unchanged.

The installed common raw reader also supports schema 2 and the GCU
`timeline_events_enflame` adapter for existing advanced append captures. It
preserves atomic start/end fields, work-item identity, local-label provenance,
sampling and dropped-pair counts. The default GCU collector now also uses the distinct compact first/last layout
and this common reader. New feature-1 compact captures can additionally derive
finite-window empirical counter-ns views as described above. The legacy append
path still lacks that evidence. See [raw events](timeline_events.md) for the
versioned contract and evidence boundary.

## Finalization and recovery stages

Finalization nonblockingly checks completion and gives currently ready owners
readback/persistence opportunities before polling unknown writers. All owners
share the bounded finalization deadline; it does not promise arbitrarily many
ready buffers will fit. Unresolved owners and their states remain in the index.
Decoding and machine mapping follow this original-retention pass. Each original `.raw`,
`.input.json`, and required compiled/source artifact is persisted before its
completed device owner is released. The second pass decodes these retained files;
a decoder failure does not prevent other invocations from being saved or decoded.
Owners with unresolved completion/readback remain explicit and can be retried
when the transport permits it. A native SDK free error has an unknown outcome:
the resource ledger and admission budget remain retained, repeated release fails
explicitly without another free, and the quarantined handle cannot initialize,
read or supply a launch pointer. Successful sub-resource frees are not repeated.
Another invocation's failure never establishes that a resource is safe to free.

`attempts/flush-NNNN.json` preserves each attempted finalization and its failures.
The mutable `index.json` also identifies `pending_decode` and `retained_owners`;
its replacement is atomic, unlike the immutable per-invocation originals. The
first failure remains the raised error even if later journal persistence fails.
A successfully acquired but invalid readback is not a missing D2H result: the
payload, actual length, integrity errors and available `.guard.raw` are retained
before interpretation is rejected. Safe release follows completion and durable
raw/input retention, including corrupt captures. A later decode attempt does not
read the device again or reinterpret a corrupt guard as valid data. This guard
carrier is implemented by both CUDA and the current GCU timeline transport.
GCU's native runtime allocates a 64-byte prefix and suffix, initializes them on
the owner stream and copies the complete physical allocation back. The hidden
argument still points at the original raw layout; the guards are separate
128-byte evidence. Runtime binding feature
`GCU_TIMELINE_ALLOCATION_GUARD_VERSION=1` prevents Python from silently using an
older runtime without these guards. See the real-device prefix corruption and
subsequent-session recovery receipts in the
[r058 evidence](../../integration/evidence/timeline-review-fixes-r058/README.md).
A finite intact guard does not prove the absence of every possible large-stride
out-of-bounds access.
JSON slot maps are rehydrated to the physical decoder's tuple contract; raw
identity is checked again before decoding. This conversion changes no raw fields.

An in-process retry of the retained hook uses the same internal evidence directory
and only rereads the saved inputs for owners already released. The public API may
use an internal staging directory different from the requested bundle path; on
failure it reports retained intermediates. This retry still handles ownership
inside that process. The separate offline command below consumes fully retained
inputs without relying on that hook or owning a device buffer. It cannot recover
bytes that were never read back or release a still-active device owner.

## Offline decoding and versioned counter traces

Use the Python from the matching installed FlagTree/FlagPrism wheel:

```bash
python -m flagtree.profiler.timeline_reexport trace-run/timeline
# Optionally select one retained invocation:
python -m flagtree.profiler.timeline_reexport trace-run/timeline --invocation-id INVOCATION_ID
```

The directory must contain `captures/*.input.json`, matching raw bytes and
required source/compiler artifacts. The command verifies sizes/digests, decodes
raw again and writes an immutable `derived/canonical/<revision>/events.json`.
It does not trust a previously written events/view document as evidence. NVIDIA
counter-ns re-export additionally requires the retained cubin/PTX, machine-map
status and text/JSON disassembly: the target-specific provider re-parses those
inputs and binds its result to this binary/raw/observer and recorded host window.
A historical `counter_mapping_unavailable` diagnostic can be revalidated by
new rules if its complete original object and text/JSON inputs remain. The
command does not rerun tools or the application, or overwrite that first status;
it saves the newly derived map and input digests under `derived/machine/<revision>/`.
The same command derives `derived/control/<revision>/wait-control.json` and
returns its path as `wait_control_file`; rules and plan digests bind the report.
Old bundles can acquire these facts without replay or changing their originals.
An unavailable control analysis is explicit and does not suppress otherwise
valid counter-unit exports.
A prior successful map must still match the fresh parse. Missing or inconsistent
required machine evidence is an explicit error; the canonical revision and
original capture remain. GCU captures with a valid retained full-identity clock
window now return `counter_unit_only`; legacy or unqualified captures return
`raw_only` with the missing-unit reason. Ascend paired captures can derive
counter-ns and qualified scalar native dependency views from their retained
getter and final-image evidence; other epochs and physical busy remain unverified.

`derived/counter-ns/<revision>/` contains a canonical snapshot, inputs, views,
traces and `complete.json`. Revision identity includes canonical/raw identity,
proof contents, actual provider/rule implementation fingerprints and the pinned
Perfetto schema. The same complete inputs are idempotent; legitimate proof/rule
changes create another revision and preserve old files. These mechanics do not
authorize arbitrary caller-supplied proof JSON: the offline NVIDIA path obtains
proofs from the actual retained-target validator.

A bounded OS file lock serializes cooperating exporters. Files are synced and
immutable; the completion receipt is the commit point. The atomic HTML index
only discovers content-checked complete receipts, so a trace written before a
failure is not advertised as complete. Retrying can finish that same revision,
and can rediscover a receipt committed before an index-write failure. Changed
committed bytes are rejected, not silently repaired. Retained counter traces are
bounded to 16 MiB across these revisions; the derivative tree has a separate
64 MiB cap. This does not certify the separate whole-bundle/session budgets.

Real server-Docker checks exercised the public module and fresh normal/`-O`
processes on retained NVIDIA and GCU captures. NVIDIA re-export ran with no GPU
visible, an empty working directory/cache, and two audited processes denying
Python reads/execution in the original environment and child-process launches;
these are audit-hook checks, not an OS sandbox. The new
NVIDIA capture also produced 32 actual traces checked by generated protobuf and
real Trace Processor; six were opened, expanded, selected and focused in standard
Perfetto UI, with the bundle unchanged. These checks cover counter-unit-only
export plumbing, not fine timing precision, final source boundaries, physical
async reuse, time flows, independent-math qualification or full UI acceptance.
See [r018 evidence](../../integration/evidence/timeline-reexport-ui-r018/README.md).

### Late NVIDIA native boundary diagnostics

For inspected SM120 late captures, `native_boundary_control_file` names the
retained `late-native-boundaries.json` diagnostic. The public offline exporter
also derives this report under its versioned control report's
`native_boundaries` field without replaying the application. Original PTX
instruction lines are bound to actual LDGSTS, LDGDEPBAR, BAR.SYNC and LDSM
instructions through the retained object and both disassemblies. Per-site
`native_boundary_control_order_checked` means a conditional forward control
order relative to the inline reader, with external entry rejected. Unknown,
predicated or ambiguous forms remain explicitly unverified.

The same report's `source_issue_sites` checks a finite set of scalar global
32-bit loads/stores and FP32/integer arithmetic. A checked entry binds an
original PTX operation to its final SASS instruction strictly between both
readers, with a straight path and no external entry after the first reader.
Conditional memory issues retain their native predicate without claiming its
identity or that every lane executed the memory operation. Unsupported or
multi-operation forms stay unverified. In particular, adjacent readers with
the computation hoisted or sunk outside them do not pass this check.

Recorder manifests with `compute_operand_fence_version=1` add bit-preserving
compiler dependencies from the entry reader to external compute inputs and
from externally used compute results to the exit reader. Internal intermediate
results are not artificially made live, preserving contraction opportunities.
These dependencies add no device synchronization or replay and do not by
themselves certify final-machine order. The source-issue diagnostic checks the
actual emitted code; elapsed intervals include instrumentation and other work
between the readers, not exclusive arithmetic latency or engine activity.

This diagnostic does not establish the timer-to-record register/store value
flow, all-participant execution, source-region cost, engine busy intervals or
physical completion times. It does not enable dependency arrows. Each report
retains implementation digests so a future offline rule can derive a new
report while preserving the initial raw capture and diagnostics.

For late SM120 captures the native boundary report additionally contains
`timer_store_values`. Its `timer_to_native_store_values_checked` entries bind
both words of each actual full-width getter to native STG.E.64 stores mapped
from original PTX. The bounded reaching-definition analysis covers branches,
register moves (including overlapping MOV.64), predicated writes and matched
forward reconvergence regions. A path bypassing the getter, an overwritten
word, an unknown instruction or an ambiguous control pattern remains unverified.
Implementation fingerprints and the inspected native/store PCs are retained.

This establishes the stored timer value at the identified native instruction.
It does not yet prove that the address expression selects the allocated raw
slot, that payload/address geometry is correct, or that a publication represents
all participants. `record_storage_binding_verified`, full
`record_value_provenance_verified`, payload qualification and time-flow rights
therefore remain false. Existing counter coordinates and original raw artifacts
are unchanged; this diagnostic is evidence for completing the dependency path.

The same late native diagnostic also contains `relative_record_fields`:
`native_record_fields_checked` means the actual four stores for a site's tag,
begin, end and payload have the declared coalesced relative displacement and
stable common native address/descriptor registers, the tag is the actual
literal, and both timer fields are the previously verified getter values.
Constant payloads are checked through all native reaching definitions. Wait
payloads additionally match the actual DEPBAR group limit; commit/barrier
reserved-zero payloads require their checked native control boundary.

Default captures independently retain `native_control_payload_file`, scoped to
the invocation and raw SHA. It records each decoded wait/commit/barrier payload
that agrees with the freshly checked native operand, including actual actor,
ordinal and exact raw tag/payload byte spans. Public offline reexport retains
this as `native_control_payloads` in its versioned control report. It never
updates a binary-wide static report with invocation-specific data.

Relative fields and decoded value agreement do not establish the absolute raw
allocation/program/ordinal address expression or variable shared-memory address
and valid-size payloads. Those qualifications and dependency flows remain
unverified. A mismatch is retained as an explicit diagnostic and does not grant
or remove an unrelated counter unit. No engine-busy interval is inferred.

### Native shared payload values and coalesced operations

SM120 late `native_boundary_control_file` additionally contains
`shared_payload_values`. The epoch-local native expression checker compares
both recorded payload words with the actual shared-memory operation's address
and width/source-valid predicate. Mutable loop registers get distinct header
inputs; loop-invariant aliases may be reconstructed only through acyclic
preheader definitions. An uncut loop or inconsistent reaching definitions
remains unverified. Expression hashes describe scoped symbolic values; they are
not physical address IDs shared between invocations or threads.

Adjacent scalar PTX loads may map to one native LDS.64. The report keeps every
source origin and byte subrange, checks their complete union when available,
and identifies the first source bracket that actually contains the native
operation. A later source observation with no separate native load is marked
explicitly; it is not presented as a second hardware operation or engine cost.
Matrix collective geometry remains distinct from scalar byte widths.

Default captures retain `native_shared_payload_file` per invocation. Its compact
`columns`/`rows` table binds actual program/actor/native ordinal, payload byte
offset/value, static native operation group and first ordinal of that dynamic
group. Raw byte domains, allocation bounds, source-valid byte sets and merged
source subranges are checked; the full collective byte model is recomputed.
Public retained-only reexport adds this as `native_shared_payloads` to its
versioned control report. No application replay is required.

These checks establish native payload-word relationships and decoded-domain
agreement. Absolute raw allocation/program/ordinal store-address binding still
remains separate, and full raw provenance, physical overlap, source cost,
engine activity and temporal flows are not granted by these reports. Kernels
without applicable shared operations produce an empty applicability result.
The separate real ALU test exercises the native LUT/64-bit selector families;
it is mechanism validation, not independent mathematical qualification. LUT
truth-table reference: [NVIDIA PTX ISA](https://docs.nvidia.com/cuda/parallel-thread-execution/#logic-and-shift-instructions-lop3).


### Native record ordinal addressing

The SM120 late report additionally contains `record_address_arithmetic`, and
captures retain invocation-specific `native_record_ordinal_file` tables. Public
offline control evidence contains `native_record_ordinals`. The bounded native
checker relates both pointer words to the published count header, checks each
LEA/LEA.HI.X carry and input lifetime, and associates a complete straight-line
store batch with its one full-width count update. Raw sequences must contain
whole native batches with matching field offsets; the final count is not used
to fabricate missing events. Initial count assignment and loop appends remain
distinct. Unknown native patterns retain explicit diagnostics.

This is header-relative record-ordinal binding. Absolute launch allocation,
physical program/thread header addressing and full raw provenance remain
separate requirements. No clock, physical overlap, engine-busy or temporal-flow
qualification is granted by this report. The default timing/old offline formats
are preserved when this additional diagnostic is unavailable.


### Native launch header origins

SM120 late captures add an invocation-specific `native_header_origins_file`;
public offline control evidence contains `native_header_origins`. The checker
uses the actual entry signature, ELF parameter table and referenced constant
bank symbol to locate the reserved scratch pointer. It checks both pointer
words, actual block dimensions, first/last program allocation, hardware thread
and block getters, native identity stores, magic, and the source-bound shared
symbol materialization. Context validation covers every recorded actor; a
binary-wide successful invocation cannot authorize another launch geometry.
This diagnostic is collected independently of clock-unit qualification.
Unknown metadata or machine patterns retain explicit unverified diagnostics.

`header_allocation_origin_verified` concerns the launch header only. Record
ordinals, timer/payload values, native control boundaries, collective byte
lifetimes and clocks remain distinct checks. This report alone grants neither
full record provenance nor temporal flows, source cost or engine busy.

### Lossless decoded-report storage

New late captures store the full auxiliary decoded report as `.json.gz` with
`decoded_encoding="gzip-json-v1"`. The raw native ABI, individual records and
values are unchanged. Previous plain JSON reports remain readable; an absent
encoding means `json-v1`. Use the same reader for both:

```python
from flagtree.profiler.timeline_decoded_reports import read_decoded_report

decoded = read_decoded_report(timeline_directory, capture)
```

The reader bounds decompression to 256 MiB and rejects truncated, concatenated,
oversized or corrupt gzip members and unknown codecs. Compression reduces
repeated field-name storage without sampling or removing actors, events or raw
references. Old count/native modes keep their existing plain report behavior.
The primary offline analysis still reconstructs events from retained raw data;
the auxiliary decoded report is a lossless convenience view.

### Reading the controlled examples

`tests/timeline/p01_controlled_workloads.py` exercises real runtime work and
matrix tilings without kernel annotations. In the recorded GCU C1 example,
the same instrumented binary executes work counts 3, 7 and 11. On program 0,
the repeated loop-body region (origin label `gcu.border`) has respectively
3, 7 and 11 occurrences. Its summed counter-bracket times across three captures
are 1514–1545 ns, 3496–3570 ns and 5503–5581 ns. This identifies the repeated
region and its measured growth; logger perturbation is part of these timings.

GCU C2 keeps the same 64-by-192 times 192-by-64 matrix product and changes
the reduction tile from 32 to 64. Program 0 then has six versus three
`gcu.matmul` brackets, summing to 811927–812126 ns versus 779536–779626 ns
over three captures each. The developer can inspect the surrounding actual
submit/wait records to distinguish fewer stages from shorter individual stages.
These are elapsed brackets in instrumented execution, not native engine busy
times, an uninstrumented speedup, or an overhead estimate. Re-measure ordinary
execution before claiming an optimization benefit. The original captures and
summary provenance are indexed in `integration/evidence/timeline-independent-deltas-r056/`.
