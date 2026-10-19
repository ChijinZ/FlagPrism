# Independent timeline deltas, R055–R056

This is an unfinished engineering checkpoint, not final acceptance.

The first NVIDIA independent 72-call run passed mathematics and numerical side
conditions but retained twelve missing-unit and nine observed-writer overflow
failures. Complete static libdevice branches can disappear during target
lowering after late LLVM instrumentation. The counter mapper now records
wholly unemitted static sites explicitly, rejects half-emitted brackets, and
still requires every actual raw endpoint to have its inspected machine getter.
All twelve original missing-unit captures re-exported successfully without
application replay; removing an actually used getter still failed in each case.
The original captures remain unchanged. Normal and optimized CPU map contracts
both passed 32 tests.

The full-CTA record policy uses the existing raw ceiling to improve capacity
for large participating blocks. It preserves the former 2 MiB allowance for
small blocks, targets 512 records per actor where possible, and caps the pair
at 8 MiB minus 128 allocation-guard bytes. The previous failures remain in the
denominator. The latest policy's affected device regression is pending.

GCU's thirteen affected independent calls passed after the generic primitive
coverage and lossless metadata fixes. Current controlled runtime-work samples
have 28, 36 and 44 positive internal intervals for work 3, 7 and 11; the same
instrumented binary is used. The two matrix tilings have 196 and 106 intervals.
These counts are observations, not timing accuracy or optimization-gain claims.
All have actual internal nanosecond traces and observed dependencies.

Six newly exercised Ascend mixed AIC/AIV traces passed actual Trace Processor
SQL and standard Perfetto UI inspection. They preserve separate observer
scopes and do not claim cross-observer alignment or engine busy time.

`results.json` gives immutable small-evidence paths and hashes. Large captures,
compiler objects and SDK-private files remain on the existing server Docker
filesystems. No paper or Study data was modified. Unchanged historical UI,
native components and ordinary mathematical baselines were not replayed.
