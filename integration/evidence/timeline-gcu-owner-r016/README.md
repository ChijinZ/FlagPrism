# GCU compact producer and deferred public timeline: r016

This is an engineering raw-capture milestone, **not P01 or full timeline completion**. No paper/Study files were changed. All imports, builds, CPU tests, GPU math and CLI runs took place in existing Docker `flagprism-enflame-dev` on `zhiyuan_suiyuan`.

## Source and installation

- New native build: `789757f3725f72f8be3e348a2e52552d3356c99b`, `/workspace/chijin-timeline-r016/native-v6`. Seven changed TUs actually compiled, 358 objects reused only after input-byte checks, six links, native Runtime/Metadata/Frontend tests passed. Runtime/storage and publisher versions both 2.
- Installed product: `ea70da7d5909a1ffe73a58340e98c95875fa33e2`, venv `/workspace/chijin-timeline-r016/runs/install-v5/output/venv`. Native-source bridge checks equality with the native build; Python came from the separately frozen Git archive. Wheel SHA `dde171bb115abe7e449209e53ce0c240e1181d9a45374289ff6c3587210cf20e`. Independent recheck verified all **450** installed wheel members in its triton/flagtree scope and actual native flags `[2,2,2,2]`.
- Current unit correction `794a5f6` and additional ordinary CLI/recovery tests `c4fc1e7` change tests only; they do not silently patch installed product code.
- General source build/installation remains [the Enflame recipe](../../patches/enflame/README.md). A current compiler/runtime pair is required; old beta publisher metadata cannot use the new compact allocator.

## What actually ran

| Path | Evidence | Outcome and scope |
| --- | --- | --- |
| Explicit physical producer | [original byte audit](original-byte-audit.json) | Three complete captures, same binary, grids 3×2 / 2×2 / 1×1, runtime K3/7/11; real events per observer 10/14/18. Fourth cap4 capture honestly drops 56 endpoint references; both actual writers present |
| Standard advanced export, no custom prepare | Original archive; terminal default-export-v2 | 28 intervals/56 exact endpoint references and canonical data survive final standard bundle writing; legacy per-launch sync still applies to this separate advanced mode |
| Common ownership/readback and GCU policy CPU contracts | [installed recheck](installed-cpu-result.json), normal/optimized logs | Each mode passes 11 legacy GCU + 11 first/last + 16 common raw + 5 GCU deferred-policy + 27 owner/finalization tests: **70 per mode**. Fixtures are not device qualification |
| Public default API | [API result](public-api-result.json) | Cold/warm sessions, six actual ordinary calls; three independent owners submitted before any collector query/read, no per-launch global wait; same binary across K/grid and warm session |
| Public default CLI | [CLI result](public-cli-result.json) | Three actual calls through standard `--detail timeline --backend enflame --device 0`, ordinary script unchanged by profiler scopes |
| Two actual GCU streams and first decoder failure | [recovery result](owner-recovery-result.json) | Three originals persisted and safe owners released before derived work; other two decode despite first failure; retry preserves SHA/history with zero device transport actions, next normal session one call succeeds |

The default-path byte audit checks **13 captures, 576 physical endpoint references and 288 intervals** across API, CLI, recovered originals and the following legal session. It detects cross-invocation ID collisions and checks every tick at its exact raw u64 offset; see [public byte audit](public-owner-byte-audit.json). This workstation audit uses only stdlib bytes, without product imports, device access or math replay.

## Failures preserved

Native v1 failed for missing stdexcept; v2 for AddPtr builder result type; v3 for an object/depfile directory. v4/v5 compiled, but their first/last beta address was unsafe: an i32 pointer received a byte stride. Prototype-v2's terminal success only checked host-declared coordinates, so its dual-writer conclusion was withdrawn. Standard advanced export then exposed a real empty last ring and dropped canonical field. No old beta capture is counted as proof of the corrected producer.

Publisher2 uses element-correct stride, actual writer-arrival flag and strict cache/native checks. Real producer-v3 requires actual events for every selected observer; standard output now preserves/binds canonical to raw. Initial install-v1 also exposed a CANN mismatch unit expecting abort instead of the intended pre-SDK invalid_argument; the source/negative contract was fixed and full native tests rerun.

Install-v5's first CPU pass failed because the new test used a dict where debugger launch preparation expects the actual compiler metadata object shape. Test-only correction 794a5f6 uses SimpleNamespace. The install terminal remains failure; separate cpu-v5-recheck terminal and result prove all corrected tests and installed bytes without replacing that history or modifying installed Python.

## Original artifacts and reproduction

Large originals stay outside Git:

- `artifacts/timeline/run-016/preflight/gcu-first-last-original-evidence-v2.tgz`: 18,393,566 bytes, 1,605 members; SHA `5e2e5d0421b2b4752b732b114f0d813f00b9e25803a8de8a0c2c94353dc45e31`. Includes native build-input audits/logs, earlier failures and corrected producer/standard advanced raw.
- `artifacts/timeline/run-016/preflight/gcu-owner-original-evidence.tgz`: 10,321,088 bytes, 280 members; SHA `8eab98f1b755e7b0df60d77498dba1366700e8bdfee7fd15e5788608b30e7ec7`. Includes actual default bundles, CPU/install logs, recovered originals and selected task process checks (964 declared identities, all missing/reused/zombie rather than live).

`audit_originals.py` and `audit_public_owners.py` reproduce stdlib byte audits against these archives. Exact launch/check/transfer scripts and immutable Git archives remain under `artifacts/timeline/run-016/preflight/`; execution went through `scripts/study_remote.py`, never printing credentials. All accepted jobs have actual terminal receipts and missing worker/controller checks. No owned device job is left by these runs. Selected checks are not an audit of other users' processes or other machines.

The actual installed CLI entry is:

```bash
/workspace/chijin-timeline-r016/runs/install-v5/output/venv/bin/python -I \
  -m flagtree.profiler.cli --detail timeline --backend enflame --device 0 \
  -n /workspace/chijin-timeline-manual \
  /workspace/chijin-timeline-r016/extra-tests-input/ordinary_enflame_timeline_workload.py \
  --evidence /workspace/chijin-timeline-manual-math
```

Run it inside the existing Docker, with `FLAGTREE_BACKEND=enflame TORCH_DEVICE_BACKEND_AUTOLOAD=0`, and choose fresh output paths. Inspect `<bundle>/timeline/index.json` and its capture/raw/events references. The API equivalent is `start(path, detail="timeline", backend="enflame")`, normal kernel calls, then `finalize(session)`.

## Still incomplete

No certified ns/epoch, final source-region boundary, GCU timeline-allocation guard, true async mechanism/two-generation reuse, standard `.pftrace`, Trace Processor or actual UI qualification follows from these raw captures. The recovery demonstrated here retains the hook in-process; a standalone public cross-process recovery command is not delivered. NVIDIA still needs affected actual regression/installation and its machine-boundary/clock/perturbation work; Ascend needs its new timeline producer. Independent six new math and the three additional final code reviewers remain required. The design reviewers from r8 are not those final reviewers.
