# Late recording public-integration components (r035)

This is progress toward the timeline goal, not full acceptance. The default
NVIDIA timeline hook has not been switched to this recorder. No paper/Study
files changed; no new Perfetto/clock/three-backend qualification is claimed.

The maintained parent patch adds a real LLVM-text callback after ordinary O3
and scratch metadata extraction. The component transform uses the actual
matching LLVM22 native recorder, keeps compilation input/output/logs and process
receipts, validates its manifest, and commits scratch metadata after success.
The wheel assembler can package the separately built recorder and checks its
bytes and executable mode. No core native rebuild is claimed: unchanged core
C++/CMake inputs were byte-bridged to the actual r024 ABI3 build, while the
standalone tool was rebuilt separately.

The installed wheel (`d74e84a2…`) had 608 installed members checked against its
archive. The installed parent callback compiled an ordinary unannotated kernel
with distinct ordinary/profile cache identities, one cold transform and warm
reuse, in normal Python and `-O`. The installed generic driver tests ran one
ordinary and one instrumented launch each for nonlinear elementwise and row
Softmax; original CPU-double math, inputs, output tails and raw guards passed.
These are development cases, not independent qualifier cases or default API
acceptance. The same tool also recorded runtime/constant-K GEMM prototypes.

Real capacity loss from the first K224 run is retained. The candidate default
capacity was then increased from 128 to 256 records per actor, within the
existing 8MiB raw capture budget for these tests. Five successful real captures
and the original overflowing capture were decoded by the installed raw module
in normal Python and `-O`; seven damaged-byte cases were rejected. Arrived-empty,
not-arrived and divergent streams are explicitly decoder fixtures, not device
measurements. Raw decode does not grant collective dependency eligibility.

After formatting, native LLVM output for both GEMM inputs differed only in the
first `ModuleID` input-path comment, and the recording manifests matched apart
from executable/output provenance. The initial overly strict byte comparison
failure and its exact diff are retained. Existing public/machine/wait contracts
passed 70 tests and two subtests in both normal Python and `-O`.

`verification.json` binds current source to installed inputs and the immutable
local archive, including original allocation bytes, PTX/CUBIN, native build and
wheel receipts, first failures, callback/cache results, and raw contract output.
The archive is 20,883,032 bytes, SHA256
`3801fdc83cb998cd80645bd87dcc910b32097058fb1c1cc04e35b10e44456a33`.
All 2,465 retained file hashes were audited. The 66 distinct recorded NVIDIA
process identities were inactive at collection. GCU formatting used its existing
Docker; no GCU device work was performed this round.

Next: connect the new compiler manifest to the default hook, existing owner and
stream lifecycle, the generic raw decoder, actual final-machine timestamp/source
mapping and standard Perfetto export. Ascend/GCU full timelines, dynamic clock
and async evidence, independent six-math qualification and the three additional
specified final reviewers remain required.
