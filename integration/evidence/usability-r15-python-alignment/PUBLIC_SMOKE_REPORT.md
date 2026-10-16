# New installed a829 public CLI functional smoke

NVIDIA and Enflame new installations both passed the authorized default CLI smoke on GPU0. These are known public development regressions, not a repeated full hardware qualification or performance measurement. Ascend was not accessed. The preexisting installation evidence archives/indexes remain unchanged.

| Backend | Actual user kernel calls / captures | Dynamic records / raw bytes | Bundle bytes | Complete export seconds | CLI host wall seconds |
|---|---:|---:|---:|---:|---:|
| NVIDIA | 2 / 2 | 16 / 256 | 3,572,714 | 0.259227255 | 3.370378 |
| Enflame r2 | 4 / 4 | 32 / 26,752 | 19,530,814 | 0.505059382 | 15.238801 |

All are within the engineering compile120s/export60s/bundle64MiB limits. Each entire CLI case also had a360s controller limit. Host times are engineering budget evidence, not GPU latency, throughput or profiler overhead comparisons.

The commands use the actual new `venv/bin/python -B -I -m flagtree.profiler.cli --detail auto --device 0 -n NEW_BUNDLE application.py ORIGINAL_APP NEW_MATH_RESULT`. `application.py` is an external ordinary runpy startup ledger wrapper; no private profiler APIs, supplied site IDs, scope annotations, altered kernel/math/oracle, hidden warmup or application replay are used. Sources and the original independent physical raw-byte verifier were copied byte-for-byte from the a829 component. `source-pins.json` records their actual SHA256 identities. Each attempt has a new cache and bundle. NV wheel7d95df69... and GCU wheelf24cd4cb... were preserved and their actual installed native members rehashed against the wheel again after capture.

NVIDIA original `warp_specialization_affine_smoke.py` and its unchanged affine module passed runtime K128/320 (2/5 tiles), same compiled binary, original mathematical tolerances, unchanged inputs, tail canary, actual worker region, and device_calls1 each. The independent raw verifier checks every physical cell byte/flags/padding/hash, exact emitted-row set, source/actor/binary/invocation association and fine-view equivalence. It additionally finds common actual sites with2/5 visits under the two distinct invocation IDs. Each capture has at least2 internal sites, and the actual HTML view is nonempty (490256B).

Enflame original `source_census_application.py` default passed weighted2/5 and cubic3/6 runtime repetitions with same binary within each pair. It retained four explicit calls, original math/input/activation/tail canary checks, and matching actual output/expected digests. The same independent raw verifier checks all physical bytes and fine-view records and finds common actual sites carrying the requested runtime counts. Four distinct capture/invocation identities and at least2 sites per capture are verified. Its actual HTML view is nonempty (91366B).

First GCU attempt356147/CLI356148 naturally failed before external startup ledger creation and before runpy entered the application: the wrapper selected module names with `startswith(('triton','flagtree'))`, incorrectly including external SDK dependency `triton_kernel_gcu`, then rejected that permitted system dependency path. The collector/device had already initialized; this was not a claim of zero device access. No user application kernel was executed. Original rc1/cli.log/controller/source/bundle artifacts remain in `gcu-initial-failure-evidence.tgz`. Root explicitly authorized one new independent attempt after this harness correction; this was not an automatic retry.

Only the wrapper's module-name filter changed to exact `triton`/`triton.*` and `flagtree`/`flagtree.*`. CPU regression reproduces the old false rejection, permits external SDK dependencies, and still rejects3 actual-package fallback cases. Wrapper SHA df1258c89abb2de520130b7a9f187fff146022678d8e42079c8dde10939ed4ea. Old/new interpreters independently found identical87 dependency files and paths under `/usr/local/lib/python3.12/dist-packages/triton_kernel_gcu`. It has no separate distribution/version metadata or module __version__; the retained actual SDK distribution is torch_gcu2.10.0+3.8.20260703. `gcu-{old,new}-sdk-dependency.json` records exact paths/hashes/metadata; this dependency is not represented as a new-venv file. GCU r2 kept every actual triton/flagtree import inside the new venv.

GCU successful controller356331/PGID356331, ticks998437314, argvSHA8fe0b776c819348f0ccddf554899dca72af4d9bae8be27e800853436ac00d466 completed naturally and was actually absent together with CLI/owned children at collection. It used direct foreground docker exec without outer setsid.

NVIDIA controller20154/PGID20154, ticks3285280, argvSHA3d097b1c10308c60bb8260b46ef2ab457262a6acc0c5501fd1d19a446476b3b8 completed and reaped all owned children but remains a PID1 terminal zombie. The outer setsid forked under Docker exec despite the foreground SSH parent. It has0 file descriptors and0 children, and no live/device work remains; no init/daemon intervention was attempted. The initial strict release receipt required PID absence and retains `device_lease_released:false`. Separate `nvidia-terminal-z-release.json` explicitly proves terminalZ/fd0/children[] and releases the device lease without erasing that limitation. Both GPU0 leases are returned; no more device work is queued.

Complete locally verified evidence:

- `nvidia-smoke-evidence.tgz`:400608B,54 indexed files, SHAd0194cf6d8e86bddb9ae92d7a0a2e60369c23e7ca3e0b11a51ee874adf6a2035.
- `gcu-r2-smoke-evidence.tgz`:908443B,62 indexed files, SHA21275ffdb6bf43f0ffe1c6a641ee6d5fac4cff8e2e2e976dbb1a19c806af9a8c.
- `gcu-initial-failure-evidence.tgz`:15375B,12 indexed files, SHA8ecf1616cdeafbc3b57a82afb41bb4f886c6462853f4e1277cfcd724288c0d34.
- `local-smoke-archive-audit.json` records all archive-member/index byte/hash verification and actual outcome/budget totals. The extracted directories retain original scripts, raw observations, source material, UI HTML, math receipts, startup ledgers and terminal release documents.
