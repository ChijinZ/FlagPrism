# Independent retained-capture audit

The two external archives are content-addressed in the root audit JSON. They remain outside Git (87.6MB and 27.1MB compressed). The audit validates every bundle manifest file by size and SHA, original buffer SHA and raw record identity, actor cursor/attempt/drop statistics, and the 20ns local duration formula. It runs as offline analysis of retained bytes, without invoking the profiler implementation.

The first archive contains 108 six-family requests plus nine fixed-shape T5 requests: 117 results, 78 bundles, 11,232 manifest entries, 8,976 observations and 315 raw buffers. The second contains 18 heldout requests plus three detailed and three native long-K controls: 24 results, 18 bundles, 2,584 entries, 2,520 observations and 48 raw buffers. Entries are checked per bundle, not necessarily distinct file contents across captures.

These observations have zero declared drops and local rate conversion, not a verified shared clock origin. Numerical tests executed in Ascend Docker; this independent audit checks their recorded results and trace consistency, not a second numerical execution. Short long-K controls contain three samples/config, not a full performance acceptance.

Wheel-r4 verifies packaging/import of the accepted runtime binaries. The root hash audit shows one later explanatory HTML source change; compiler-static dependency modules are being developed subsequently. Wheel-r4 is therefore not the final source freeze.
