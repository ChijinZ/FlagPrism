# Internal timeline handoff

The product behavior is frozen at `6e78f136214da74254211fa19b90a3f7b7353fa2`.
Subsequent commits add evidence and correct public application examples; they
do not change runtime/native timing. The current acceptance reports accompany
this directory. Raw reports with conservative qualification fields are retained
unchanged; scoped sidecars, not rewritten historical raw, record later audits.

## Run your ordinary application

Use these already installed matching environments inside the existing server
Docker. Keep SDK activation/import order from your normal development setup.
Replace `/path/to/my_script.py` with your ordinary launch script, and select
the same logical device in the script. The script needs no manual timeline
scopes, operation IDs or scratch parameters.

| SSH alias | Existing Docker | Matching installed Python |
| --- | --- | --- |
| `zhangquan_pro6000` | `chijin-study-pro6000` | `/workspace/chijin-timeline-r077-nvidia/runs/native-install-v3/output/venv/bin/python` |
| `zhiyuan_suiyuan` | `flagprism-enflame-dev` | `/tmp/chijin-timeline-r098-gcu/runs/normal-install-v3/output/venv/bin/python` |
| `zhiyuan_ascend` | `chijin_v3.5.x` (Docker as chijin) | `/tmp/chijin-timeline-r105-ascend/runs/install-v1/output/venv/bin/python` |

```bash
# In the NVIDIA Docker; leave FLAGTREE_BACKEND unset.
/workspace/chijin-timeline-r077-nvidia/runs/native-install-v3/output/venv/bin/python \
  -m flagtree.profiler.cli --backend cupti --device 0 --detail timeline \
  -n /tmp/my-nvidia-timeline /path/to/my_script.py

# In the Enflame Docker, with its normal SDK environment.
FLAGTREE_BACKEND=enflame /tmp/chijin-timeline-r098-gcu/runs/normal-install-v3/output/venv/bin/python \
  -m flagtree.profiler.cli --backend enflame --device 0 --detail timeline \
  -n /tmp/my-gcu-timeline /path/to/my_script.py

# In the Ascend Docker; import torch_npu before Triton in the application.
FLAGTREE_BACKEND=ascend /tmp/chijin-timeline-r105-ascend/runs/install-v1/output/venv/bin/python \
  -m flagtree.profiler.cli --backend cann --device 4 --detail timeline \
  -n /tmp/my-ascend-timeline /path/to/my_script.py
```

Open the resulting `timeline/index.html`, choose a standard `.pftrace`, and
open it in Perfetto. For source builds, normal wheel installation, diagnostics,
API, offline export and backend-specific native tools, use
[the quickstart](../../../Profiler/docs/timeline_quickstart.md), its three
integration links, and [the runtime reference](../../../Profiler/docs/timeline_runtime.md).
Replacing Python alone is not a native integration installation.

## Actual outputs and interpretation

Workspace root is `/home/jin-lab-pc/workspace/osdi_flagprism`.

- Convenient exact-byte copies of the six new q11 observer traces: root
  `artifacts/timeline/run-105/preview/` (each file is SHA-bound in its manifest).
  For example, `q11-observer-0-aic.pftrace` shows the actual matrix actor.
- New independent q11 traces: root
  `artifacts/timeline/run-105/preflight/phase-receipts-v1-recovered/runs/profile-q11-s0-c0-v1/output/cold/capture/timeline/derived/counter-ns/`.
  Each revision contains actual `traces/*.pftrace` and its matching `views/*.json`.
- All new q11/q12 traces remain in the Ascend Docker under
  `/tmp/chijin-timeline-r105-ascend/runs/profile-<combination>-v1/output/<cold|warm1|warm2>/capture/timeline/`.
  Use actual combinations `q11-s0-c0` through `q12-s1-c1`.
- Existing readable counter/dependency samples: root
  `artifacts/timeline/run-062/preflight/samples/ascend-case000-counter.pftrace`,
  `ascend-case000-dependency.pftrace`, and `ascend-case048-counter.pftrace`.
- Actual previously qualified Perfetto screenshots: root
  `artifacts/timeline/run-050/preflight/clock-view-data-v1/output/UI/1/details.png`,
  and `artifacts/timeline/run-048/preflight/view-output-v1/UI/0/overview.png`.
  These show their original captures; they are not screenshots of new q11/q12.
  The unchanged UI/export schema is reused rather than re-running browser tests.

The two controlled GCU examples in the runtime reference preserve their original
measurements: work 3/7/11 produces 3/7/11 repeated regions; matrix BK32/BK64
produces six/three internal brackets. See
`integration/evidence/timeline-independent-deltas-r056/` for provenance. They
explain repetition and staging, not a certified uninstrumented speedup.

## Validation and limits

The independent new matrix set has eight ordinary combinations and 24 profile
runs, all passed. The additional 144 standard traces passed the unchanged pinned
Trace Processor, exact raw/ns/event identity checks and complete importer stats.
All actual SQL, input manifests, verifier return codes and 263 stats per trace
are retained at root `artifacts/timeline/run-105/preflight/tp-receipts-v2/`.
The corresponding server receipts are in the NVIDIA Docker at
`/workspace/chijin-timeline-r105-nvidia/runs/new-matrix-tp-v1/`.
No device run or kernel/application replay is involved in these SQL imports.

A reproducible CPU-only SQL check of one retained input, using a new output
folder, is:

```bash
/workspace/chijin-timeline-r003/runs/perfetto-tools-offline-v1/output/venv/bin/python -I \
  /workspace/chijin-timeline-r059-nvidia/tools-smoke-input-v1/source/verify_perfetto_traces.py \
  --manifest /workspace/chijin-timeline-r105-nvidia/runs/new-matrix-tp-v1/output/000/manifest.json \
  --output /tmp/my-new-timeline-sql-check
```

Use scope from each capture: NVIDIA SM120 does not qualify other targets;
separate observer/domain files do not acquire a shared epoch from a zero origin;
issue/wait-return brackets are not hardware engine busy or exact completion;
instrumented elapsed is not source-exclusive cost or ordinary speedup. Real
loss/overflow stays visibly incomplete, and unsupported mechanisms retain a
reason. NVIDIA exclusive-load performance/overhead experiments remain deferred
at the user's request. Optional static fragment diagnostics may be unknown;
they do not replace actual raw/source timing or invent intervals.

First failures, subsequent generic fixes, historical partial coverage and
qualification boundaries remain in `record.snapshot.md` and the linked evidence.
No paper or Study file is changed by this implementation task.
