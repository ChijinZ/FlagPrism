# Physical shared-byte lifecycles in actual time-event details (r039)

The default NVIDIA late path now retains producer, commit, first covering wait,
first publication, consumer and physical-byte reuse associations. Selected
canonical events and standard Perfetto slice details carry these facts through
`coverage["nvidia.dynamic_dependencies"]`. These are conditional collective byte
relationships. This milestone does not align observers, generate time flows,
measure source costs or infer hardware-engine busy intervals.

## Actual installation and original evidence

- Docker `chijin-study-pro6000`, RTX PRO 6000 SM120, GPU0.
- Installed Python `/workspace/chijin-timeline-r039/runs/install-public-v2/output/venv/bin/python`.
- Wheel SHA256 `1a3db2df7cd549d892a1d220f1fdcaf5f0f08a76b4e7b52e77e489a0c28334bd`;
  all 615 installed archive members verified. Core ABI3 and the standalone
  recorder have unchanged sources/executable and explicit reuse bridges.
  This is a real component wheel update, not a new native compilation.
- Archive `artifacts/timeline/run-039/preflight/lifecycle-evidence-v1.tgz`:
  109,802,032 bytes, SHA256 `51cc64a7e9f30154aa90b1b531923d21c6160132485717ecc2e3864848ea573c`.
  All 7,627 retained file hashes were verified (7,630 members). Its 160 distinct
  recorded NVIDIA process identities were inactive at collection.

`verification.json` binds actual installed inputs to current sources and keeps
full lifecycle/recovery/offline/UI results and explicit remaining qualifications.
Formatting of final prose/evidence is a separate server-Docker operation. No
product code was edited after the final installed tests.

## Lifecycle semantics and fixes

Model `nvidia.late.shared_byte_lifecycle.v2` consumes the full recorded CTA before
view selection. Each generation has actual native ordinals, an exact aggregate
AS3 offset/length footprint, and its first completion/publication observations.
Each submission has its own footprint; `generation_shared_ranges` explicitly
names the aggregate when several submissions form one group. IDs are local to
the actual invocation/program, not globally unique hardware token names or
assumed fixed buffer slots. Completion means a recorded wait/barrier return,
not the engine's unknown physical completion instant.

Two correctness cases are covered by explicit CPU fixtures: partial overwrites
count current byte owners (two plus two bytes, rather than six historical
bytes), and a later unrelated barrier cannot replace first publication.
A further two-submit fixture checks separate ranges `[0,16]` and `[16,16]`
against the aggregate `[0,32]`. Fixtures do not substitute for device positives.

The final installed actual runtime-K GEMM captures identify 24/40 generations,
26/42 reuse edges and 352/640 annotated time events. Normal and optimized tests
check first covering native wait operands, publication order, physical ranges,
raw-ordinal/program attribution and unchanged originals. They preserve the
unqualified precision/epoch/time-flow flags.

## Actual checks

The final independent installation exited zero in 135.400 seconds. Default API
math/streams/warm-session checks (13 captures), runtime-K GEMM math (two full-CTA
captures), and actual compile/derive/copy-fault recovery all passed. Normal and
optimized shared regressions each passed 81 tests and two subtests. Late native
wait control, seven async-model negatives and whole-raw/view corruption checks
also passed in both modes. Public/normal/optimized GPU-hidden offline reexport
reproduced all 16 current traces byte for byte, without replay or changed inputs.

`runs/installed-views-v3/output/` retains 32 actual traces: two final fresh
captures and two r038 captures upgraded through the current installed public
offline command. All passed actual TP SQL/protobuf checks. Standard Perfetto
v57.2-da1d152cf with Chromium 140.0.7339.16 opened six distinct traces across all
four actual calls, selected events with lifecycle coverage, and read their
source/raw/quality/lifecycle details. Original private source trees (176 files)
and copied post-upgrade inputs (229 files) were unchanged by SQL/UI checks.
The local engineering preview contains `actual-lifecycle.pftrace` and actual
screenshots under `artifacts/timeline/run-039/preview/`.

The historical original source still matches every r038 archived file. Public
upgrade changes only the copied derived `index.html` navigation among previously
existing files; the root audit checks that both old and new committed trace
links remain. Historical raw, canonical events, views and trace bytes are kept.
This expected navigation refresh is distinct from immutable original evidence.

## Retained failure history and limits

The first source probe reached actual captures but failed because the CPU
fixture omitted `site_id`; the fixture was corrected. The first installed
version passed, then the per-submission/aggregate distinction was clarified and
verified in the final second installation. Both versions remain archived.

Initial UI attempts exposed an insufficient two-call manifest, asynchronous
track attachment, and a legacy selected-slice positive-width assumption.
No invocation was silently dropped and no timestamp stretched. The four-call
manifest remains required. A requested lifecycle slice may legitimately be zero
width, while every displayed trace must still contain a real positive internal
interval. The old K96 call has zero-width lifecycle intervals; the final UI
actually selects its real zero-width wait and retains its metadata. Earlier
failures, DOM/body text and screenshots remain. Successful final SQL/UI evidence
uses the final installation and exact current checker, not the preliminary UI.

Still required: broader native submit/publication/consumer boundary and record
value evidence, shared counter-domain/precision qualification, actual temporal
flows, full Ascend/GCU implementation, independent six-new-math qualification,
controlled cases and three fresh specified final code reviewers. NVIDIA device
throughput/overhead certification remains deferred. No paper or Study was edited.
