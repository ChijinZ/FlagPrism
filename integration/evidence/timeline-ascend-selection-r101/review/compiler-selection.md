# R101 limited compiler review: timeline selection and cache intent

Reviewed freeze: `db1e7197d28e76f586b20f1a82c5d7d2946733a2`.
Requested reviewer configuration: GPT-6.1-Sol / xhigh; actual resolved model and effort are not exposed and are **unknown**. This is the continuing independent compiler reviewer, not a new whole-goal qualification.

## Conclusion

No confirmed blocker, major, or minor defect in this delta. The source implements the R100 minimal intervention: Ascend timeline selection reserves an eligible aggregate in an actual repeated control region before the existing allocation, while preserving the logical site budget and default counter behavior. An independent timeline policy version affects compile-option identity. Matching source-loaded CPU evidence supports this limited conclusion. Normal installed execution and the selected dot's actual lowered bracket remain pending in the materials reviewed here.

## Source findings

- `Debugger/python/flagtree_debugger/automatic_plan.py:125`: the new branch uses compiler control ancestry and `repeated`, retains the existing direct-region preference, excludes control-condition computations through `_is_data_candidate`, and prefers dot over other aggregates. It does not identify a kernel, source line, or fixed operation ID. Every reservation uses the existing `select` function, which deduplicates and enforces `max_sites`. The old census, scalar-context, region, and class allocation follows with the remaining capacity. With `timeline=False`, neither this branch nor the extra result field executes.
- `Debugger/python/flagtree_debugger/compiler.py:331`: the Ascend branch passes `timeline=timeline` after the existing inlining and assignment of actual TTIR operation metadata. It retains `census=True` for the existing remainder policy. Counter requests pass false and retain their old result.
- `Debugger/python/flagtree_debugger/compiler.py:62`: `debug_timeline_selection_policy_version` is inserted for an automatic `runtime_first_last` request in the publication compile configuration. `apply_compile_options` serializes that configuration into `options["instrumentation_mode"]` at lines 120–125; component registration exposes that option hook. This uses the existing pre-lookup option/specialization chain, rather than only changing the emitted plan or manifest. The retained source integration also treats `NPUOptions.instrumentation_mode` as the frozen hashed request. The delta does not change that underlying hook. The CPU fixture checks configuration identity, not an actual new installed JIT cache hit/miss.
- `Profiler/docs/timeline_runtime.md:184`: the added paragraph correctly separates source selection from a complete lowered computation lying between readers. The established maximum-site paragraph supplies the budget qualification. No change to clock, observer ABI, SDK lowering, or synchronization appears in the four-file commit.

## Matching evidence actually read

Read `run-101/preflight/selection-receipts-v1`, including the runner, fixture, original baseline, all terminal records, v3 identity/steps/results and normal/optimized logs. Independently checked all **40** indexed file sizes and SHA256 values: no mismatch. Candidate bytes equal the executed v3 inputs:

| File | SHA256 |
| --- | --- |
| `automatic_plan.py` | `a2c8785729ae3c7f6e94963ae1f11a08db3d5f6f1909125cbca40fcf26b71c21` |
| `compiler.py` | `f2d727cf671941090d5daa7d5ac24a792d66fe5918d3a2abc9a737de0c8c6b52` |
| `p01_ascend_timeline_selection.py` / executed `cases.py` | `39e72b91d25cb195202ed4d6762a394eb821187cbe3dc73d9218bfd60bdca42e` |

The executed baseline is byte-identical to the planner in the commit's parent, SHA256 `95a937b58b518054d166f920c23b72340c8b72237e05cfba2c6a7f8ca30047c2`.

`selection-v3` is terminal **0 / 17.093501678 s**. Both normal and `-O` child steps returned zero; the fixture uses explicit `need` checks, so optimization does not remove the assertions. It covers budgets 1/2/3/8, reversed input order, control-condition exclusion, exact full-dictionary counter equality, and a policy-version change producing a different compile configuration. The retained q05 tracked table has capture SHA256 `1f1474d9b5f9e1874651d13ef937c8f4d1788eadf31271a0ee07a790893b6aec`:

- Old selected IDs: `[33, 42, 1, 6, 73, 50, 2, 78]`.
- New selected IDs: `[43, 33, 42, 1, 6, 78, 46, 77]`; ID 43 is `tt.dot`.
- Both modes explicitly report `counter_plan_unchanged=true`, `public_install_verified=false`, and `device_executed=false`.

v1 and v2 remain terminal **1**: their logs show Torch/NPU backend import initialization and circular import failures respectively. v3 fixes fixture initialization/environment; those failures are not rewritten as successes. The successful child logs retain `can not use command: npu-smi info`; they contain no traceback and the runner records both zero return codes. This receipt is CPU source validation, not a device capability claim.

## Necessary verification gaps

1. **Matching normal installation / public option path.** A normal package containing these source bytes and a public Ascend compile must confirm that the frozen `instrumentation_mode` includes policy version 1 before lookup and that the resulting compiler plan contains the newly selected dot. Reuse the existing identity chain; a new cache framework or broad matrix is unnecessary.
2. **Actual q05 computation coverage.** Selection closes the frontend omission only. The targeted new q05 result must bind the selected dot carrier to the real original/adapted actor and establish whether the actual MMA call is in its observer fragment. If lowering still puts MMA outside the fragment, retain that fact and address that separate boundary problem. Existing unselected-dot captures do not acquire coverage from this change. This review does not certify native issue boundaries, ordinary pipeline preservation, or whole-goal completion.

## Optional

No additional optional work is necessary for this selection delta. The current fixture checks configuration change rather than an installed JIT specialization transition; the pending public/normal-install evidence should state that distinction explicitly.

## Reading and execution boundary

Read the four changed files, relevant unchanged option-hook and Ascend request/integration code, and the primary CPU receipts above. Reused the reviewer's own R100 scope; read no peer report. Performed only Git/text/JSON/byte-identity inspection and wrote this report. Did not import project code, run product tools/tests, compile, access a server/device, replay mathematics, or run SDK/TP/UI. No implementation or other report was modified.

## Matching installation and public-capture addendum

The candidate remains `db1e7197d28e76f586b20f1a82c5d7d2946733a2`. Read the primary `run-101/preflight/delivery-receipts-v2` installation/public/diagnostic runners, configuration, terminal records, installation assembly/reuse evidence, public mathematical and host-once results, expanded capture, fresh decoded batch, and original/adapted actor indices. Independently checked all **216** indexed file sizes and SHA256 values; no mismatch. No product or test execution was performed for this addendum.

**The matching normal-install and public option-path gap is closed.** `install-v1` is terminal **0 / 67.264490596 s**, with 446 installed wheel members checked against wheel bytes and both installed normal/`-O` selection checks returning zero. Wheel SHA256 is `a15f5cd40b26cd46ea6cc1e5b98ff4711db248d85bb416878a21db3f00a1942c`. Assembly records the same reviewed planner `a2c87857…26b71c21` and compiler `f2d727cf…c6b52` source hashes. This is a normal wheel assembly/install of Python changes with checked unchanged native/compiler/plugin inputs; it does **not** claim a new native rebuild. The installed fixture's generic `public_install_verified=false` field is unchanged fixture wording; installation and public execution have separate actual receipts.

`public-q05-v1` is terminal **0 / 69.405376358 s**. Its single public CLI invokes the new installation with a fresh compile cache, default eight-site timeline mode, q05 shape/config 0 and runtime K=3. The actual capture's frozen `instrumentation_mode` contains `debug_timeline_selection_policy_version=1`, and the actual automatic plan selects `[43, 33, 42, 1, 6, 78, 46, 77]`. Thus the new intent/version is observed in a real compiled public request, not merely in a hypothetical configuration dictionary. Together with the already reviewed version-change fixture and unchanged pre-lookup hook, this closes the finite cache-intent connection; it is not a separate hot-cache transition experiment.

The four actual application source SHA values match the frozen public configuration. The original mathematical result reports 4096 elements with zero maximum absolute error, guards/input immutability/unique logical State checks true, and requested launches 1; the sole host-once marker matches the mathematical process PID 689120. Fresh decode is complete, the raw allocation is **786,816 B**, and the bundle is **3,588,409 B**, with the original readback guard and budget checks passing. Raw SHA256 is `b195a2d7ddb727b3ef3051d101807787493a9c3c06b1382bdf58d804d5414dd7`. This is the one new public profiled invocation, not a repeated ordinary/profile matrix.

**The targeted frontend omission and empty-MMA-fragment concern is resolved for this actual new q05 object, with a deliberately limited diagnostic conclusion.** `dot-inspect-v4` is terminal **0 / 9.134969193 s** and reads the same retained public capture without another application/device run or SDK compilation. Its LLVM15 tool is the previously reviewed `d0e82b1f…a99d61`. The retained original/adapted text hashes match their handoff fields and the indexed input hashes:

| Actor | Original LLVM SHA256 | Adapted LLVM SHA256 |
| --- | --- | --- |
| AIC | `73dcaca086ec4094f4f73a0b20cf9199550d2920859b869787ffad47724c1406` | `a19d22280bc179fb4b34bb300e721e9bdd27bccc32bba9fe5d677122a0764be4` |
| AIV | `dd913eca39ce08470ad4b3bc991bf9c87454bb016455e1b37003354045db7982` | `d502dad16bd894b893c10d91a400270e07fca81680b26bb7920eb78bc2d444f3` |

In the original AIC typed graph, carrier 197 for selected source op 43 is followed in block 85 by body instructions 199 and **200 = `mma_tile_half_to_float`**, before the next carrier. The adapted tuple binds site 21 to begin reader 2124 and end reader 2141; actual MMA call 2130 is in block 2098 between the relevant reader blocks. The diagnostic explicitly cuts natural-loop backedges and records both begin→call and call→end reachability. That establishes an included actual LLVM MMA member and a within-iteration reachable route; it is **not** an all-path, final-native, or exclusive-cost certificate. The raw-derived batch has two AIC observers with three positive dot-linked intervals each (six total), and four AIV observers with three positive dot-linked intervals each (12 total). The AIV source-linked fragment contains its actual cast/vector computation and flag operations; it is not mislabeled as an AIC MMA call.

The v4 event join uses canonical site source-op identity and the observer's `ascend.function`, rather than assuming a backend-specific function attribute on a canonical site. v1 remains terminal 1 because it parsed the prefixed `instrumentation_mode` as a complete JSON document. v2/v3 remain terminal 0 diagnostics with zero reported events due to incorrect metadata joins; they are superseded for occurrence counts, not treated as successful zero-event evidence or product failures. v4 requires actual intervals and reads the same public raw data.

No new confirmed defect was found. Both original R101 gaps are closed at their stated **selection/installation and actual LLVM-fragment diagnostic** scope. All emitted `source_boundary_qualified` and `native_schedule_qualified` fields remain false; the tuple diagnostic also preserves its selection/body/actor/loop verification flags as false. Reachability and positive durations do not upgrade those fields. Existing historical unselected-dot captures, broader source/native/loop qualification, pipeline preservation, and whole-goal completion are not changed by this addendum.
