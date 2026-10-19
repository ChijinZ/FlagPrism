# Native NVIDIA count lifetimes and sparse reexport (R070)

Runtime source `baea70620f8561369cc440fefba48f7938cbc25a` (base `7f8fdf5`).
The old function-wide inventory incorrectly treated temporary R12/R13 reuse as
counter writes. Actual sparse object writes at PC1456/1552 do not reach the
header/count-index uses. The checker now follows both words from those uses,
recursing through self-adds and retaining all live definitions on all paths.
Live partial/predicated/unknown updates still reject. No operator identity gate.

The independent compiler reviewer found a safety omission in the first fix:
a live zero assignment after recording could be mistaken for initialization.
The final guard checks predecessors of both zero initialization and fixed-base
initial batches against any earlier record store/nonzero count update.
The accurate regression has a completed first batch, a conditional zero-reset
path and a bypass path merging at publication; no backedge to the first batch.
It is explicitly a synthetic CPU native-CFG fixture, not device evidence.
The original finding and its fix/fixture/installed closure remain in the review.

Normal wheel installation passed: 639 packaged members matched actual installed
bytes; unchanged native sources were checked and existing native inputs reused.
Normal Python and -O each passed the four original default/sparse K3/K7 captures
and 21 negative cases. The previous address regression passed 33 negatives and
confirmed 113 originals unchanged. This installation changes the offline checker,
not the device recorder, ABI or captured application; no GPU replay is needed.

The installed public reexport CLI on an owned copy of the first sparse capture
produced eight counter traces and two observed-dependency traces, reason null.
The two newly qualified dependency exports passed the pinned actual Trace
Processor/protobuf/raw-word verifier: 180 endpoints and 404 flows each; full
stats retained, no positive error/data_loss. Old unchanged UI/SQL is reused;
no new UI run or repeated full matrix. Ordinary pipeline/source-region
qualification is not inferred from this successful reexport.

Failures retained: v1 assembly hit setuptools' absolute egg_info manifest path
rejection. The maintained assembler now supplies a relative egg_base (a71d32f),
and v2 assembly passed. V2 installation then hit old pip's missing --python
option. V3 seeds the target venv with standard ensurepip and installs normally
with its own pip; all 13 steps completed. No native build is relabelled as new.

Reviews cover limited deltas only: initial compiler/runtime/delivery review of
1326509; compiler additionally closes the zero-reset source/fixture/installation
fix. Delivery additionally closes its install gap from the actual installed/SQL
receipts and reviews the small relative egg_base assembler fix. None is whole
three-backend goal signoff. Finite source/loop boundaries and preservation of
ordinary critical dependency opportunities remain open. No paper/Study edits.
