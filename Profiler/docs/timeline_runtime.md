# Timeline invocation ownership

The public hook/API/CLI now collect source-linked raw internal timestamps using
these ownership components. Clock certification, canonical ns events and
Perfetto qualification remain incomplete. The current output is explicitly
`partial_clock_unverified`, not a certified time axis or full P01 result.

```bash
python -m flagtree.profiler.cli --detail timeline --device 0 -n trace-run my_script.py
```

The equivalent API is `start("trace-run", detail="timeline")`, followed by the
ordinary workload and `finalize(session)`. Open `trace-run/timeline/index.json`
to locate original raw records, decoded timestamps, logical async facts,
source/compiled artifacts and per-invocation metadata. No kernel scope or site
annotation is required. There is no certified `.pftrace` yet; raw ticks must not
be interpreted as ns or used for cross-observer overlap without clock proof.
The current public path is NVIDIA-only, eager and one host thread per session;
it accepts multiple CUDA streams. Nested sessions are explicitly rejected.
Other backends still need their timeline producer paths.

Build with the matching `preallocation-admission.patch` v2: it passes the actual
launch stream before either scratch allocation and exposes admission ABI 2.
An old launcher is rejected before hook activation. Compiler and launcher/hook/
runtime file fingerprints enter timeline JIT cache identity before lookup;
per-capture epoch qualification is separate. Count/native modes keep their
existing meaning.

The automatic timeline compiler now also requires native
`TIMELINE_BOUNDARY_VERSION=1`. Its plan reports
`timeline_boundary_strategy="llvm_ssa_pending_machine_audit"`: begin timestamps
feed bit-preserving operand anchors and end counter calls consume observed
results. NVIDIA getter inline asm additionally declares an LLVM memory clobber,
which constrains memory motion without emitting a GPU completion barrier.
Compiler/cache identity includes this implementation. Unsupported boundary
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
through `machine_counter_mapping`. Tool absence or a failed mapping preserves
raw data with an explicit unavailable reason. No application replay or network
download is performed. Postprocessing is bounded by the shared export deadline.

`counter_mapping_complete_region_unverified` means the static counter PCs are
located, not that the observed operation stayed inside their machine boundaries.
Line matching permits only erased `.loc`/`.file` and typed DWARF data in explicit
debug sections; executable tokens, line positions and actual text/JSON getters
must agree. Duplicated static PCs remain candidates, not exact per-occurrence PC
attribution. Read suppression, source-region ordering, completion and clock
qualification still require separate proof; raw event status stays unverified.

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
