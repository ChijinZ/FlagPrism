# Ascend SDK capability investigation (r028)

This is a compiler/tool investigation, **not** a new timeline acceptance or
counter-unit certificate. The initial capability probe did not change product source. The subsequent
source retention change below does not alter installed wheels, native code,
device math or historical captures. No paper/Study files changed.

The existing `chijin_v3.5.x` Docker and retained r020 compiler inputs are usable.
The installed c220 GetSystemCycle implementation uses SYS_CNT; its header SHA is
`0a889a0604d0383b38045c8c0ee38361ab6ce42277507f4ecb0d0e53d524b948`.
This identifies a getter implementation, not the final instructions or epoch.

## New actual observations

- The SDK's `msobjdump` extracts/displays ELF metadata; it does not disassemble
  the target's instructions. It cannot replace a clock instruction check.
- On the actual adapted LLVM and original SDK link inputs, `bisheng -###`
  returns zero **while reporting unsupported option** and emits no frontend
  command. Exit status alone is insufficient here.
- Direct `-print-after-all` is unknown. `-mllvm -print-after-isel` is rejected by
  the SDK's print-after filter. `-via-file-asm` is rejected as device-side `-S`.
  These are different invocation paths, not successful assembly exports.
- The second harness failed while constructing its final summary (`front` was
  removed). All three stdout/stderr files precede that NameError and are kept.
  Their individual exit codes were not durably retained; no values are inferred
  or claimed. The controller's actual return code is 1. No compiler rerun was
  performed to conceal the harness failure.

The earlier r020 evidence already retains the unavailable objdump decoder,
rejected device `-S` and print-after, and successful save-temps that produced no
assembly. Those unchanged commands were not repeated here.

## Evidence and next action

`verification.json` records the immutable archive hash, every member hash,
controller/worker identities, terminal receipts and observed inactive states.
The workspace archive is
`artifacts/timeline/run-028/preflight/ascend-capability-evidence-v1.tgz`.
Workstation auditing used stdlib byte reads only; SDK invocations ran in Docker.

Ascend remains raw-only: this investigation does **not** grant CounterUnitProof,
source durations, shared epoch, async flows or full P01. The source change below closes the actor-object input gap for future
compilations. Its installation and fresh public capture still need validation
before continuing the time/export vertical slice. Current SDK instruction export remains
an explicit unresolved mechanism, not a reason to declare the whole goal done.

## Source retention implementation and bounded tests

`ascend_compiler.finish` now seals available actor object bytes into new timeline
handoffs using the existing exact portable-file mechanism. It bounds each read
at 32 MiB, checks receipt hash/length, and marks absent objects explicitly. Older
captures remain valid; no new native/record ABI or clock qualification is granted.
The existing compiler cache fingerprint includes this Python implementation.

Inside Ascend Docker, the current source namespace passes 28 tests normally and
28 with Python `-O`, including exact bytes surviving scratch removal, changed
objects, missing objects and over-budget input. The existing driver-receipt
regressions run in the same matrix. The real retained dav-c220-vec actor object
also round-trips through the bounded implementation: 21,432 bytes,
SHA `72a4b0fc58229c48354d2418bacb1f1dfdcb63766a6040a247c585978dbe1abc`.
This last check consumes an existing real object; it is not a new SDK compile.

The GCU container runs only the cached full pre-commit formatter/checker, with
AST equivalence and a second fixed-point pass. No GCU device work was launched.
`retention-verification.json` binds current source bytes, actual receipts and
inactive owners to the final evidence archive. This milestone is **source tested**;
new wheel/default device collection, clock and three-backend acceptance remain
pending. No unchanged native sources, device math, TP/UI were rerun.
