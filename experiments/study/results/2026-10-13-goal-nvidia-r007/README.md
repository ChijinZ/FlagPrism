# PRO 6000 NVIDIA starting-point search

Run inside `chijin-study-pro6000` on `zhangquan_pro6000`, using the persistent
`/storage/Ext_01/chijin-study-pro6000/workspace` mount. No experiments ran locally.
Environment: Torch2.8.0+cu128, FlagTree package0.7.0 / Triton3.6.0 from the saved
PR1262 source, FlagPrism from this study branch. Container source-build missing
external include was fixed with `third_party/FlagPrism` symlink. Setup scripts,
failed attempts and image/device identity are in
`artifacts/study-goal-run/commands/pro6000/` and `environment/` outside Git.

20 operator-shapes: the original18 plus GEMM/fused512x512x4096. All use the
canonical input bytes produced in the GCU Docker. Search:108 GEMM configs,
20 row configs (warps1/2/4/8),36 transpose configs. Total1152 configurations,
1112 passed,40 shared-memory resource failures retained. BK512 exclusions are
resource estimates for the finite budget, not claims of compiler impossibility.

`selection.json` is the authoritative frozen native winner. Per-case
`result.json` has two different fields: `selection` is the graph-search winner;
`native_selection` is the final native winner. A graph timing search ranks
candidates; its top3 distinct binaries each receive3 independent captures of
30 uninstrumented kernel launches through FlagPrism/CUPTI. Final selection is
minimum median of batch medians across those candidates. This is a finite
source search, not a vendor-optimal implementation or architecture peak.

The historical sweep's `DONE` log accidentally printed the graph winner;
use JSON `native_selection`, never that log line, to construct target P.
The runner now prints `DONE_NATIVE` with the correct field.

180 native captures /5400 positive kernel intervals are included. Correctness
and post-profile checks passed for all captures. `selected-asm-native` belongs
to the final winner; `selected-asm` in the raw archive belongs to graph winner.
These are tuning observations. Final breadth plots require fresh matched
sampling of frozen N and target P, not the chosen fastest search sample.

This compact bundle retains JSON traces, correctness, source/compiler hashes,
all trial statuses, native candidates, selected native assembly and manifest.
The complete logs/all assembly are in
`artifacts/study-goal-run/pro6000-n-search.tgz`; its SHA is in `manifest.json`.
Absolute `/workspace` paths in records refer to the remote persistent mount.
