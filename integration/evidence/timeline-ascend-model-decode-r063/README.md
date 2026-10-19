# Finite Ascend final-object decoding evidence (R063)

This diagnostic uses the installed CANN CPU simulator only to obtain instruction
names and PCs for an unchanged ELF already executed on hardware. It does not
provide simulated durations to FlagPrism, modify the SDK/device ELF, or qualify
arbitrary source regions. No product code changed.

The original hardware ELF and the SDK's dumped ELF have identical SHA-256:
`73c2d8d27a949359f22fce1095c56706240d065cad492e73f97653848d682b0d`.
The SDK supplies text-load base `0x10d11000`; the retained ELF has a single
zero-address `.text` section. All 1,728 SDK-reported aggregate PCs fall within that
section. Of 36 retained counter markers, 28 appear in the CSV and decode as
SYS_CNT reads with the expected destination registers. Eight markers are absent
from the retained CSV and remain unverified by this diagnostic. Because the SDK
child failed and output completeness is unproven, absence does not establish
that a marker never executed.

For the existing public recurrence example, source fragment 16 contains both
`VMULS` (0x12e8) and `VADDS` (0x130c) between readers 0x12d0 and 0x1334.
Fragments 17 and 18 contain the two expected MTE3 store instructions between
their respective readers. The original source-fragment hashes and manifest
bindings are retained. Internal branches are explicitly reported: numeric PC
containment is not an all-path boundary proof, and the result grants no source
exclusive-cost, physical engine busy/completion, or ordinary-overlap rights.
No runtime product qualification flags are changed.

The original outer controller and SDK CLI both returned zero. However, the SDK
stdout explicitly reports a child-process exit status of **139** after the host
wrote its mathematical/state/guard success report. This is **not** a successful
end-to-end simulator qualification. Both facts are preserved in the terminal
receipt. The generated decoding material was audited without replaying the
model or hardware application. The prior two host builds failed before any
simulation because of SDK include search paths; those failures remain indexed.

`model-only-host.cpp` is a finite SDK diagnostic loader for this existing public
example's ABI, not a product frontend or per-operator profiling requirement.
`model-only-runner.py` records the original run, including the overly permissive
SDK outer exit; its output is interpreted with the explicit child failure above.
`retained_decode_audit.py` only reads existing output in the server Docker.
SDK private headers, model libraries/configuration, and model-generated times
are not published as product traces. Larger retained inputs and SHA-256 hashes
are indexed in `local-input-index.json` and remain in the workspace/server.

No new mathematical qualification, Trace Processor/UI result, performance
measurement, or full-goal acceptance is claimed here.

## Additional finite compute-prefix check

A retained-only server Docker check in normal Python and `-O` establishes that
every 4-byte position from site16's entry through its VADDS has an SDK decoding
row, with no JUMP-family instruction or END before the two required operations.
This strengthens numeric containment to a local contiguous prefix without
control transfers. Three negative fixtures reject an exit before the add, a
missing decoded prefix instruction, and a branch before the multiply.

This is not proof of external-entry coverage, actual hardware dynamic order,
or all paths through the entire region. The independent reviewer assessed the
finite criterion as sound, including JUMPC/JUMPCMP in the JUMP family; that
follow-up did not execute or perform a new line-by-line script review. It grants
no additional runtime proof rights. No model, application, SDK compiler,
Trace Processor, or UI was rerun.
