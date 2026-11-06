# Ascend explicit-capacity admission, 2026-11-06

Code: `db36d303`; collector wiring regression: `737cc444`.

The 16384-pair DSA baseline fits a single allocation, but split-attention partial and merge launches together exceeded the old 8 MiB pending-owner admission ceiling. Each maximum-size launch has six slots of `(64 + capacity * 64)` bytes plus 128 guard bytes. At capacity 16384 the two launches require 12,583,936 physical bytes.

The collector now scales the admission ceiling relative to its default 2048-pair physical geometry, only for explicit larger capacity requests. The unspecified default and smaller requests retain 8 MiB. At capacity 16384 the ceiling is 67,070,660 bytes; both old and enlarged policies admit ten maximum-size pending launches and reject the eleventh before allocation. This is a ceiling, not preallocation. Individual compiler, decoder, raw-storage and owner-count bounds remain in force.

The recovered Ascend installation also had an older mixin interface. Its deployment patch adds only the already-supported `max_pending_bytes` parameter and passes it to `TimelineOwnerPool`; unrelated installed code is unchanged. Backups and before/after SHA256 receipts are retained. The first real attempt exposed this installation mismatch and failed before profiler launch; it is not silently overwritten.

Installed verification: actual collector construction with capacity 16384 passed; 15 targeted tests passed, including default retention, admission boundaries, public capacity bounds and collector-to-pool wiring. The first test harness import order was changed to import torch/torch_npu before Triton, as the real runner does.

Real capture rerun: `artifacts/journey-full-2026-11-06/cann/dsa-final16-q8-fulltrace-budget-v2`, using the existing `chijin_v3.5.x` Docker and recovered-site installation. It is capture-only; no new timing measurements are claimed.

Outcome: terminal passed; all three raw captures are complete, with zero dropped endpoints. Baseline has 24184 events/48368 endpoints, split partial has 3128/6256, and merge has 66/132. Both timeline indexes have no failures, pending decodes or retained owners. Profiled output and LSE errors equal their unprofiled checks (details in real-capture-summary.json). The indexes retain `clock_status=unverified`; record completeness does not certify a common clock or elapsed-time precision.

Reproduction: apply the two source changes from db36d303 to the recovered profiler package, then apply installed-hook-compatibility.patch from that package directory (the current repository mixin already contains this interface). The deployment receipts record each original/new hash and backup path. Launch with scripts/journey_remote.py cann launch --attempt <new-name> --case dsa --sequence 8 --tile 16 --stages 1 --warps 4 --record-capacity 16384 --capture --capture-only.

Compatibility patch SHA256: `9432e25b26d015086dd8668f77f976731afcd1dcae6febc5937a905f1a304b4b`.

Mechanism evidence: dot-fragment-counts.json records each observer separately. AIC source sites 108/109 each occur 128 times per selected observer in baseline and 16 times in candidate. AIV site 109 has two distinct vector observers per selected program, each with the same 128→16 reduction; summing those writers gives 256→32 per program. Across selected programs, the three backend sites total 256/256/512 versus 32/32/64. These are observed source-fragment occurrences, not a hardware matmul instruction count.

Presentation limit: the baseline raw event document is complete, but its derived counter-ns Perfetto export reports `Perfetto trace exceeds byte budget; originals remain intact`. Candidate partial/merge counter-unit exports are available. This remaining export-size limit is separate from both record loss and clock certification; no further GPU run is needed to address it.
