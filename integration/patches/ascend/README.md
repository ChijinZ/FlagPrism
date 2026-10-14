# Ascend FlagTree handoff recovery

Status: **pending complete patch export and build validation**. The first gateway
check on 2026-10-14 returned `no available gateway`. A later authorized retry
returned the actual container sentinel and hostname `chijin-v35`; baseline and
dependency HEAD reads succeeded. This directory is a recovery entry, not a validated final integration
patch. Do not publish `initial-handoff.patch` as the complete patch: it predates
the compiler cache-key callback.

The independent FlagTree baseline is
`0364ed4bc39d1dfae483741ec272298297fa5bda` (triton_v3.5.x). The original patch
SHA256 is `9a67673d0e55c3ae1e8941552a5f924b3117f101231568231d90e892fcc20c0d`.
`restore_core_handoff.py` applies the original driver prepare/finish callbacks
when absent, adds the codegen cache-key callback, verifies both supported
Ascend driver routes, and exports the complete resulting diff and dependency
identities. It refuses the user's main checkout and a different HEAD.

After access returns, copy these two files to the existing container's
`/tmp/flagprism-method-ascend/recovery-input/`, then run **inside that Docker**:

```sh
python /tmp/flagprism-method-ascend/recovery-input/restore_core_handoff.py /tmp/flagprism-method-ascend/recovery-input/initial-handoff.patch
```

Retrieve the generated `recovery/flagtree-driver-handoff-complete.patch` and
`recovery/core-handoff.json` into this directory, then save the actual independent
worktree change as a local commit and record its commit ID. No upstream push is
required. Preserve the full original baseline diff as the reproducible patch;
do not substitute a diff against the newly created commit. Export has not yet
run, so neither that complete patch nor its commit/hash is claimed here.

Dependency provenance: AscendNPU-IR must be pinned to
`4c30492166f6cfbc5fa0c81a72f53630b9a3e6a9`, obtained from the official dependency
declared by FlagTree's Ascend setup tooling. FLIR was cloned from
`https://github.com/flagos-ai/flir`; the actual remote checkout HEAD read after
restoration is `516ad3110cbf6112bbed8f927ae606c627a193f2`. Both dependency trees
must pass the tracked-clean guard in the generated manifest before calling the
entry reproducible.
Core compilation uses the existing LLVM22 cache. The late observer uses upstream
LLVM15.0.7 in a separate `opt-15` process; loading this plugin into the vendor
bisheng LLVM fork previously crashed and is unsupported.

Synchronize the canonical FlagPrism source into the independent worktree's
`third_party/FlagPrism` symlink, retaining current shared root/GCU source changes.
Build the actual `triton` target (producing `python/triton/_C/libtriton.so`),
runtime and separate observer, then follow `tests/ascend/README.md`. Latest
hidden-only binding, role checks and shared runtime changes remain pending real
build/tests. M3 automatic SDK evidence producer and public finalize integration
remain implementation work, not just an unexecuted test.
