# Final-origin candidate: Softmax cooperative reduction mapping

## Identity and origin

Workload FP32 Softmax127×769, paddedBLOCK1024, one source row/program, same canonical input bytes, grid127. Authoritative NVIDIA selection snapshot `softmax-N-frozen.json` verified equal to final native-selected manifest. NVIDIA N chooses ROWS1,num_warps4,num_stages1: native search-validation median1.152us; candidatesw1=1.248us,w2=1.216us. This is a fixed-budget optimized origin, not universaloptimal. Genericport changes no source/configuration for P; configguided R changes only targetnum_warps4→1.

All execution/compilation/CPU checks/profiling in reused `flagprism-enflame-dev`, persistent `/workspace/study-goal-enflame-tail-r008`, bound `/root/chijin_workspace/study-goal-enflame-tail-r008`. Canonicalbytes from `/workspace/chijin-study-canonical-inputs-r007`, SHA retained in every native result and source_N entry. Device0, exactTOPSPTI kind=kernel,name=rows. No research source instrumentation in performance samples.

## Hypothesis before intervention

`hypothesis-before.json` saved before native P/R/control measurements. Four work-items cooperatively split the row into256-column local slices. Width769 leaves useful slice counts256/256/256/1; arithmetic uses sentinelpadding to1024. One work-item owns a full paddedrow, avoids shared partialexchange and coordination. Predict native duration decrease and collective/topology change; alternatives taskcount change ruledout by constantgrid127, purebarrier attribution explicitly tested with w2.

## Native recovery, independent process batches

| Batch | P4items us | R1item us | alternative2items us |
|---|---:|---:|---:|
|0|114.8685|71.145|73.553|
|1|115.064|71.1245|73.653|
|2|115.209|71.055|73.777|

Each value median30nativecalls; three random-order batches/version, all270 mathematical checks/outputs passed PyTorch CPUFP32 toleranceatol.0005,rtol.002. P/R medianofbatchmedians=1.617784 speedup,38.186% latency reduction. Keep raw distributions `uninstrumented-native.csv`, sourceevents IDs/binary IDs explicit. No target hardware change, no disabled usefuloptimization in P.

Actual runtime launch block_x4→1, grid127 unchanged. Compiled partial sizes1×256→1×1024; shared partial1×4 removed; staticbarriers2→0; localbytes/item3072→12288; sharedbytes1024→0. `w2` alloc1×512, shared1×2, two barriers, local6144/shared1024bytes; nearlysameperformance as R despite barriers. Therefore explain cooperative partition/resource mapping jointly; do NOT say barriers alone explain38%. Scheduling/concurrency breakdown not separately identified.

## Original-binary fine backend observations

TCU application replay, exactkernel rows,21invocations/config include first6initial/warmups;24 SIPinstances eachrecord. All replayCPUreference checks passed. Officialmetric definitions from installedSDK (matching earlier query) retained in experiment report.

| SDK metric median | P4 | R1 | alt2 |
|---|---:|---:|---:|
|1D instruction cycle share %|.840995|2.99055|1.32603|
|MSF instruction cycle share %|.258768|1.27597|.505155|
|SIP busy includingwaitstall, avgcycles|6192.08|5028|6353.5|

TCU efficiency denominator is SDK totalcycles, NOT occupancy, activewarp%, or exactenginebusyfraction. Familypercentages need notsum100. BUSY includeswaitstall; alt2busy>P yet taskmuchfaster proves not singlemetricexplanation. Per-SIP identities retained, IDs capture-local; not joined to othernativecaptures by kernelname.

## Sparse selected-program source projections

Exact shared-source2D ROWS1 arithmetic/indexing; four clocks +publicationonlyprogram0. No addedsourcebarrier, actual GPUbarriers2/0/2 unchanged. Compilerlocal fences2→10 fromrecordpublication; per-block resources/control changed. InstalledSDK readonlytimer shim, leaderguarded staging, rawticks/frequencyunverified.15nativecalls/config with same-invocationprogram0/workitem0 records. Brackets are sourcecontrol-path timing, not physicalvectorcompletionorbusy.

| Configuration | maxbracket ticks | sumbracket ticks | probe task us |
|---|---:|---:|---:|
|P4|1096|1110|118.169|
|R1|855|690|74.745|
|alt2|1245|1109|76.186|

Independent whole-task comparison suggests~2.7/5.1/3.4% addedcost respectively; formalpairedperturbation not yetdone. Differentcalls cannotbe stitchedintopipeline; actororigin unverified, do notdrawcrossactoroverlap. Sparse timing reductions support mappingeffect but explain neither originalphasefraction nor its full38% walltimegain.

## Story and classification boundaries

Same source optimization knob has different execution meaning: NVIDIA4warps versus GCU4work-items withprivatevectorlowering. Comparable program/block organization and cooperative reductions are proven; same GPGPU/SIMT hardware is NOT claimed. Compiler mapping identifies actual collective topology and source-to-backend correspondence; per-SIP metrics expose backenddetails absent from simple source-regionduration. This case supports profiling services that preservebackendexecution details. It does not experimentally benchmark Proton/KPerfIR or prove their abstractions fundamentally incapable ofextension.

Full search/negativecontrols retained in `enflame-candidate` (earlier medium exploratoryw4 was NOT finalN). Finalmedium/smallNw1 have no manufacturedfour-itemP. Mainoverview matching3shapes,2N-nativeconfigs,3×30calls is separate `softmax-matching/`. Independent NVIDIA casecontrols now verified by root: `artifacts/study-goal-run/pro6000-independent-r008/case-controls-independent-r008`, three90callconfig totals, native batchmediansw4all1.152us,w1all1.248us,w2approximately1.216us. StaticNVIDIAcolumn assignment independently checked actualemittedLLVM/PTX: striped193/192/192/192 usefulelements perwarp versus GCUcontiguous256/256/256/1 pervectorworkitem. `static-column-mapping.json` recordsformula/sourcehash; staticusefulcounts are NOT measuredutilization or solecausalexplanation.

## Reproduction

Remote source/scripts `driver.sh`, `benchmark.py`, `tail_brackets.py`, immutableNselection; all exact argv saved in nativeexecution/portexecution files. Timerhelper existing path `/workspace/flagprism-study-closure-20261013/sdk-clock/global-timer-shim.ll`, inspect priorSDKprovenance before reuse. `analyze.py` is offline-only and verifies eventcoverage/identities/math/IRfields, exports compacttables. Raw resultslocal `artifacts/study-goal-run/enflame-tail-r008/`; no claimthese outsideGitfiles are committed yet.
