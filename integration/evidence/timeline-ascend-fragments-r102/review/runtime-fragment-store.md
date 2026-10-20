# R102 finite runtime review: automatic/offline Ascend fragment storage

Requested reviewer configuration: GPT-6.1-Sol / xhigh; actual resolved configuration unknown. Reviewed freeze: `00d810450e92f827b9205b434f26865ac0bfaa76`, Git verified. Store SHA: `421cd6319964bb6700339bfe68525775b66934712fa20e874b0e14d9b8cd86bd`.

Scope: `timeline_ascend_fragment_store.py`, its new collector/offline calls, optional wheel packaging of the actor indexer, and `p01_ascend_fragment_capture.py`. The fragment-operation rules themselves were not re-reviewed, and no compiler review/report was read. This was local read-only source/Git/JSON/SHA work plus writing this report; no product import, tests/checkers, SSH, SDK/device, mathematics, SQL or UI execution was performed.

## Confirmed findings

**M1 — Major: the header's tool digest is not bound to the reader that executed.**

- Location: `inspect_capture_fragments` in `timeline_ascend_fragment_store.py`, from packaged tool selection through the final `tool_sha256=sha256(tool.read_bytes())` header construction.
- Trigger: the packaged reader is replaced between the original/adapted invocations, or after an invocation finishes but before the final digest read. The routine does not snapshot a digest before execution or compare it afterward.
- Evidence: `_run` is called through the selected path for each input; only after all outputs are produced does the new caller read that path's current bytes for the header. The existing `_run` lifecycle logic is not a tool fingerprint check and is not being reopened here.
- Consequence: an input closure can claim a new reader SHA for output produced by a different reader, while all retained source/graph hashes still pass. This defeats the new header's advertised tool provenance even though raw capture integrity is unaffected.
- Minimum correction/verification: capture the expected reader digest before the first invocation and ensure it stays unchanged across execution/publication, then write that expected identity into the header. On change, return optional unavailable without publishing `inputs.json`. A narrow CPU fault replacing the reader during a mocked stage is sufficient; no SDK or mathematics replay is needed.

**M2 — Major: a non-object JSON reader result escapes optional failure isolation.**

- Location: `inspect_capture_fragments`, immediately after `graph = json.loads(graph_raw)`, before `graph.get('input_sha256')`.
- Trigger: a reader exits 0 but produces syntactically valid JSON `[]`, `null` or a string.
- Evidence: there is no dict check before `.get`; these cases raise `AttributeError`. The function's exception handler catches parsing/value/OS/type/key/Unicode/recursion/subprocess errors, but not this attribute failure. The collector calls this optional function before its regular counter/dependency exports, without a surrounding optional catch.
- Consequence: malformed diagnostic output can escape the new optional stage and interrupt subsequent timeline finalization/export, rather than leaving an explicit `fragment_paths_unavailable` result. Retained raw may remain intact; that does not establish failure isolation.
- Minimum correction/verification: validate the top-level result as a dict before accessing it. The three non-object JSON cases should return unavailable and preserve raw/capture inputs. This needs only a CPU reader-output fault fixture.

No other confirmed defect is identified in this finite review. Both findings were sent to root before report completion. The fragment helper's unimplemented whole/native/clock/value-equivalence rights are not treated as false success.

## Reviewed positive behavior

The new stage runs after canonical raw decoding; it does not change recorder allocation, readback, event endpoints or existing publication. It reuses the previously reviewed owned-child `_run` implementation, including exclusive output files, the remaining-deadline/per-call 20-second bound, 32 MiB output check and bounded cleanup/reap. No new child implementation was introduced or requested for revalidation.

The original/adapted actor inputs are checked against compiler metadata, retained immutably with `persist` under `export_lock`, and each graph's input SHA is checked before header publication. Only after every stage succeeds is the header persisted. Loading that header checks the binary/compiler identity, artifact count and source/graph digests, and recomputes current fragment facts rather than trusting saved analysis status. The derived report includes current rule digests and remains explicitly unqualified for native scheduling and source-value equivalence.

Offline `load_fragment_paths` reads retained input/header/graph artifacts and invokes pure rule functions; it does not call `_run`, Popen or an SDK. It checks retained original/adapted bytes against the capture's compiler closure and uses the explicit recorded actor trace role. The retain callback receives those input members. The offline wrapper converts its documented failures to an unavailable field without changing the existing counter/dependency results.

For repeated binary IDs, a completed header is reloaded with exact input checks. A differing compiler artifact set cannot silently reuse the old graphs. Concurrent/incomplete attempts cannot overwrite another reader's stdout because `_run` opens it exclusively; conflicting immutable source/header content also fails closed. An interruption that leaves stdout without a header will make a subsequent attempt unavailable instead of overwriting that diagnostic. I do not count that conservative retry behavior as a new mandatory gate in this review.

Wheel assembly can explicitly receive `--actor-structure-tool`, or use a sibling tool when present. Missing tool remains an optional-analysis case. The copied tool has a deterministic package path and is byte-checked in the wheel. This static packaging path is not proof that the current normal installation already contains/imports/executes it successfully.

## Evidence and verification gaps

Read `preflight/phase-receipts-v1/phase-index-v1.json`; all 123 indexed files match local size/SHA. The format result identifies the store SHA above, collector SHA `3e35cd735d4d0027ca35a4a705ca04d98557b952f28852d252085b3dc92cb3fa`, offline SHA `8f835169ad2a546e720ec8307350c2229f2f741c277d32a5c89d1c5cd6b0da86`, wheel script SHA `cabb6a4b9bc53d712ca12c3839ca164ba3a6442ffe2511cf8e95201138af917b`, and capture-test SHA `d79f81026abda0954b11131f0273695baf890d3a9482df35fe87abf2566261ae`.

These phase receipts concern helper/source QA; they are not substituted for normal store installation. The supplied retained-capture test covers an installed direct default analysis call, offline recomputation with Popen forbidden, cached-status refusal, graph corruption and compiler-hash mismatch, plus raw preservation. At this report's creation the matching installation's terminal evidence had not arrived, and its successful path would not by itself cover M1/M2.

Minimum remaining work is the two narrow faults/corrections above and the already planned matching installed retained-capture/packaging evidence. No new SDK/math/SQL/UI matrix or complete operation/SSA/native proof is requested. Optional expansion: none. Whole-goal and complete writer/source/clock/native qualification remain open outside this delta's claim.

## Matching M1/M2 closure addendum

M1 and M2 are now closed for this finite store/integration review. This addendum supersedes their open status at `00d8104`; the original findings and the distinction between helper QA and store installation remain preserved.

Corrected freeze: `51f90cb0310207ce3dc7ffb1040dc4ae7e8aa474`, Git verified. Exact store SHA is `eb4f458add33662583f3db2fb6a7018409ef52e1c9b1709fc990209d8329b15e`; capture-test SHA is `4c21a54d0d03eb1f5027d18b3eaaa2e81668cb4512300a6913739a6d2bbc7ccd`. Both local files are byte-identical to the recovered formatted source copies in `phase-receipts-v3/format-input-v2/source/`. The later untracked evidence directory is not represented as a product change.

**M1 closure.** The store captures the reader digest before its first execution, checks that expected digest immediately before and after each original/adapted `_run`, and publishes only the frozen digest. A mismatch raises the existing optional-stage error before `inputs.json` publication. The new fault executes one actual packaged reader stage, then mocks only the bytes returned by `Path.read_bytes` for the tool. It does not alter the installed tool. The post-stage mismatch returns `fragment_paths_unavailable`, publishes no header and preserves raw bytes. This covers the reported provenance gap without reopening the owned-child implementation or demanding a general filesystem adversary proof.

**M2 closure.** A `type(graph) is dict` check now precedes `.get`. The `[]`, `null` and string faults each take the documented unavailable path, leave `inputs.json` absent and preserve raw. The top-level attribute exception can no longer escape for these valid non-object JSON outputs.

Read `phase-receipts-v3/phase-index-v3.json`: all 32 indexed files match local size/SHA. `runs/install-v2/terminal.json` is terminal 0 / 71.631539158 seconds. Its exact installer script SHA is `4b48ba2600554f429d8d989f9a6bd8502738be79e2778c485ee9afdd79df9df5`; I read its wheel-member comparison and installed-test invocations. The result binds the corrected source commit, 449 installed members compared byte-for-byte with the wheel, wheel SHA `1fe73f7d44a7f72b1afcbe7d33416cc56f20f4917d0f3dee5da6e4b6e92c1e96`, and packaged reader SHA `d0e82b1fdc5fc322c322bc80c44a9e5e552afc5918174e2ba0f9504cc7a99d61`. All ten installer steps return 0.

The matching normal and optimized retained-capture tests both report automatic analysis 11/15, nine retained input-closure members, offline reconstruction with Popen forbidden, ignored cached success, altered-graph refusal, changed-compiler refusal, and raw unchanged. Both modes also include all four new fault cases with the expected unavailable reasons and the explicit no-header/raw checks in the inspected test source. This is exact installed store evidence on a real retained capture clone, not merely the earlier helper QA or a new application/device replay.

No additional confirmed issue or necessary verification gap remains for M1/M2 and this matching installation gate. The separately reported new public CLI run is not used as closure evidence here because its complete archive was not yet supplied to this addendum. That does not add a new requirement to these two defects. No product/tests, SDK/device, mathematics, SQL/UI or old helper matrix were executed by this reviewer. Whole/current-96, native/SSA/value-equivalence and loop qualification are not granted by this bounded closure.

## Subsequent public collector integration receipt

The public archive is now available and was read independently of any compiler review. `preflight/public-receipts-v1/public-index-v1.json` has 152 entries, all matching local size/SHA. The `public-q05-v1` controller is terminal 0 / 48.186708919 seconds; its application terminal is also 0 and records one invocation of the public CLI through the same install-v2 Python at source `51f90cb`. This is the already completed user application run, not a new execution requested or performed by this reviewer.

The retained expanded capture is `raw_complete`, with raw size 786,816 bytes and SHA `8bc1d954e65efd2d3a2d03e53f6fe0f3d2ddfe6b11cc052b502a543b1572941c`; the recorded bundle size is 7,243,351 bytes. Its new binary identity is `b28e6765ebf515bc285a57fe813b4fc035f0b0649fa7327e6f96c85fd6171b8f`. No cache-hit or identity equivalence with the earlier retained clone is claimed.

The actual collector-written `source_fragment_paths` is recomputed 11/15 with native/value-equivalence fields false. Its retained header binds packaged reader `d0e82b1fdc5fc322c322bc80c44a9e5e552afc5918174e2ba0f9504cc7a99d61`; all four original/adapted child receipts are terminal 0. Six existing `counter_ns_exports` remain present with the documented counter-unit-only/unverified-precision status. The math/result files retain zero max absolute error, input immutability, guard success and the host-once success for this single application call.

This supplies direct public automatic-hook evidence in addition to the installed clone/offline/fault coverage above. It does not alter the M1/M2 closure or grant SSA/body equivalence, loop/native/clock precision, current-96 or whole-goal qualification. No further necessary item is identified within this finite store review.
