# Ascend timeline selection and real matrix fragment (R101)

Product freeze `db1e7197d28e76f586b20f1a82c5d7d2946733a2` adds a separate timeline intent. It reserves an aggregate (preferring a contraction) in each actual repeated control region before the existing allocation, within the same maximum-site budget. Counter selection stays byte-for-byte equivalent to the old planner result. A separate policy version enters the serialized compile options before cache lookup. No kernel, source-line, operation-ID or shape allowlist is used.

All execution used existing Docker `chijin_v3.5.x`. The Python-only wheel reuses independently matched compiler/plugin inputs; no SDK or unchanged native rebuild occurred. The normal install finished with return code zero in 67.264490596 seconds; all 446 wheel members matched, and the installed normal/-O selection fixtures passed. Source fixtures cover budgets 1/2/3/8, input-order stability, exclusion of control-condition computations, unchanged counters and compile-configuration identity.

The frozen q05 application then ran once through the normally installed public `--detail timeline` CLI on npu:4. Its four source digests are unchanged. Independent original CPU math, input immutability, output/state guards and the exclusive host-once marker passed. Actual compile metadata contains timeline policy version1 and selects the actual dot. The application returned zero in 60.689159627 seconds. Fresh decoding is complete; raw uses 786816 bytes and the retained bundle 3588409 bytes, within the unchanged limits. This is a functional run, not a performance/overhead experiment.

Read-only LLVM15 inspection of the exact retained original/adapted actor inputs shows that the selected dot fragment on AIC includes the direct `mma_tile_half_to_float` call. Its complete eight-word tuple binds the actual SYS_CNT begin and end. A path from begin through that call to end exists without traversing an original iteration back edge. Fresh raw contains three positive intervals per observed AIC actor (two sampled programs, six intervals total). The corresponding AIV fragment contains cast/vector/control work and has three positive intervals on each of four observed actors. This establishes a real selected computation and real timestamps. It does not yet prove all-path source containment, loop semantics, native issue bounds, exclusive computation cost or engine activity; those qualifications remain false.

The old eight-site plan omitted the dot. The new plan chooses eight actual sites, including it. IDs in the receipts are actual compiler output, not production special cases. Older unselected-dot captures are not reclassified by this change.

Historical inspection failures remain: v1 treated the prefixed instrumentation-mode string as plain JSON; v2/v3 looked for the actor function in the wrong canonical field and reported zero matching events. V4 joins actual source sites with observer function identity and reports the real six/twelve intervals. All are CPU-only reads of the same successful public capture, with no device replay. Earlier source-fixture v1/v2 Torch import-order failures also remain in the selection receipt archive.

Recovered archives, with every indexed member size/SHA256 checked:
- source-selection: 40 files, `c11c395ad53a4828e5cc88a9fd8641f1d8000c929921c322e0cacdc31bb85e1a`;
- matching normal install/public/inspection: 216 files, `5bded893677bf0e629a868fcf51baafe31bff073cdf33470c7bf70d59a6acbab`.

Full raw, actor LLVM, private graphs and binaries remain in root/server artifacts. This folder contains small identity/terminal/result records. Final whole-goal review and outstanding Ascend automatic region/loop integration plus GCU native composition are not certified by this milestone.
