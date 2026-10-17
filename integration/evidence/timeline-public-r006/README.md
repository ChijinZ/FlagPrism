# Public timeline raw collection checkpoint (T012)

The real public `start(..., detail="timeline")` API and
`python -m flagtree.profiler.cli --detail timeline --device 0 -n trace-run my_script.py`
now collect internal raw timestamps on NVIDIA through the actual profiler hook.
This is **explicitly `partial_clock_unverified`, not a certified ns axis,
Perfetto delivery, complete P01 or final qualification**.

## Implementation and installation

Initial public collection commit `67322072bb495164b7397fc283920adf4492ee93`
passed real API cold/warm sessions and CLI (12 nonempty captures). Follow-up
`3ebf1a276aeb8c58e93446bee0b359507abf2511` closes the native session even when
internal export fails, handles zero-grid without an owner, and adds fault/
recovery/zero-grid and legacy count regression tests. Both originals remain
separately indexed. No failing data or tolerance was discarded.

Timeline uses independent per-invocation owners and stream-local completion,
not the old shared buffer/SM-clock parser. Launch identity comes from the same
LaunchHook metadata object and actual binary/function/grid/stream. Finalization
persists raw bytes, decoded records, logical async facts, source snapshots and
actual compiled artifacts before releasing owners. Clock and arrow status stay
unverified. Eager, multiple streams and one creating host thread are supported;
nested timeline sessions are explicitly rejected.

The launcher now exposes preallocation admission ABI 2 and supplies the actual
stream before either scratch allocation. Its old patch was reversed and v2 was
first applied in an isolated single-file trial, then applied to the owned parent
source after exact byte checks. [Launcher delta](launcher-delta.json) identifies
the changes. The actual libtriton/launcher/hook/runtime hashes enter timeline JIT
identity before cache lookup; epoch qualification remains a separate runtime gate.

Both packages changed Python only, with Ninja no work and all seven native
wheel members byte-identical through the prior actual `545bf8a` native build.
Final wheel: 390635688 bytes, SHA
`0600be7e891b177083393a77f1d63c7ed982b6d36ef06716a5e18f09cf146952`.
Fresh installed venv:
`/workspace/chijin-timeline-r006/runs/install-v2/output/venv`.
Only the existing RTX PRO 6000 GPU0 Docker `chijin-study-pro6000` was used.

## What the real public test proved

The target is ordinary unannotated Triton: three runtime-loop recurrence calls
interleaved on two streams and one masked GEMM, with original numerical/input/
tail/side-effect checks. The test covers:

- Public API cold and warm sessions using the same JIT objects; root verifies
  that the actual loaded function handles and binary IDs were reused.
- Each timeline workload also requests a zero-grid call; it changes no original
  counter and produces no raw capture or synthetic event.
- A deliberately injected export failure still finalizes the native session,
  drops hooks and retains owners. Raw recovery saves the same four original
  calls without rerunning the workload. A subsequent public session succeeds.
- The actual CLI, including its compile/export supervisor and standard bundle,
  processes the same ordinary script once.
- The old `--detail auto` path processes the nonzero workload separately and
  retains four count captures and observations, without becoming timeline mode.

In the final run: **20 nonempty timestamp captures, 6720 physical records,
400 logical commit groups**, plus four separate legacy count captures. Per
workload host-once markers, numerical results, original side-effect counts and
zero-grid checks passed. Root independently validates raw SHA/header/slot/
program/cursor/site/phase/sequence/full-tick/offset, invocation and same-metadata
launch/binary linkage, actual compiled artifact hashes, standard bundle file
hashes, and cold/warm function reuse. Logical groups are not verified time arrows
or physical buffer generation evidence.

CPU contracts in the fresh installation: 16 owner methods and seven storage
methods each normal/`-O`; two public rejection/finalization methods each normal/
`-O`; three existing automatic-hook methods; actual CLI help. Fake/mocked
contracts supplement the real device test, and do not count as device evidence.
No NVIDIA performance/overhead or hardware-overlap certification was attempted.

## Artifacts and remaining work

Examples in the server Docker:

- API bundle: `/workspace/chijin-timeline-r006/runs/device-public-v2/output/api-cold/timeline/index.json`.
- CLI bundle: `/workspace/chijin-timeline-r006/runs/device-public-v2/output/cli/timeline/index.json`.
- Recovered original raw: `/workspace/chijin-timeline-r006/runs/device-public-v2/output/recovered-raw.timeline/index.json`.

Read [runtime/public usage](../../../Profiler/docs/timeline_runtime.md).
Physical clock scale/epoch and final machine boundary/order certification,
canonical time events/Perfetto SQL and UI, GCU/Ascend timeline paths, independent
new math and three final specified code reviews remain required. No backend has
completed P01. The old design's proposed command is now a real raw-stage entry,
not proof that all its intended time semantics have been implemented.

Root original archive: `artifacts/timeline/run-006/preflight/public-original-evidence.tgz`,
3016461 bytes, SHA `d3e6cc4b55116d1496b4a586e6ffd58de8b1728ae884a74c18329fc1030f5448`.
[Raw index](raw-artifact-index.json) covers all original members, including the
expected failure, native recovery intermediates and both source versions. Root
byte-only audit: `artifacts/timeline/run-006/preflight/audit-public-raw.py`.
All six owned jobs are terminal; worker processes are gone, controllers remain
only as PID1 zombies. No paper/old Study or other-user processes were changed.

[Package](package-terminal.json), [source](source-bridge.json),
[native bridge](native-byte-bridge.json), [install](install-result.json),
[device](device-terminal.json), [result](device-result.json),
[expected failure](expected-export-failure.txt), [root audit](root-audit.json),
[process audit](owned-terminal-status.json).
