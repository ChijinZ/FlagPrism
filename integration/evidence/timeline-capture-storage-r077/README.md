# Capture storage and release recovery (R077)

This delta adds versioned content-addressed capture metadata, migrates maintained readers, and preserves immutable capture facts across a failed resource-release retry. Raw device records, compiler/clock/dependency qualification and native ABI are unchanged. Legacy inline captures remain readable.

- Normal wheel source `ea2c936`: all three backends passed 55 tests and 11 subtests in normal and optimized Python. Native inputs were checked and reused.
- Real E01 sessions: ten interleaved calls, two specializations, per-call math/input/tail/State checks and retained identity/raw checks. NVIDIA and GCU whole bundles passed at 28,846,429 and 41,135,845 bytes.
- Ascend E01 originally failed only the complete-bundle budget at 67,773,556 bytes. That failure is preserved. `cf0ee96` changes only observations JSON whitespace; its normal Ascend wheel passed the same affected tests. A retained-only owned-copy repack passed the original post-finalization checks at 66,815,281 bytes. It did not rerun device mathematics or turn the original terminal failure into success.
- Public re-export: all three new-schema bundles passed three fresh processes, with retained artifacts unchanged and counter trace bytes matching prior exports (40 NVIDIA, 10 GCU, 10 Ascend).
- These 60 new traces passed the pinned independent protobuf/Trace Processor verifier, exact raw/time checks and all 263 importer statistics each. No positive error/data-loss statistics. Prior UI evidence is reused; no new UI claim.

`summary.json` records source identities, original terminal states and SHA-indexed full receipt archives retained in the workspace. Individual results and test logs are included here; large captures, SDK binaries and complete raw/SQL receipts stay in those archives.

The independent reports preserve original findings and append bounded closures. This is a storage/recovery delivery, not whole timeline-goal acceptance. Original cross-backend boundary, ordinary/profile dependency preservation and independent State-writer requirements remain open. No paper or Study data changed.
