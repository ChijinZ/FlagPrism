# Timeline invocation ownership

The public hook/API/CLI collect source-linked raw internal timestamps. Captures
remain explicitly `partial_clock_unverified`. NVIDIA automatic timeline now uses
late instrumentation after ordinary LLVM O3, with a separately packaged matching
LLVM recorder and `optimized-llvm.patch`. On the inspected SM120 target, the late
layout now also maps actual marked PTX/CUBIN readers and exports standard
observer-relative counter-ns Perfetto files. These show observer issue brackets,
wait brackets and checkpoints, with conditional byte-dependency facts. They do
not establish precise source costs, hardware busy time, shared epochs or verified
physical time flows.

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

Late captures contain `.late-decoded.json`, `.late-events.json` and
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

An unwritten admissible segment remains explicitly unobserved; it is not proof
of execution or non-execution. Current real recurrence and Softmax probes use
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
This is a raw collection milestone: GCU clock scale/epoch, final source boundaries,
allocation-guard qualification, async reuse and Perfetto remain unqualified.

Build with the matching `preallocation-admission.patch` v2: it passes the actual
launch stream before either scratch allocation and exposes admission ABI 2.
An old launcher is rejected before hook activation. Compiler and launcher/hook/
runtime file fingerprints enter timeline JIT cache identity before lookup;
per-capture epoch qualification is separate. Count/native modes keep their
existing meaning.

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
and this common reader. Neither path is yet a certified ns producer or Perfetto
exporter. See [raw events](timeline_events.md) for the
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
Owners with unresolved completion/readback/release remain explicit and retryable;
they are never freed merely because another invocation failed.

`attempts/flush-NNNN.json` preserves each attempted finalization and its failures.
The mutable `index.json` also identifies `pending_decode` and `retained_owners`;
its replacement is atomic, unlike the immutable per-invocation originals. The
first failure remains the raised error even if later journal persistence fails.
A successfully acquired but invalid readback is not a missing D2H result: the
payload, actual length, integrity errors and available `.guard.raw` are retained
before interpretation is rejected. Safe release follows completion and durable
raw/input retention, including corrupt captures. A later decode attempt does not
read the device again or reinterpret a corrupt guard as valid data. This guard
carrier is implemented by the CUDA transport; GCU allocation guard qualification
is still separate.
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
original capture remain. GCU currently returns `raw_only`
with the missing-unit reason and does not invent a trace. Ascend's paired raw
producer also supports offline canonical revisions, while its time-unit and
Perfetto qualification remain unfinished.

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
