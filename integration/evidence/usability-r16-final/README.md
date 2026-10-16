# Final automatic-profiler usability delivery

The frozen current implementation meets the recorded basic automatic-mode
acceptance on the three validated compiler/SDK environments. The original
independent six-kernel cohort passed 24 ordinary combinations and 48 cold/warm
profile runs on each backend. Ascend's generic SDK repair additionally passed
two new independently authored mathematical kernels (8 ordinary, 16 profiles).
Original failures and repaired-version results remain distinct.

Start with the [current installation and usage checkpoint](../../../Profiler/docs/qualification.md).
It includes the existing Docker/venv commands, result counts, report entry point,
reproducible source-build links and limits. The default service supplies
source-linked internal visits, observers, programs, calls and exactness; it does
not manufacture instruction durations or aligned hardware pipelines.

Evidence: [NVIDIA](../usability-r16-nvidia-current/),
[Enflame](../usability-r16-gcu-current/),
[Ascend original cohort](../usability-r15-ascend-main24/),
[Ascend additional kernels](../usability-r15-ascend-new8/),
[installation](../usability-r15-python-alignment/), and
[final independent reviews](../usability-r16-final-review/).
The latter separates three product roles from the three additional requested
GPT-6.1-Sol/xhigh code-review seats and preserves their actual scope.

`ACCEPTANCE.json` maps requirements to evidence. The contract and execution
record snapshot document the scope; the live root record remains outside Git
and is not automatically committed. Final Git push/remote identity are verified
after creating this checkpoint, avoiding a self-referential commit hash.

All owned device runs and browser checks have ended. No NVIDIA device
performance certification was performed. This engineering task did not edit or
build the paper or old Study data; previously observed parallel paper changes
were preserved without guessing their author or restoring old versions.
