# Automatic GCU relative record-block selection (R092)

This is an internal checker increment, not whole timeline acceptance or a
normally installed/public automatic source-loop rule. Production capture and
export behavior are unchanged; no wheel/native rebuild is claimed.

`inspect_inline_record_fields_auto` derives candidate straight blocks after a
DI-selected reader and direct guards. It checks the complete candidate through
the next control packet, preserving late-overwrite/alias/unknown diagnostics.
Non-padding co-issued instructions in the terminating control packet are
rejected. No instruction addresses, register names, operator names or object
hashes select the algorithm. Existing reader/value-flow code validates each
candidate; ambiguous candidates are rejected. Input instructions still require
independent ELF binding. MMIO, incoming begin/site, ring/selection, external
entries and source/loop qualification remain unverified.

The actual owned Docker runner finished in 2.671033470 seconds: 46 normal and
46 `-O` tests passed, including seven semantic negative cases for automatic
selection and the existing reader/record tests. The pytest optimized-mode
warning is retained. Two rounds of Ruff/YAPF/check-AST passed; formatter AST
identity was checked. Returned source bytes are the committed source bytes.

The runner also checked two unchanged actual loaded ELF/native inputs, including
all nonzero executable bytes and the descriptor/symbol extent. Automatic
selection checked one of 23 distinct end-marker locations: ELF 7d56f25… site1's
shared end at 0xaaa0 selects a whole block beginning 0xabcc. The other 22 retain
concrete unsupported-reader/guard/path diagnostics; this is not 23/23 source
qualification. There was no device execution, application replay or SDK codegen.
Manual tail selection is absent from this new path.

Raw receipt archive SHA256:
`385df2fb5bfef6f474a5da05ea61db72bf42a86e6ef6def6cb2f3f41fad49e7b`.
Full workspace receipts are in `artifacts/timeline/run-092/preflight/`;
server root `/tmp/chijin-timeline-r092-gcu/runs/automatic-tails-v2`.
V1 preceded the additional control-packet-store rejection; it remains in the
raw archive and is not substituted for final V2. The initial local packaging
attempt referenced a nonexistent pyproject.toml and launched no worker.

Remaining original goal work: integrate automatic finite final source/loop
checks into normal capture/offline paths for GCU/Ascend, connect actual required
capture coverage, and obtain independent delta closure. This helper alone does
not satisfy those gates.


## Follow-on ELF binding component (V5)

`gcu_native_image.bind_instructions` now supplies the previously test-only
ELF/disassembly binding as an internal product component. It checks bounded
ELF sections, ordered/non-overlapping instruction bytes, descriptor/symbol code
extents and all nonzero executable-byte coverage. SDK routines elsewhere in the
same executable section remain byte-bound, separately counted, and excluded
from the returned kernel body. This is byte binding of trusted SDK disassembly,
not an independent ISA decoder or source/reader qualification.

V5 terminal0 /2.869233883s: 60 normal and60 optimized tests passed; two unchanged
actual loaded objects match the independently retained byte-audit instruction
lists. The record-block outcomes stay1/23. Formatter/AST checks passed; returned
source hashes match this commit. Source-image fixtures are synthetic corruption
checks; the two loaded objects are the actual positive evidence.

V3 initially rejected linked SDK code outside the kernel symbol, which actually
exists in both real images. V4 corrected the scope and added its positive
fixture. V5 additionally bounds aggregate symbol-table traversal. Their original
terminal/results remain in workspace archive SHA256
`30cb01526b039771e15d1c111338b849c3055986fe8287e56455ad3b83c0a7c8`.
No normal install, new compiler/native build, device execution, public provider
integration or source-loop qualification is claimed for these internal helpers.
