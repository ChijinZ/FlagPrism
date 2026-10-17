# Deferred timeline owner development checkpoint (T011)

This checkpoint verifies reusable per-invocation ownership and actual CUDA
stream-local completion/readback. It is **not public timeline hook/CLI support,
full P01, clock certification or Perfetto acceptance**. Only the existing
NVIDIA RTX PRO 6000 GPU0 Docker `chijin-study-pro6000` was used. No paper/Study,
other-user processes or system driver settings were changed. No NVIDIA
performance/overhead certification was attempted.

## Implemented and exercised

- `timeline_runtime.TimelineOwnerPool`: independent invocation IDs and snapshots,
  pending byte/owner admission before allocation, explicit submission/completion
  states, completion polling, retryable D2H, safe release and retained/quarantined
  owners. Physical planning is delegated to the transport. A pool is restricted
  to its creating Thread object, so OS thread-ID reuse cannot authorize sharing.
- `timeline_cuda_runtime.CudaTimelineTransport`: actual launch-stream allocation
  and initialization, stream-local completion events, later readback and optional
  canaries. Neither submission nor event recording synchronizes the host.
- Strong retention prevents a dropped Python reference from silently freeing
  buffers that may still be written. This can deliberately retain resources on
  an unrecoverable failure; it is reported rather than called successful cleanup.
- The old shared-buffer native/count hook is unchanged. These components are
  consumed by the installed real-math development collector; integrating them
  into the public profiler hook/CLI remains required work.

## Source, installation and tests

Initial source `56d5716da899f040fd048dd397b0f445f457da47` passed 15 owner contract
methods and seven storage methods, normally and with `-O`, plus the real device
collector. Source `2c5c85c1e0d3068f4ad689a55e43088017298aaf` then retained the actual
Thread object and added a nonboolean-completion negative: final 16 owner methods
and seven storage methods pass in both modes. The actual final installed modules
match these source bytes. The original two rounds remain separately indexed.
CPU fake-transport checks are contract evidence, not hardware evidence.

Both changes were Python-only packaging, each with Ninja reporting no work.
All seven native wheel members were byte-identical to their predecessor; the
first bridge binds to the actual `545bf8a` native build from r004. The final
wheel SHA is `5406558bf3c36e7fe949d9dbde62bfad2253e3747da7f97c4e1d7ac19768d03e`
(390631260 bytes). Fresh independent installation byte-checked 603 members:
`/workspace/chijin-timeline-r005/runs/install-v2/output/venv`.

The real ordinary recurrence collector uses runtime loop K, tail masking and
per-program side effects, with CPU numerical references. It ran seven ordinary
invocations and seven instrumented invocations; a separate eighth profile
request was rejected before allocation/device execution. It:

1. Submitted six invocations interleaved on two actual CUDA streams without a
   collector wait/read between launches. Each retained a distinct allocation.
2. Rejected the seventh while all six owners were still retained and the
   pending budget was full. Its original device counter remained zero.
3. Read the first six in reverse order `[5,4,3,2,1,0]`, preserving invocation,
   binary, stream, actual grid and sampled program association.
4. Released persisted raw owners, then successfully submitted/read case 6,
   proving recovery after admission rejection without replaying earlier work.

All outputs, inputs, tails and original per-program invocation counts passed;
all allocation canaries passed. All seven captures share one actual instrumented
binary despite runtime K/grid changes. Root independently checked 1536 physical
records against raw headers/counters/sequences/sites/phases/full ticks/offsets,
two distinct stream handles, six distinct in-flight buffer pointers, read order,
installed module SHA, native byte bridges and explicit terminal process states.
Host action order plus source establishes absence of collector per-launch
wait/read; it does not prove physical engine overlap or lack of incidental
runtime/compilation serialization.

## Limits and originals

No physical ns/epoch/final marker-boundary proof is added by these lifecycle
checks. No claim that all graph/thread/exception paths passed actual hardware:
CPU fault injection supplements the real two-stream/budget/recovery positive.
The public legacy hook still has its old restrictions. Public integration,
canonical timed events, three-backend P01, genuine async/time arrows, independent
math, Trace Processor/UI and final three code reviews remain incomplete.

[Raw index](raw-artifact-index.json) identifies every retained member. Root
archive `artifacts/timeline/run-005/preflight/owners-original-evidence.tgz`,
142815 bytes, SHA `699cc426883f81e117fc08b67bd1b5bfc16309878f34d9f4c7c91093c08a7b39`.
Raw/decoded/TTGIR originals remain under
`/workspace/chijin-timeline-r005/runs/device-owners-v2/output`.
Root byte-audit script is `artifacts/timeline/run-005/preflight/audit-retained-owners.py`;
it imports no product modules. All six owned jobs are terminal, workers gone;
container PID1 retains controller zombies, which are not live device tasks.

[Package](package-terminal.json), [source bridge](source-bridge.json),
[native bridge](native-byte-bridge.json), [install](install-result.json),
[device terminal](device-terminal.json), [device result](device-result.json),
[root audit](root-audit.json), [process audit](owned-terminal-status.json).
