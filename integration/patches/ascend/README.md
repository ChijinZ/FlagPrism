# Ascend FlagTree handoff recovery

Status: **native worker receipts validated; detailed hardware validation incomplete**. The first gateway
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

To reproduce the export from the pinned uncommitted baseline, copy these two files to the container's
`/tmp/flagprism-method-ascend/recovery-input/`, then run **inside that Docker**:

```sh
python /tmp/flagprism-method-ascend/recovery-input/restore_core_handoff.py /tmp/flagprism-method-ascend/recovery-input/initial-handoff.patch
```

Retrieve the generated `recovery/flagtree-driver-handoff-complete.patch` and
`recovery/core-handoff.json` into this directory, then save the actual independent
worktree change as a local commit and record its commit ID. No upstream push is
required. Preserve the full original baseline diff as the reproducible patch;
do not substitute a diff against the newly created commit. The export has now
run in the actual Docker worktree. The resulting patch SHA256 is
`a0d612e6ca1d7d30728c3dec1b901d2a282c8190dc65912248c04a91f8a1ff92`;
`core-handoff.json` records the original baseline, both transformed file hashes
and clean dependency HEADs. A worktree integration commit is still pending.

Dependency provenance: AscendNPU-IR must be pinned to
`4c30492166f6cfbc5fa0c81a72f53630b9a3e6a9`, obtained from the official dependency
declared by FlagTree's Ascend setup tooling. FLIR was cloned from
`https://github.com/flagos-ai/flir`; the actual remote checkout HEAD read after
restoration is `516ad3110cbf6112bbed8f927ae606c627a193f2`. That unpinned revision failed
against the baseline TLE API. The restoration is now compiling the official
older FLIR revision `ff91e64b6042a27e0db053f28ea3741be65d24d0`; it has
compiled and linked the full new core and standalone `triton-mlir-opt`.
Two native vector shapes have compiled and run through those exact tools.
The six-family detailed matrix is not yet validated with this dependency. Both dependency trees
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

`patch_launch_receipts.py` has been **applied to the isolated Docker worktree**;
the generated worker was compiled and executed through the public profiler. It is not the exported complete
patch. It was reviewed against the official immutable 0364 driver SHA256
`31630a5e4ed2c60f00825cf248c0964cdcb01b87e8e7b67d27838630463eebbb`.
After restoring access, verify the actual independent worktree driver hash,
then run this script there. It adds an optional metadata capsule, pure C++
retained worker callbacks and SDK thread-last-task/stream/device queries right
after the original `rtKernelLaunch` (including its supported alternate SDK
launch path). No kernel formal parameter is added. Header bytes come from the
registered authoritative provider and participate in generated wrapper cache
identity. Absent provider plus present capsule fails explicitly. The worker
patch was applied on 2026-10-15 (three source files changed). The actual public
native smoke passed four calls, two binaries and two streams, including valid
task zero, retained worker IDs, unique SDK capture seals and exact SDK
connection-table proofs. Its complete exported source diff is retained in the
evidence archive described below; the older two-file patch above is incomplete.

The restored full core build genuinely compiled the Debugger hidden-only helper
objects, then failed in FLIR516ad3 because its incubated conversion references
`tle::SymmAtOp`, absent in the pinned FlagTree0364 TLE API. FlagTree declares
FLIR with an empty commit pin. Resolve this published dependency compatibility
before claiming a linked new `libtriton.so`; deleting the feature or disabling
warnings is not a validated recovery. SDK/codegen header requirements discovered
by actual builds require the configured `ascend;nvidia;amd` backends and official
TableGen generation before component compilation.

An independent native ACLprof single-owner capability probe did collect a real
Triton vector kernel, valid SDK MSTX range and native task/connection tables on
device4. The external msprof-op range owner returned an invalid range and no
data even through the SDK Python API; its exit0 was rejected. Neither probe
used the formal new hidden-only binding. The receipt registry, SDK epoch directory seal, generated worker bridge and
automatic task-identity producer now have actual public native-smoke evidence.
Associating those proofs with the normalized report and clock counter/domain
production remain separate implementation work; task identity alone does not
certify shared-axis alignment.

Full core build5 terminated with the old Ascend GPU layout API mismatch:
`CTAEncodingAttr` is absent in this FlagTree baseline. The component now uses
its actual `CTALayoutAttr::get` only in the Ascend build branch. The new NVIDIA
and MThreads layout branches and program-selection semantics remain unchanged.
Build6 linked the full core with warnings retained. Its shell exit1 was the
subsequent checksum command using the wrong expected output path; the actual
`compiler-build/libtriton.so` SHA256 is
`4fa158e2d08c6bbe3ac952e1ebb5fae7909beb23bde4588cd5677da7956a3a6e`.
The standalone tool required configured AMD/NVIDIA generated-header include
roots and the actual PTXBuilder library dependency; neither registration nor
features were disabled. Its SHA256 is
`72e6764ce12c9272563f08b5679ef5ef5d1ddb6ad65a443f0eb7ac17b81d2b4e`.
Actual new-core hidden-ABI and backend contracts passed 80/80. This is not
detailed end-to-end acceptance: the first genuine observer launch exposed a
common metadata-capacity overwrite, underallocating three actor segments. That
failure is retained. The common fix and symmetric preallocation checks then
passed 11/11 contracts plus a valid 49248-byte zero-buffer allocation/export.
A fresh Softmax32x256 hidden-only run passed math/input/canaries and exported
32 dynamic records over four calls. Default temporary SDK output is currently
removed too early for the Python identity producer; fixing that lifecycle and
normalized-report association is still required.

The immutable native-smoke evidence archive is repository-root
`artifacts/method-run/ascend/native-receipt-evidence-r3.tgz`, SHA256
`6d61cfdec74816062e37b5f0ac8c5e8ea6fa0e6273960568a8dc3b0f8c867eaa`.
It contains SDK raw packets/SQLite, the public bundle, source-byte and binary
hashes, full core source patch and build/contract logs. No SDK libraries are
shipped. The public smoke command in the Docker is:

```sh
METHOD_SOURCE=/tmp/flagprism-method-ascend/source \
METHOD_COMPILER_SOURCE=/tmp/flagprism-method-ascend/FlagTree \
METHOD_COMPONENT_PYTHON=/tmp/flagprism-method-ascend/compiler-python \
python /tmp/flagprism-method-ascend/source/tests/ascend/native_receipt_smoke.py \
  --device 4 --output /tmp/flagprism-method-ascend/new-unique-native-smoke
```

Exported task proofs remain `clock_alignment=unverified`. Native lifecycle
envelopes do not establish actor occupancy or cross-actor counter offsets.

`flagtree-source.patch` is the full public-source diff exported from the actual
validated native-r3 worktree, including worker bridge and standalone build
repairs. `flagtree-source-manifest.json` records the original baseline, exact
dependency pins, patch/binary hashes and remaining validation boundaries. Use
this full patch for a new worktree; do not layer it on the historical partial
patches. Component source remains a separate synchronized/pinned dependency.
