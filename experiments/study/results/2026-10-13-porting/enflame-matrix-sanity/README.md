# GCU matrix path sanity (bounded appendix)

Frozen GEMM512³ N config BM32 BN32 BK32 w4 s4 yields target P local16×16 dot operands. Existing three90total TOPSPTI batches give ~94.741ms/task. Independent counter-free device-stream batch median94.756ms and synchronizedhost94.792ms corroborate this order; native units are not the explanation.

One guided work-item-only intervention keeps grid256, BM/BN/BK32 and stages4, changes w4→w1, localdot becomes32×32. One30-call native batch median268.529us. Two larger-tile controls BM/BN/BK64: w4 local32×32 median266.1215us; w1 local64×64 median73.1015us. Every CPUFP32 reference passed with identical canonical inputbytes. These controls are bounded single-batch diagnosis, not yet a fullyindependentlyreplicated newoptimizationcase.

TCU original-binary replay records9invocations/config (6initial/warmup +3measurement),24 SIPinstances/metric. Original P has SIP/2D_EFFICIENCY exactly0 for all9invocations. Guided controls have positive2Dcycle shares: .786727/.395656/1.98662% medians for fixedgridw1/tile64w4/tile64w1. Original1Dcycle share16.8096%, versus .393364/.197828/.993311%; BUSY includesstall and is not purecompute.

Generated gcuir/llir maps exactmatmuloperandtypes and calls tops_addmm_fp16_fp32. Installed primary SDK helperdefinition is generic scalar multiply/add loops; downstream compiler may recognize/replace them. `installed-helper-facts.json` stores path/library/definitionhashes and derivedoperationcounts. Actualengineuse is supported by originalbinaryTCU, not assumed from helpername. Installed acore header documents separate nativepatterns, but we do not equate those directly with thehelper or infer universal32×32 hardwareminimum. No claimofchippeak, universalhardwarelimit, or accidentalfallbackwithoutfurtherproof.

This explains extreme initial portable-software-path latency in the overview. It is not a fabricatedslowP. The existing independentlyreplicatedSoftmaxtail case remains separately preserved. A tuningdirection claim for GEMM requires fresh NVIDIAw1/2/4comparison, underway separately.

Compact data includes fullnative resultJSON and generatedtextIR, exactnativeevents forcontrols, fullTCUcounterCSV and replayvalidationresults, hypotheses and commands. PrivateSDKlibraries/source and generatedfatbins are excluded; fullraw +binaryhashes remain in `artifacts/study-goal-run/enflame-matrix-sanity-r011/` and initial P raw in `artifacts/study-goal-run/enflame-overview-r010/`. These are explicitly differentcaptures; no joinbykernelname and no stitchedtimeline.

Run offlinevalidation from this directory with `python analyze.py`; it verifies correctresults/nativeidentity/coverage and rewrites `summary.json`. Experimental scripts execute inside existingservercontainer `flagprism-enflame-dev`, `/workspace/study-goal-enflame-matrix-sanity-r011`. Canonicalinputpath and all exactargv are in scripts/logs. Shared `run_case.py`/`kernels.py` versions are identified by resultsourcehashes; resolve them through activebranch/runtime snapshots ratherthan modifying the SDK.

## Expanded-native-choice w2 discriminator

Fresh NVIDIA512³ controls findw2=3.2155us,w4=3.296us,w1=3.632us; theoriginal4/8search wasbounded, notglobaloptimal. ExactGCUw2 at32³,s4/grid256 yields local16×32 output andpositive2Dcycle share.20546% (nineTCUinvocations), native30callmedian1014.554us. This falsifiesanyuniversalminimum32×32 claim; local16×32canuse2Dinthismapping, while16×16didnot. Targetw1still3.78×fasterthanw2inpreliminarysinglebatch, butremainingmechanismnotisolated. Do notreplacefrozenoverviewbaselineorprimarytailcase silently. PreservebothboundedsearchandexpandedNcomparisonfacts.
