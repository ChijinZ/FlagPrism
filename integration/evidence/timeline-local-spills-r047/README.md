# Fixed local timer spill development evidence

Source-only delta to the unfinished observed dependency timeline work.
The existing SM120 one-warp runtime-K GEMM stores both words of two clock
samples with STL.64 and reloads them with LDL.LU.64. The verifier now follows
fixed thread-local words through the actual native control graph. It rejects
uninitialized/bypassed slots, clobbered bases, possible aliasing, wrong words,
unsupported addresses and overwritten bytes. 32/64/128-bit local accesses keep
word offsets rather than treating a local stack as one interchangeable value.

The first run rejected nvdisasm JSON that omits the comma before local load
addresses. The parser now accepts that exact unambiguous representation after
the independent text/JSON instruction binding. The first failure is retained.

The final formatted source was tested with ordinary and optimized Python.
Each mode rechecks two four-warp captures (70 getters each) and two one-warp
captures (163 getters each), with 1,386 and 3,114 actual-object corruption checks
respectively. Six positive and ten rejection cases are CPU fixtures, not new
math or synthetic device timelines. Original inputs remain unchanged.

No device replay, recorder/ABI change, native rebuild or new wheel is claimed.
The one-warp dependency timeline still needs wide-literal and shared-payload
expression qualification; this evidence does not complete it. The original
compiled inputs are retained in the r047 development archive. The full goal,
other backends, independent math, default/offline integration and final three
fresh reviewers remain outstanding. No paper or Study files were changed.
