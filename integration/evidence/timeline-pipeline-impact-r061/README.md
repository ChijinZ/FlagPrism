# Finite NVIDIA pipeline-impact investigation

Shipping runtime remains 730b9fe; optional site-budget test is d882cf8. These are retained actual-device objects and captures, followed by CPU inspection. No application was replayed by the inspection, compiler probe, or SQL verification.

Four sparse ordinary/profile runtime-K mathematical calls passed. The enclosing regression exited 1 because observed dependency qualification conservatively rejected a partial or predicated write to the published count. Preserve that failure; do not claim qualified sparse time arrows. Existing native-boundary/wait checks passed on the retained objects.

Ordinary default/sparse PTX and cubin are identical. Profile variants preserve the 21 critical native instructions and wait/barrier mechanisms but change instruction interleaving. This neither certifies ordinary overlap preservation nor proves complete engine serialization. The bounded CPU matrix-clock clobber-removal probe did not restore ordinary interleaving and is not shipped.

All 20 newly produced sparse counter/shared traces passed the pinned actual Trace Processor verifier. This certifies import/timing export consistency, not source-exclusive duration, ordinary pipeline fidelity, or advanced dependency arrows. Earlier 1,740 traces and UI checks were not repeated.

Full local archives and hashes are in artifact-index.json. Selected receipts are committed; large raw/binary inputs remain in the archives and server-owned run paths. The finite compiler review is pending. The overall pipeline-impact acceptance item remains open.
