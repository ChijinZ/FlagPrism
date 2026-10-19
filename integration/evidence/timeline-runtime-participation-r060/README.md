# R060: device-published Ascend participant cardinality

The default Ascend recorder now distinguishes reserved ABI slots from participants using a real device getter. Production changes are f0bb81a and the legacy-output compatibility delta in 6a1bdc3. The follow-on 1f34bb5 changes only a test assertion. No paper/Study files changed.

## Protocol

The optional exact `runtime_participation` manifest feature binds header word 7, shift 8 and the actual AIV `llvm.hivm.GET.SUBBLOCKDIM` SSA (AIC uses constant one). Low flag bits, 64-byte headers/pairs and three reserved segments are unchanged. The decoder validates publisher versions, counts, flags and agreement. Only a published count of one plus a completely zero second AIV segment excludes slot 2. Missing expected publishers stay incomplete; old logs without the feature retain their original canonical result and unknown slots.

## Actual current-device checks

Existing C1 recurrence and C2 BK32 matrix multiplication each executed once ordinary and once profiled in `chijin_v3.5.x`, NPU 4. Device task terminal 0, 61.711 seconds; controller/worker are missing after completion. All four mathematical calls passed values, input preservation, four-element output tail and state exactly once. Actual 128-byte allocation guards and raw timestamp offsets passed.

| Current capture | Header flags per selected program | Actual participants | Events | Counter-ns exports |
| --- | --- | ---: | ---: | ---: |
| C1 vector | AIV slot 1: 257 (count one) | 2 across first/last programs | 36 | 2 |
| C2 mixed | AIC: 257, AIV slots 1/2: 513/513 (count two) | 6 across first/last programs | 160 | 6 |

Both captures are complete. `ascend-positive-source-audit-v1.json` independently records five/seven distinct source-fragment sites with actual positive events, excluding native-control sites. Reviewer feedback tightened the test to this condition in 1f34bb5. The original device run used the earlier assertion; the stronger condition was checked afterward on the same original canonical data, without replay.

Actual installed Python: `/tmp/chijin-timeline-r060-ascend/runs/participation-install-v2/output/venv/bin/python`. Wheel SHA `5a66bba9115e82b48e549ea3d3882582ac63bd8c10ceb9e71d2fff12289d3ee9`, 437 installed members checked. Normally rebuilt plugin SHA `250859a51115125249b926a84967ad274ffee67b0b287c0dc7c5a381d0bbed1f`. The new plugin was built by its normal CMake target; unchanged core/native runtime/SDK objects were matched and reused. Four actual opt debug/no-debug AIC/AIV checks passed. New getter codegen used retained actual SDK arguments; the modified getter-probe kernel was never executed. The first unsupported device `-S` probe remains a recorded failure; normal object codegen succeeded. SDK sources and private mathematical snapshots are not included here.

## Focused regressions and standard trace import

- Container CPU contract tests: normal and `-O` each 49 pass; formatter fixed point and Python AST preservation. Fixtures are explicitly synthetic, separate from actual device results.
- Actual retained logs: normal and `-O` preserve the old vector/mixed canonical objects exactly and leave all 31/32 original files unchanged. New vector/mixed retained files likewise stay unchanged. Raising expected cardinality or removing an expected publisher produces incomplete data; dirty excluded slots or inconsistent counts are rejected. No application replay or device access in these checks.
- Actual pinned Trace Processor: all eight new counter traces and two native dependency traces pass raw/proof/protobuf/SQL checks. Both dependency traces have 18/24 actual flows. Each result retains 263 importer-stat rows, with no positive error/data_loss. `trace-index.json` links all ten trace/view/raw/canonical/proof inputs to sealed hashes and exact result SHA/row. Tool/protobuf environment and verifier hashes are unchanged from R059.

Original bundles remain in the Ascend Docker at `/tmp/chijin-timeline-r060-ascend/runs/participation-device-v1/output/device/{vector,mixed}/capture`. Open the exact `.pftrace` named in each recorded `counter_ns_exports` entry; the record includes its SHA. SQL input blobs remain on the NVIDIA tools container under `/workspace/chijin-timeline-r060-nvidia/runs/participation-tp-v1/output/inputs/`. The actual source-byte input archive is retained locally at `artifacts/timeline/run-060/preflight/ascend-participation-tp-inputs-v1.tgz`, 315226 bytes, SHA `c017d82e9b2201b0cb5940349db0f0d04ffc6519ceb01fc8ab09679a842369eb`.

The attached small receipt archives contain authoritative launches/terminals, build/install source hashes, actual results, CPU logs/formatter outputs and full SQL/stats. `summary.json` gives their individual SHA/size. Runners are retained for reproduction. First failures are kept separately; none is relabeled successful.

## Scope

These two current execution forms establish the new participant mechanism. They do not update the historical 96-capture matrix, certify arbitrary targets or turn empty legacy slots into proof. They do not close final source/loop boundaries or ordinary/sparse/default scheduling. Counter brackets are not source-exclusive cost or engine activity. Existing UI evidence is reused; this change did not run another browser matrix. NVIDIA performance remains deferred.
