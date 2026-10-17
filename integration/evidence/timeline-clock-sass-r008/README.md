# NVIDIA clock primitive and actual machine objects (T015 / r008)

Status: **development evidence, not P01, certified ns, dynamic-buffer qualification, or Perfetto acceptance**. Product runtime code/native objects did not change in this checkpoint. The added dedicated clock probe runs with the existing r007 independent install; no wheel repack or repeated native build was needed. No paper or Study files changed.

## What actually ran

Existing NVIDIA Docker `chijin-study-pro6000`, GPU0 RTX PRO 6000 (SM120), product Python `/workspace/chijin-timeline-r007/runs/install-v2/output/venv/bin/python`. Installed product/native lineage stays at d15933a / actual changed-source build 545bf8a; source for the new test is [p01_nvidia_clock_scale.py](../../../tests/timeline/p01_nvidia_clock_scale.py), SHA in registration and terminal receipts. It contains no FlagPrism scope/site annotations; the timestamp asm belongs only to this dedicated device-clock primitive, not ordinary-operator qualification.

Two pinned NVIDIA public tools 13.2.86 were downloaded in the existing GCU Docker through a per-call mirror, checked against official PyPI SHA, transported as bytes, and installed offline in a separate NVIDIA Docker tools venv. The initial direct payload timeout is preserved; the successful mirror job was polled to actual terminal, not restarted due to an observation timeout. No system SDK, host driver, daemon or network configuration changed. Sources: [nvdisasm wheel and SHA](https://pypi.org/project/nvidia-cuda-nvdisasm/13.2.86/), [cuobjdump wheel and SHA](https://pypi.org/project/nvidia-cuda-cuobjdump/13.2.86/), [binary utilities documentation](https://docs.nvidia.com/cuda/cuda-binary-utilities/).

Actual `nvdisasm` and `cuobjdump` successfully disassembled two previously retained public-profile cubins. Then actual nvdisasm source/PTX line annotations, JSON and full CFG succeeded on these two and the new calibration cubin. No `--no-dataflow` fallback was used. Tool, cubin, output SHA and actual tool/compiler metadata are retained. The disassembler is 13.2.86; cubin metadata identifies the actual compiler as ptxas-blackwell 12.9.86, not 13.2.86.

## First failure and method correction

The first eager bracket executed one mathematical recurrence at K4096: 10528 internal ticks versus 110944 rounded CUDA Event ns. It failed the preregistered `max(10000ns,2% of event)` consistency gate. The raw integer samples, original stderr/terminal and immutable source archive remain available. This difference includes the host enqueue gap between event recording and kernel submission, so it does not establish a physical timer-rate failure.

The corrected dedicated primitive uses captured external event nodes around the same real math and **nine explicit graph launches** (K4096/16384/65536, three each). Compilation/loading are explicit and execute no math; capture is checked to leave the incrementing state at zero, and state reaches exactly 1..9 after the nine requests. The gate and math tolerance did not widen. The same cubin is used for all runtime K values; CPU oracle, input, output tail and side-effect checks pass. This is a calibration graph, not a claim that the public timeline path supports CUDA graphs.

Internal deltas were about 10.3–10.5, 40.3–40.5 and 160.2–161.0 microseconds under the documented 1 ns candidate. Event-minus-internal differences were 1856–7456 ns, all within the original gate. [PTX globaltimer specification](https://docs.nvidia.com/cuda/parallel-thread-execution/#special-registers-globaltimer-globaltimer-lo-globaltimer-hi) defines the candidate while warning of target-specific behavior; these measurements check consistency on this target, not universal frequency, fine-grained error or epoch guarantees.

## What final objects show, and do not show

| Real object | Static instructions | Actual globaltimer reads | Async copy / commit / wait instructions |
| --- | --- | --- | --- |
| Existing public GEMM | 864 | 44 | 6 / 6 / 2 |
| Existing public recurrence | 496 | 16 | 0 / 0 / 0 |
| Dedicated clock recurrence | 104 | 2 | 0 / 0 / 0 |

These are static counts, not runtime invocation/group counts. Actual calibration code reads at PC0x90, branches on that value, executes the recurrence/reduction, then predicates its final read at PC0x4d0 on the computed sum. The selected public recurrence loop has a timer at PC0xdb0, FFMA at PC0xde0, another timer at PC0xe70 and backedge at PC0xf40. These facts can guide a per-site proof, but do not certify every region/participant or async mechanism closure.

Two details matter for the next implementation step. The calibration runtime-K load is scheduled after the first timer, despite being before it in source; source adjacency is therefore insufficient even for this small case. Also a public prologue globaltimer read at PC0x190 is unconditional, followed by selection of its value at PC0x1c0. Existing IR-level gating/compact storage must not be described as proof that **every** unselected machine-level timer read is eliminated. No unselected logger write or buffer corruption was observed; this finding limits gating/perturbation claims and must be considered in final boundary/cost checks.

The device-event bracket includes prologue/epilogue and event-node work. Its allowance is **not** a certified endpoint error. Neither this probe nor static counts confer ns conversion, shared SM epoch, physical buffer generation, engine busy, or verified time arrows. Raw status remains `partial_clock_unverified`. Next work must produce an applicable clock/uncertainty model and actual region/async boundary/participant proofs, then use them in the common ns/Perfetto path; GCU/Ascend, independent qualification and final three code reviews remain mandatory.

## Originals, audit and reproduction

- Docker: `/workspace/chijin-timeline-r008/runs/{tools-install-v1,clock-scale-v1,clock-scale-v2,object-inspection-v1}`. The successful clock input is `/workspace/chijin-timeline-r008/clock-input-v2/p01_nvidia_clock_scale.py`. For a new owned output/deadline, run that source with the matching product interpreter via `run_primitive_probe.py`; do not reuse the existing result directory.
- Workstation immutable archives: `artifacts/timeline/run-008/preflight/{disassembly-tools-original,tools-installed-evidence,clock-objects-original-evidence}.tgz`; sizes and SHA are in `clock-objects-root-audit.json`. They retain logs, receipts, exact inputs, compiler outputs and actual disassembly. Tool wheels/venv and giant originals are not committed.
- `audit-clock-objects.py` is retained-byte auditing only (stdlib JSON/tar/hash); it never imports product or runs a device/CPU oracle locally. It independently recomputes tick/event comparisons, explicit state counts, source and compiled hashes, tool output hashes and original-r007 cubin bindings. Device math assertions come from the actual executed harness, not this byte audit.
- `final-owned-state.json` checks actual `/proc` identities/groups: all four owned NVIDIA jobs are terminal, no live owned worker group remains. Final GPU state is retained. No other user's task was changed.

`INDEX.json` binds this small evidence set. Prior first failures remain preserved; no P01/qualification/SQL/UI result is filled from these artifacts.
