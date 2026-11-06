# MetaX detailed timeline qualification — 2026-11-06

Public automatic recording was tested in `chijin-flagprism-metax` with real user
Triton kernels. Four kernel tests passed: vector, reduction, matrix and loop,
each warmed outside capture and launched twice inside it. Three bounded checks
passed: a 2D grid, capacity=1 loss reporting, and auto→timeline session/allocator
restoration. The packaged release's vector smoke also passed. Exact pytest
output, raw/canonical file hashes and native build/install receipts are retained
here; full original bundles are under project `artifacts/metax-detailed-2026-11-06/`.

Independent actual Perfetto Trace Processor verification parsed twelve traces
from the four kernel tests, with slice counts equal to their canonical observer
events and no unfinished slices. Every root track explicitly declares NOT ns.

The first MetaX vector ABI proof selected native LLVM sites automatically and
recorded first/last logical programs 0 and7. The initial reused Torch CUDA
transport produced an all-zero second capture under repeated launches. Replacing
initialization alone did not fix it. The MetaX-specific SDK transport (device and
pinned host allocation, exact-stream events and readback) fixed the repeated
public capture tests. This evidence establishes the successful adapter boundary;
it does not claim a proven single root cause in PyTorch's compatibility layer.

Opaque compiler operand dependencies use actual supported 32-bit `r` constraints,
splitting64-bit values. SDK rejected `v` and `l` variants before device execution;
those were not enabled. The tested dependent vector retained correct output and
complete records. Hardware timing boundaries, counter tick-to-ns conversion and
cross-observer alignment remain unqualified.

`detail="auto"` on MetaX uses bounded first/last feedback, not an all-grid census.
Schema1 records expose written/retained counts and a saturation flag; exact drop
counts are not manufactured. Overflow is explicitly incomplete. Perfetto files
are presentation-only raw-counter coordinates, one observer per file.

The final tool was rebuilt after narrowing the matrix classifier to actual
`llvm.mxc.mma/wmma/mfma` namespaces (avoiding accidental gamma-function matches).
This preserves classification for the tested `llvm.mxc.mma.f32.16x16x16f16`.
The final build receipt records its exact SHA. The package smoke preceded that
namespace-only narrowing; no additional GPU round was needed or claimed.

Inside the container:

```bash
source /workspace/env.sh
source /root/chijin-metax-detailed-20261106/release/activate.sh
/opt/conda/bin/python3 /root/chijin-metax-detailed-20261106/timeline-source/Profiler/examples/metax_timeline.py --output /tmp/my-metax-profile
```

The standalone example was syntax checked and follows the tested vector/API
path. Its output directory must be fresh. Full installation details and scope
are documented in `docs/metax.md`.
