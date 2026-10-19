# Finite NVIDIA pipeline-impact investigation

Shipping runtime remains 730b9fe; optional site-budget test is d882cf8. These are retained actual-device objects and captures, followed by CPU inspection. No application was replayed by the inspection, compiler probe, or SQL verification.

Four sparse ordinary/profile runtime-K mathematical calls passed. The enclosing regression exited 1 because observed dependency qualification conservatively rejected a partial or predicated write to the published count. Preserve that failure; do not claim qualified sparse time arrows. Existing native-boundary/wait checks passed on the retained objects.

Ordinary default/sparse PTX and cubin are identical. Profile variants preserve the 21 critical native instructions and wait/barrier mechanisms but change instruction interleaving. This neither certifies ordinary overlap preservation nor proves complete engine serialization. The bounded CPU matrix-clock clobber-removal probe did not restore ordinary interleaving and is not shipped.

All 20 newly produced sparse counter/shared traces passed the pinned actual Trace Processor verifier. This certifies import/timing export consistency, not source-exclusive duration, ordinary pipeline fidelity, or advanced dependency arrows. Earlier 1,740 traces and UI checks were not repeated.

Full local archives and hashes are in artifact-index.json. Selected receipts are committed; large raw/binary inputs remain in the archives and server-owned run paths. The finite compiler review is pending. The overall pipeline-impact acceptance item remains open.


## Finite actual matrix issue and runtime occurrence check (run062)

An additional CPU-only check re-read the four already recorded default/sparse K3/K7 captures. It freshly reconstructed each actual machine map from retained cubin/PTX/SASS and checked the four original FP16/F32 matrix issues against their exact embedded PTX lines, unconditional readers and a single-entry straight native path. Default readers are0x1260/0x1310 around HMMA0x1270/0x1290/0x12b0/0x12d0; sparse readers are0x1010/0x1090 around HMMA0x1020/0x1040/0x1060/0x1080.

Each capture has eight displayed observers, each with3 or7 positive issue intervals matching the runtime tile parameter:24/56 intervals per capture,160 across all four. Endpoints match actual raw timestamp words. Occurrence counts are not promoted to loop iteration identities. Product/runtime flags remain unchanged. No application/compiler/device was executed. This is finite native issue-placement and runtime occurrence evidence, not an arbitrary-kernel, exclusive-cost, engine-completion or ordinary-overlap certificate. The existing sparse dependency rejection remains unchanged.


## R064 all-clock memory-clobber diagnostic (not shipped)

A single CPU-only codegen probe on the retained actual default LLVM removed
memory clobbers from all 70 counter-reader calls, preserving input/output
operands and other instructions. Actual target codegen/ptxas/nvdisasm and the
counter map completed. The 21-instruction critical opcode/wait projection still
matches the existing profile rather than ordinary execution; four HMMA
instructions remain between the matrix readers. Thus removing those clobbers
alone does not recover the original critical interleaving. This is a negative
probe, not a repair or a unique root-cause result. No application/GPU execution,
product mutation, hardware-overlap or source-cost qualification is claimed.
Actual compile outputs remain in the indexed 78,964-byte archive. The owned
worker is missing and its terminal controller is only a zombie, not live work.
