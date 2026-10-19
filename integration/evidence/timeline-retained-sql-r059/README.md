# R059 retained-trace SQL audit

This is a CPU-only import of existing real captures in the existing NVIDIA Docker. No application was replayed, no GPU/NPU kernel was launched, and no original capture qualification was changed.

| Backend | Counter traces | Dependency traces | Passed / registered |
| --- | ---: | ---: | ---: |
| NVIDIA | 944 | 0 | 944 / 944 |
| Enflame | 218 | 194 | 412 / 412 |
| Ascend | 336 | 48 | 384 / 384 |

The 1,740 registered traces have actual pinned Trace Processor results: 1,735 fresh imports and five exact-input smoke-result reuses. The smoke run also executed normal and optimized Python modes and rejected bad trace SHA inputs in both modes. Actual counter endpoints are checked against retained raw words, rational ns conversion, protobuf and SQL slices. Dependency checks use the retained dynamic view and its raw/canonical/proof files, checking actual flow endpoints. Full importer stats, including zero-valued errors, are retained; no positive error/data_loss was found.

`trace-index.json.gz` is a JSON array with one row per registered trace. Each row records original capture path/SHA, actual registered view, individually sealed verifier inputs, exact-input proof key, verifier-result path/SHA/row, and stats count. `summary.json` retains each authoritative controller terminal, denominator, source SHA and aggregate. `TP-environment-v1.json` identifies the actual tool and protobuf package. Product runtime freeze is 46c23c65fced45e7afb22412a08953a40fc71fe2; verifier changes are in 27abfe9.

Full receipts (1,762 regular files, including all per-trace SQL/stats results) are retained at `/workspace/chijin-timeline-r059-nvidia/audit-receipts-v1/receipts.tgz` in Docker `chijin-study-pro6000`, and locally at `artifacts/timeline/run-059/preflight/receipts.tgz`. Size 6,852,305 bytes; SHA-256 `d52653b3ab7c4183fd0875fab4a2ad97a3aebc5281e4adeff3da9db3cb9efe51`. The downloaded archive's size/SHA were verified before safe regular-file-only extraction. Large original raw/trace blobs remain on their recorded servers; they are not copied into Git.

For audit without replay: unpack the receipt archive, resolve each indexed result path relative to `/workspace/chijin-timeline-r059-nvidia`, verify its SHA, then inspect the indexed `checks` row. The compressed index's input hashes reconstruct `proof_key` with the exact algorithm in the retained runner. Re-executing a verifier is optional; its original sealed input manifest and pinned tool are needed.

## Limits retained

Successful import does not establish default completeness, final source-region boundaries, unperturbed scheduling, physical engine activity, current-provider dependency qualification, UI usability, or performance. Historical unavailable/overflow/partial failures remain failures. In particular, NVIDIA's original q04 missing-ns outputs are not relabeled: their 96 retained repaired traces were separately reused. Historical Ascend dependency traces are not promoted to current-provider recommendations by this audit. UI receipts already collected are reused without a new browser matrix.

## Ascend topology investigation

The attached 96-capture histogram is read-only evidence: 60 pure-vector captures (task type 10, mode aiv) have slot 1 populated and slot 2 unknown; 36 mixed captures (task type 32, mode mix) populate slots 0, 1 and 2. Actual loader source selects AIVEC binary registration for aiv. This supports investigating the distinction between reserved ABI slots and expected participating actors; it does not itself authorize ignoring empty slots. No decoder/completeness policy changed here.

`ascend-coordinate-scope-v3.json` limits SSA definitions to the exact manifest entry function. Earlier exploratory v2 closures incorrectly mixed same-named SSA values from different functions and must not be used as proof. The public metadata-view loader rejection in the first exploratory command was a wrong helper path, not a product failure. The source extracts and histogram do not establish final machine-code scheduling or exact source cost.
