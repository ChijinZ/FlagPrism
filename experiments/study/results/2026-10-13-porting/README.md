# Three-backend Study evidence

All execution, builds, reference math, tuning and GPU collection ran in remote Docker. Local scripts only parse saved observations and draw figures. The manuscript is maintained in the workspace `paper/sections/03-study.tex`.

## Results and interpretation

- Overview: 6 operators × 3 shapes × 2 frozen NVIDIA configurations × 3 measurement batches × 30 native calls × 3 backends = 9,720 intervals. Each backend has 108 successful captures. NVIDIA N is a bounded search, not vendor-best tuning.
- Case A: Softmax127×769, row grouping1; four→one GCU work-items gives1.6178× target-local speedup. NVIDIA favors four in the frozen set. Compiler ownership and native counters diagnose cooperative mapping; the two-item control shows barrier presence alone does not explain the slowdown; worker-dependent synchronization cost remains unseparated.
- Case B: Fused GEMM512×512×4096: transferred32³→BK256→BM/BN64 gives310.27→164.12→58.45µs,5.3083×. P/R_K saved AIV LLVM is byte-identical. PMU activity reports overlap and come from separate replays; do not stack them into wall time.
- Matrix sanity: the large GCU overview gap is independently confirmed by device-stream timing and software-path evidence. The16×32 control has positive2D activity, so no universal32×32 threshold is claimed. NVIDIA's extra w2 control beats the bounded w4 selection slightly; N is not a global optimum.

## Data directories (relative to experiments/study)

| Data | Directory |
|---|---|
| NVIDIA selection, full search log and native shortlist | results/2026-10-13-goal-nvidia-r007 |
| Independent NVIDIA overview and case controls | results/2026-10-13-goal-nvidia-r008 |
| Additional NVIDIA GEMM warp control | results/2026-10-13-goal-nvidia-r009 |
| Independent Ascend overview | results/2026-10-13-goal-cann-r009 |
| Independent GCU overview | results/2026-10-13-porting/enflame-overview |
| GCU Softmax mapping, native, TCU, brackets | results/2026-10-13-porting/enflame-tail |
| GCU matrix software-path sanity controls | results/2026-10-13-porting/enflame-matrix-sanity |
| Ascend native, PMU, lowering, sparse traces | results/2026-10-13-porting/ascend-diagnosis |

Raw archives, remote command receipts, environment manifests and unchanged canonical inputs are preserved under workspace `artifacts/study-goal-run/`. SDK private libraries and generated binary caches are excluded from this compact evidence directory. No credentials are needed for offline plotting.

## Offline figure reproduction

From workspace root, with Python3, matplotlib and NumPy installed:

```bash
python3 FlagPrism/experiments/study/plot_porting_overview.py --cuda FlagPrism/experiments/study/results/2026-10-13-goal-nvidia-r008/overview-independent-r008 --enflame FlagPrism/experiments/study/results/2026-10-13-porting/enflame-overview --cann FlagPrism/experiments/study/results/2026-10-13-goal-cann-r009 --output paper/figures
python3 FlagPrism/experiments/study/plot_cooperative_case.py --gcu FlagPrism/experiments/study/results/2026-10-13-porting/enflame-tail --cuda FlagPrism/experiments/study/results/2026-10-13-goal-nvidia-r008/case-controls-independent-r008 --output paper/figures
python3 FlagPrism/experiments/study/plot_actor_case.py --ascend FlagPrism/experiments/study/results/2026-10-13-porting/ascend-diagnosis --cuda FlagPrism/experiments/study/results/2026-10-13-goal-nvidia-r008/case-controls-independent-r008 --output paper/figures
make -C paper
```

Each plotting script emits vector PDF/SVG, PNG, and data/provenance. The overview parser rejects mismatched inputs, source/config identities, numerical failure or incomplete native-call counts. Native duration scopes differ by SDK and are not hardware-peak or exclusive-clock comparisons. Clocks and device exclusivity were not locked.

The unchanged Ascend raw holdout contains a stale generic exploratory scope field. [holdout-provenance.json](ascend-diagnosis/holdout-provenance.json) audits its configuration/input/source identity against frozen N; it does not reconstruct an exact freeze wall-clock timestamp.
