# Current automatic-mode validation

This checkpoint validates automatic source-site visit profiling on NVIDIA RTX
PRO 6000, Enflame ZIXIAOC200 and Ascend 910B. Use the matching
[compiler build recipes](../../integration/patches/README.md) and
[automatic-mode guide](automatic.md). A stock compiler wheel is insufficient.

## What was exercised

The installed Python component is `a829a3312af69c1b961919025053829d7096a2b1`.
Its native components retain the byte-verified inputs from the actual
`bd61acd` build. Later repository commits add SDK build tools, tests,
documentation and evidence; they do not imply that every native component was
recompiled. Installed source, staging, wheel members, native dependencies and
parent integrations are recorded in the
[installation evidence](../../integration/evidence/usability-r15-python-alignment/).

Each backend ran the original independently frozen six-kernel cohort: two
kernels in each of pointwise/fused memory, reduction and matrix/fused compute,
each with two shapes and two legal backend configurations. Tail handling,
runtime loops, unchanged inputs, output canaries, original numerical tolerances,
per-program side effects, source/binary/invocation identity and full-grid raw
records were checked. Every eligible combination was retained. Cold/warm here
means compiler-cache state, not a device performance benchmark.

| Backend | Ordinary combinations | Default cold/warm profile runs | Actual reports browsed | Largest complete bundle | Largest host export |
| --- | ---: | ---: | ---: | ---: | ---: |
| NVIDIA | 24/24 | 48/48 | 6 | 2,026,437 bytes | 0.521 s |
| Enflame | 24/24 | 48/48 | 12 | 23,212,507 bytes | 0.515 s |
| Ascend, original cohort | 24/24 | 48/48 | See additional cohort below | 22,082,976 bytes | 1.061 s |
| Ascend, two additional independent kernels | 8/8 | 16/16 | 4 | 20,499,086 bytes | 1.059 s |

Some runtime-control scripts request two kernel calls; profile-run and capture
counts therefore differ. Counts above describe complete script/profile runs.
Browser checks used actual generated reports, source anchors and backlinks,
records/actor/program/visits views, execution mapping and raw evidence. They did
not launch additional kernels. Export and bundle sizes are engineering bounds,
not kernel latency, throughput or profiler overhead measurements.

The original cohort is current-version revalidation, not newly unseen
mathematics after every repair. Earlier failures remain in their original
reports. Ascend's two original State failures were followed by a generic SDK
scalar-store legality repair, exact failing-combination revalidation, the full
original cohort and two additional independently authored mathematical kernels.
The system SDK was preserved; a separately built compiler was selected by
absolute path and SHA-bound cache identity.

Read the backend evidence and its scope:

- [NVIDIA original-cohort revalidation](../../integration/evidence/usability-r16-nvidia-current/).
- [Enflame original-cohort revalidation](../../integration/evidence/usability-r16-gcu-current/).
- [Ascend original failing combinations](../../integration/evidence/usability-r15-independent-finite2/),
  [full original cohort](../../integration/evidence/usability-r15-ascend-main24/),
  and [additional independent kernels](../../integration/evidence/usability-r15-ascend-new8/).

## Use the installed development environments

These paths identify the existing validated server containers; they are not
portable installation commands. For a new machine, follow the build recipes.
Inside each corresponding Docker, use a fresh output directory and a normal
application script that selects the same runtime device as the CLI:

```bash
# NVIDIA: chijin-study-pro6000, device 0
/workspace/chijin-r15-python-alignment-r2/venv/bin/python -I \
  -m flagtree.profiler.cli --detail auto --device 0 \
  -n /workspace/my-profile /absolute/path/my_script.py

# Enflame: flagprism-enflame-dev, device 0
FLAGTREE_BACKEND=enflame \
/workspace/chijin-r15-python-alignment/venv/bin/python -I \
  -m flagtree.profiler.cli --detail auto --device 0 \
  -n /workspace/my-profile /absolute/path/my_script.py

# Ascend: chijin_v3.5.x, device 4
FLAGTREE_BACKEND=ascend TORCH_DEVICE_BACKEND_AUTOLOAD=0 \
TRITON_ASCEND_COMPILER=/tmp/chijin-r15-sdk-scalar-legality/install-fixed/bin/bishengir-compile \
/tmp/chijin-r15-compiler-identity-install-v2/venv/bin/python -I \
  -m flagtree.profiler.cli --detail auto --device 4 \
  -n /tmp/my-profile /absolute/path/my_script.py
```

Initialize the vendor SDK/runtime environment as described by the backend
recipe. No observer IDs, scopes or edits inside the kernel are needed. Open
`my-profile/report/index.html`, then **Source-linked internal dynamic records**.
The source snapshot, internal position, invocation, observer, program, visits
and exactness are available together. Omitting `--detail auto` selects native
collection and does not request these internal records.

## Interpreting the supported service

The default records visits to selected source-control positions. It does not
provide operation durations, per-iteration event intervals, productive memory
transactions or hardware-engine busy time. Counts are associated with actual
compiled specializations and retained observer identities. Compiler structure
and dependencies remain static evidence unless a measured association is
explicitly verified. Unknown clock frames are not aligned into a timeline.

Automatic selection is bounded; unselected sites are not evidence of
non-execution. Ascend physical v3 aligns actor banks independently. Legacy
physical v1/v2 captures remain readable with unknown visibility loss and
inexact counts; zero is not proof of non-execution for those formats.

The supported quickstart is eager Triton launches through the matching compiler.
Graph capture and simultaneous host-thread JIT calls are explicitly rejected
for automatic internal collection. Independent processes and explicitly chosen
advanced modes have separate contracts. See the automatic guide for capacity,
timeouts, cancellation, loss and API limitations. This checkpoint is not a
claim that arbitrary kernels, grid sizes, concurrency or compiler versions have
been exhaustively tested. NVIDIA device performance and overhead qualification
remain deferred.
