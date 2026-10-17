# Causal clock constraints and real tool provisioning (T018 / r011)

Status: **shared causal-bound arithmetic and dedicated real-math calibration passed; not a clock/source-region/Perfetto/P01 certificate.** Only tool engineering, tests and tool documentation changed. No paper or Study edits.

## Implemented common arithmetic

`timeline_clock.bound_causal_offset` intersects four-read constraints for A publish, B receive, B respond and A receive. With commensurate fixed units/origins and proven causal ordering:

```text
max(B_respond - A_receive) <= offset(B-A) <= min(B_receive - A_publish)
```

Explicit endpoint uncertainty conservatively enlarges those inequalities. Integer arithmetic preserves large absolute values; malformed, oversized, locally reversed or inconsistent observations fail in normal and optimized Python. The function does not assume symmetric communication, fit clock rate, discard contradictory samples, infer domains/epochs or grant qualification. Caller-provided raw ticks remain raw ticks. Scale, endpoint uncertainty, ordering, reset/wrap and applicable coordinate scope need separate physical evidence.

## Actual dedicated device experiment

The [probe](../../../tests/timeline/p01_nvidia_clock_handshake.py) performs real two-CTA producer/consumer math: 64 rounds of `v = .75*v + .125`, published vector data, and consumer `y = .5*v + .25`. Timestamp values themselves are release-publication payloads; acquire observations and success control precede receiving reads. Every poll is bounded. Its synchronization is part of a **dedicated calibration**, never injected into user kernels, and is not an ordinary profiler/async-case qualification.

Existing NVIDIA Docker `chijin-study-pro6000`, GPU0 RTX PRO 6000 SM120. The target reports 1536 maximum threads/SM; actual PTX requires 1024 threads/CTA. The two observed CUDA SMID values are 0 and 1. Actual SASS uses `SR_VIRTUALSMID`; these are target/context SMID observations, not global physical silicon IDs. Scope is the observed pair and acquisition window, not all 188 SMs or arbitrary future captures.

| Check | Actual result |
| --- | --- |
| New causal-bound CPU contracts, normal / `-O` | 9 methods each |
| Existing clock arithmetic, normal / `-O` | 27 checks each; explicitly not physical clock proof |
| Fresh installation | all 607 compiler/component members checked against wheel; seven native libraries byte-identical to predecessor |
| Real final math | 3 explicitly requested kernels × 64 exchanges; input/tail, CPU oracle `rtol=atol=2e-6`, state `[64,64]` → `[128,128]` → `[192,192]` passed |
| Training / held-out | first 32 and last 32 exchanges per trial; each subset independently admits zero offset |
| Actual units | raw ticks; no automatic ns conversion or clock certificate |
| Final object | 280 static instructions, 4 actual full-width globaltimer getters; text/JSON and complete CFG retained |
| Caller integration | actual GPU `.text.exchange` byte-identical before/after adding the common CPU-algebra call |

The measured offset intervals contain zero and are about 896 ticks wide in the final acquisition. Observed delta GCD is 32 ticks; this is **not** a proven quantization/read-error upper bound. A midpoint would be a coordinate choice, not a claimed true offset. The final-machine reads and direct timestamp-to-release-atomic data dependencies were byte-audited. Consumer success-control, applicable epoch, absolute endpoint error and broader scope still need integration/qualification.

## Failures and source/install identity

- First ordinary calibration baseline rejected Triton `break` syntax before any calibration math ran. A bounded while/failure state preserves the algorithm, tolerance and denominator; original failure is retained.
- First object-inspection wrapper used unsupported `--cfg`. Text/JSON outputs and the failure remain. The corrected invocation uses actual supported `--output-control-flow-graph --print-instr-offsets-cfg`; no `--no-dataflow` fallback.
- Product/source freeze: `880706b2cee327e71100b8fb99222666523d121d`. Independent install: `/workspace/chijin-timeline-r011/runs/install-v1/output/venv`. Wheel 390952314 bytes, SHA `70a799263734b2e4fbe79c037366a4c8576f9e9c8d7d83175ff79618671713aa`. No changed C++ was represented as a new native build; the Python-only bridge checks actual native bytes.
- This checkpoint does not change raw event ABI, add a public clock-qualified mode, or certify the previous ordinary captures. Existing raw timeline remains explicitly unverified. No unchanged 26-capture matrix was rerun merely for bookkeeping.

## Trace Processor environment obstacle resolved

The previous direct download routes failed. The official virtual-host GCS endpoint successfully supplied the **same pre-pinned** v57.2 `trace_processor_shell`: 14008280 bytes, SHA `55ba613fc6d4f71df81eee2dbfc293020063655c241b3e314bff75345b802684`. Source:

[Official pinned tool bytes](https://perfetto-luci-artifacts.storage.googleapis.com/v57.2/linux-amd64/trace_processor_shell).

Download occurred in existing Enflame Docker `flagprism-enflame-dev`. Retained bytes were transferred, rehashed and tested in NVIDIA Docker. Version/help really execute: `v57.2-da1d152cf`, RPC API 14. NVIDIA executable path: `/workspace/chijin-timeline-r011/tools-input/trace_processor_shell`. Python SDK 0.58.2 remains in the previously isolated tools prefix. No host network/driver/daemon or global SDK changes.

This is tool provisioning, **not real profile SQL/import/UI acceptance**. The fixed official UI asset was located via GitHub REST; its download progress/failures are in the live engineering record. GCU currently has no browser executable. Those steps must be completed with actual profile traces later.

## Originals and reproducible audit

- NVIDIA originals: `/workspace/chijin-timeline-r011/` retains package bridge, install, all baseline/calibration/inspection failures and final outputs.
- Final archive: `artifacts/timeline/run-011/preflight/causal-final-with-tools-original-evidence.tgz`, 138922 bytes, SHA `8f209f27953bdd1e202b5aca6b965550f01cb6b1f8c4781eaab7025743a23920`. Earlier acquisition archives remain immutable.
- Official tool payload and GCU provisioning receipts: `artifacts/timeline/run-011/preflight/perfetto-tp-tools-original.tgz`; executable SHA above. Large public binaries are excluded from Git.
- [Retained-byte audit](retained-byte-audit.json) independently checks installed module bytes, source/artifacts, requests/state, causal/training/held-out inequalities, real ELF/code/GT/debug-line bindings, release payloads and terminal job identities. It imports no product and runs no workstation numerical oracle.

```bash
python FlagPrism-method/integration/evidence/timeline-clock-causal-r011/audit-retained-bytes.py \
  --archive artifacts/timeline/run-011/preflight/causal-final-with-tools-original-evidence.tgz \
  --repo FlagPrism-method --output /tmp/flagprism-causal-audit.json
```

`INDEX.json` binds these small public members. Later source changes may require the recorded source freeze to reproduce exact-source checks. This design/primitive work does not replace ordinary operator, all-backend, independent new math, source-boundary, physical buffer-generation, real Trace Processor/UI or the final three extra requested code-review gates.
