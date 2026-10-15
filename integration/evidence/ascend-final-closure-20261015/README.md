# Frozen Ascend functional and packaging closure

All planned functional requests and the final retained-source/typed-IR/selection checks have terminal success. The final wheel is a standard repack of accepted binaries, with actual ZIP/import tests for 52 Python modules, three unchanged libraries and the receipt header. ROOT compares all recorded module hashes and the header against current canonical bytes. The full FlagTree baseline diff and exact FLIR/AscendNPU-IR pins remain in integration/patches/ascend.

ROOT independently audits the original entire M2 and long-K archives, including every bundle file hash/size, raw-buffer SHA, actor records, local duration formula and recorded task association. M2: seven results/bundles, 1,029 manifest entries, 694 events, 103 raw buffers. Long-K: six results/bundles, 873 manifest entries, 40,194 events, 99 raw buffers. The archives remain outside Git at the recorded content hashes.

The small RMSNorm wait-only cost remains adverse (+60.1–78.0%). The preselected long-K original P32_K32 configuration has three paired 30-call batches with −0.08/+1.30/+0.87% device-task changes, but roughly 12.3–12.5ms host calls, 15.6–17.2s detailed export and 221–229MB per detailed 33-call session. This is not low end-to-end cost or a universal perturbation bound. All samples and original negative results remain.

All four agent-owned experiment/build/wheel PIDs were verified not live. The final common CPU source checks run separately from these hardware captures. Shared-clock origin, exclusive source cost, arbitrary Ascend sites/sampling, and general dynamic flag-generation pairing remain unsupported.
