# Controlled local-wait sensitivity and minimum source control

Actual worker source for the six fusion requests: runtime `18ed577` (same
accepted core/native/LLVM15 logger binaries). Fixed preregistered request order,
three warmups plus ten measured calls, three original long-K configurations,
all sites versus compiler-selected waits. This is a diagnostic-stability check,
not a replacement 3x30 cost campaign or an accuracy certificate.

The original preinstrumentation actor LLVM bodies are byte-identical within
each mode pair after removing only the ModuleID temporary-path line. Original
AIC CFG has phi0, signed-less-than128/16, increment1; signal counts and header
visits agree. Root independently verified all7 retained results (six requests
plus the separate source-bound128-cubed mixed smoke),1030 bundle manifest
entries,82 original buffers and7759 records, source/SDK/job/artifact identities,
portable source bytes, counts and local20ns arithmetic. No profiler modules
were imported by the audit. The original worker's numerical execution is
retained evidence, not rerun by this offline audit.

Negative result: P32 all-site AIV waits55.37/54.72us versus wait-only31.31/29.83us
(+76.8/+83.4%). P32-to-BK256 waiting decreases in both modes. The smaller
BK256-to-output-tile64 difference is not stable; it cannot explain the second
speedup. No cross-actor/native clock alignment, engine occupancy or precise
unperturbed wait cost is inferred. `wait-fidelity-measured.csv` preserves all120
measured AIV initial waits, separate actor/call IDs and raw local ticks.

The independent minimal source control uses the unchanged original cached
pure-AIV image, one block, two output words,64 fresh guarded outputs and no
observer or added kernel completion barrier. All64 raw pairs have zero tick
difference and distinct advancing per-call start counters; all17408 storage
bytes were independently checked, including exact canaries. The final GPU
image SHA and actual launcher agree. One CPU replay of the original SDK argv
reproduces the original intermediate-object SHA; this replay is not a second
GPU execution. Device-side `-S` was rejected. Consequently two source reads are
verified, but final adjacent machine instructions and an absolute wait-error
bound are not claimed.

Raw archives remain in workspace `artifacts/method-run/ascend/round2/`:

* `round2-source-fidelity-evidence-r2.tgz`,23709496B,
  SHA256 `ba5fb4b31823e353f43267494d7e80435ede97f2ded9256bcdf8b28ee0f79974`.
* `round2-final-small-proof-r2.tgz`,87178B,
  SHA256 `1cb9d8ef231783716b90930ff1ea3faf2701fee78aa7d2b2971f0fbf8f0cf7af`.

For offline audit replay, place archives beside these scripts and safely extract
regular members of the first into `root-extracted`, the second into
`root-small-extracted`, then run the respective root audit scripts. Both archives
had no unsafe or link members. Later stricter manifest-provenance validation
retains its own source version and separate derived-sidecar revalidation; the
original bundles and timings must never be silently rewritten or relabelled.
