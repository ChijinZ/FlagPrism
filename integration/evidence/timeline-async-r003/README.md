# Complete cp.async candidate recording and logical group facts — T008

**Partial engineering evidence, not full P01, hardware time-arrow, Perfetto or goal acceptance.** No paper/old Study edits. New device math ran only in existing NVIDIA Docker `chijin-study-pro6000`; GCU/Ascend work this round concerns public tool downloads/connectivity, not their timeline qualification.

## Actual implementation and checks

- Native `ddbe07e` separates the bounded logical-source-region budget from the required traditional cp.async copy/commit/wait boundaries. All relevant candidates are retained, with actual wait `num` metadata; more than 128 required static mechanism sites is a compile failure rather than silent exclusion. Timeline logical selection favors data operations. Legacy non-timeline selection remains unchanged.
- This source was actually built (127 steps, about 168s), installed, and native contract checked normally and with `-O`. The public native plan exposes the planner version and real mechanism inventory. This establishes the compiler-IR candidate set, not final ISA closure for every possible opaque assembly or lowering.
- Product `timeline_nvidia_async.py` uses complete per-observer records and actual commit/wait rules to build identity-bound logical groups and first completion guarantees. Partial waits, multiple submits, empty recorded submit sets, per-observer generations, loss and invocation isolation remain explicit. Incomplete streams yield no guessed groups/edges. Repeated waits use compact coverage ranges rather than quadratic historical edges.
- CPU fixtures passed 29 cases under normal Python and `-O` in server Docker, including a 1000-group linear-size case. Fixtures do not count as real device coverage. Physical buffer slots/iterations are not invented from occurrence numbers. Model facts do not establish physical buffer generations, hardware busy, exact completion time or verified time arrows.
- Python-only commit `1c22840` was packaged on the stable source path. Its exact three changed files were verified; Ninja reported no work, and all seven wheel native members remained byte-identical to the actual `ddbe07e` native build. The integrated wheel was freshly installed and all 600 members byte-checked. This is an explicit native reuse bridge, not a claimed second changed-C++ build.
- The installed model and compiler processed five ordinary plus five automatic-record requests: runtime recurrence K3/7/11 sharing a binary and GEMM stages2/3. Ordinary/profile math, inputs and tail checks passed. State now increments once per logical program; this supports replay checking in the development test, but the full independent replay/lowering qualification remains pending. The collector explicitly synchronizes its own test captures and does not substitute for production deferred owners.

## Independent raw and fact audit

Root decoded the retained device bytes without importing product code on the workstation: **1952 full-width records**, all async fact record references, 30 compiler artifacts and group/wait membership were checked. The five capture/invocation identities are distinct and each fact binary matches its actual compiled capture object.

| Actual capture | Required static async sites | Runtime logical groups | Wait operations | First-guarantee edges | Wait operands |
| --- | --- | --- | --- | --- | --- |
| GEMM stages2 | 10, all selected | 64 | 32 | 64 | 0 |
| GEMM stages3 | 14, all selected | 80 | 32 | 80 | 0, 2 |

The 144 groups and first-guarantee relationships are backed by actual recorded submit/commit/wait streams, not timestamps joined by proximity. Both cases end with observed drain coverage. Submit records are logical attempts and may be predicated empty; these counts are not transferred bytes or engine occupancy. Final compiled-boundary/ISA-coverage validation and clock proof are still required before promoting them into verified temporal arrows. The rule source is [NVIDIA PTX ISA](https://docs.nvidia.com/cuda/parallel-thread-execution/#data-movement-and-conversion-instructions-cp-async-wait-group-cp-async-wait-all).

## Versions and unfinished work

- Packaged source: `1c228404e15845ccfada04e00e51b08009783a95`.
- Native compiler source: `ddbe07e` (full commit in native receipt).
- Integrated wheel SHA: `7128dc09a1feae71cba11466de82c19ba00bbdae00c2111550f7ff78d8c6c2b9`.
- Installed venv: `/workspace/chijin-timeline-r003/runs/package-install-v1/output/venv`.
- Actual device raw/IR/facts: `/workspace/chijin-timeline-r003/runs/device-async-v1/output`.
- Original workstation archive: `artifacts/timeline/run-003/preflight/async-v1-original-evidence.tgz` relative to workspace root; index retains its exact SHA and size.

Public timeline CLI/API, compact collection, production invocation-owned deferred buffers, final marker/source/ISA closure, physical clock/epoch proof and Perfetto export/SQL/UI are unfinished. GCU/Ascend full paths, independent six-new-math qualification and three final additional GPT-6.1-Sol/xhigh code reviews remain mandatory. No backend has completed overall P01.

Perfetto Python SDK 0.58.2 and protobuf 7.36.2 were installed in a separate NVIDIA Docker tools venv by offline public-wheel transfer from existing GCU Docker; import succeeded. Native Trace Processor and offline UI downloads are a separate pending tools task and are not counted as SQL/UI acceptance. The actual current state of those network jobs is in workspace `timeline_impl_record.md`.
