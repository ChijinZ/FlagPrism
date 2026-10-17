# Full-width timeline record checkpoint — T007

**Partial engineering checkpoint, not a full P01 or goal pass.** All builds, installation, CPU tests and real math ran in the existing NVIDIA Docker `chijin-study-pro6000`; the workstation only orchestrated, edited, used Git and audited retained bytes. No paper/old Study changes or NVIDIA performance/overhead certification.

## What changed and actually ran

- Native `a6f7b4c` adds an explicit timeline-v2 16-byte record: tag, full uint64 timer, absolute sequence, distinct magic, saturating index, single writer per warp counter and full four-word finalization copy. Old non-timeline encoding remains unchanged. Logger-only tail CTA barrier is not added in v2; this is not a proof that all ordinary/observed schedules are equivalent.
- Product `timeline_nvidia.py` independently decodes physical layout into raw records, preserves all offsets and loss, rejects bad versions/sequences/sites/timer regression; it does not certify clock units, epoch or flows. Its 27 CPU contract cases pass normal Python and `-O` in Docker. Source initially staged for CPU checking is the same decoder subsequently included and byte-verified in the fixed wheel.
- The first real unannotated recurrence run failed at runtime K11: the inherited occupancy heuristic silently reduced an explicit 32768-byte buffer to 2048 bytes. Every warp wrote 36 events into a capacity of 32. The original failure/archive remains; root independently decoded it. K3/K7 verified 384 records, but K11 was not called a mathematical/profile success and no later GEMM was executed in that failed run.
- Generic fix `7898549` honors explicit timeline capacity within the target shared-memory bound and rejects excess; legacy occupancy behavior remains unchanged. It was actually rebuilt (127 steps), freshly installed (599 wheel members byte-verified), checked with normal/optimized native smoke including excess-capacity and clock32 negatives.
- Fixed actual math test `62853ce` uses the installed product decoder. It explicitly requests five ordinary and five automatically instrumented calls: recurrence K3/7/11 with the same instrumented binary and two ordinary GEMM stages variants. No kernel profiling annotations. Math, inputs, tail/state checks pass. Its State stores check participation, not an independent replay counter. This test collector explicitly synchronizes owned probe calls; it is not production deferred-owner implementation or host-once qualification.
- Root read the retained raw bytes independently, verified all 1024 records, both raw endpoints of 512 pairs and 30 compiler artifacts. Each recurrence observer/site shows actual 3/7/11 occurrences. Actual first/last requested programs are present and unselected allocation slots remain unwritten. Allocations are still full-grid, not compact-first/last production admission.

## Important unfinished work

The real GEMM inventories show **all async copy/commit/wait candidates excluded** by the old bounded source selection policy. `next-async-planner-gap.json` records this concrete gap. The next compiler change must preserve the relevant complete async boundary set plus its actual mechanism facts, independently of the logical source-region budget. No dynamic flow is claimed here.

Public automatic `detail=timeline`, invocation-owned deferred runtime, final instruction/SSA boundary certificate, target clock/epoch proof, async group/generation and Perfetto/SQL/UI remain unfinished. GCU/Ascend new full paths, independent six-new-math qualification and three final additional GPT-6.1-Sol/xhigh code reviews remain required. No backend has completed overall P01.

## Evidence and identities

- Fixed native source: `78985495e41cbd70db06596979b4c497b12b21d6`.
- Fixed wheel SHA: `088a83bd48754734849e2d803fd48d0d227493ff042251f8d690f5816a899208`.
- Installed venv: `/workspace/chijin-timeline-r002/runs/native-install-v2/output/venv`.
- Server raw/IR/receipts: `/workspace/chijin-timeline-r002/runs/device-record-v2` and `native-7898549`.
- Workstation original archives: `artifacts/timeline/run-002/preflight/record-v1-original-evidence.tgz` and `record-v2-original-evidence.tgz` relative to the workspace root. Their archive hashes are retained below; large binaries/venv and SDK-private files are not committed.
- These JSON receipts are intentionally small. Full raw bytes, per-artifact hashes and failures remain in the original archives. An audit summary or PTX string count alone is not a unit/epoch, pure-arithmetic placement or async semantics certificate.
