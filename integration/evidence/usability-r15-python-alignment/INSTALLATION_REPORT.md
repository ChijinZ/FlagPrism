# NVIDIA / Enflame Python component alignment

Completed CPU-only refresh of component `a829a3312af69c1b961919025053829d7096a2b1` in the existing remote Docker containers. No product source changes, native compilation, device initialization, kernel execution, device performance tests, Ascend access, or changes to old wheels/venvs. The one historical CPU receipt append and its explicit recovery are documented below.

| Backend | Final fresh environment | Wheel SHA256 | CPU |
|---|---|---|---|
| NVIDIA | `/workspace/chijin-r15-python-alignment-r2/venv` | `7d95df6950a2419a85186d2e654bca952b0b955c8c4825549e4b422822988f18` | 330 passed, 3 optional browser skips |
| Enflame | `/workspace/chijin-r15-python-alignment/venv` | `f24cd4cb39dc411c7c1e04ab3f7d6797a0628ae9284d3cb267b4e8e9b1645c30` | 330 passed, 3 optional browser skips |

Both environments import triton, profiler/debugger, compiler binding, and runtime DSOs exclusively from the new installed site-packages. Runs use `-I`, unset PYTHONPATH/plugin overrides, disabled Torch backend autoload, and empty visible-device variables. `torch.cuda.is_initialized()` is false before/after CPU tests. The shared library/backend VERSION/header/other native wheel members remain byte-identical to the previous actual installed ec75 wheels. No unchanged GPU matrix was rerun.

Each archive records all 1049 canonical Git blob identities and actual extracted hashes. Installed component Python sources (68 files each) are bridged to component source, and all packaged Python files bridge actual parent/component source → standard build_py stage → wheel ZIP → fresh installed bytes. Current canonical component files were independently checked locally against those retained source hashes. This is Python-only wheel assembly through the actual FlagTree setup.py Distribution/build_py/bdist_wheel chain with previously compiled native artifacts; it is not a fresh native build. NVIDIA's public shell entry always builds native and was intentionally not invoked. Its assembly wrapper guards compiler/build subprocesses. Enflame uses the unchanged public `build_automatic_wheel.py`.

| Audit | NVIDIA | Enflame |
|---|---:|---:|
| Component native / applicable patch files, same bytes | 273 | 273 |
| Actual original compile dependencies, rehashed | 2183 | 2106 |
| Actual successful original link inputs, rehashed | 552 | 551 |
| Complete copied parent file bridge | 6621 | 6424 |
| Installed package files | 597 | 438 |
| Python source/stage/ZIP/installed bridges | 348 | 359 |
| Previous-wheel native members, same bytes | 216 | 63 |

Original changed-object link substitutions are checked against the original object-audit old/new hashes and the exact successful native link command argv. Every dependency and link input was checked before assembly. Full source/native/package indexes are retained. The names `ec75a9f-*` in the audit outputs are inherited harness filenames; their JSON source_commit and current-wheel fields explicitly name a829 and the new wheel, and their previous-wheel fields name ec75.

NVIDIA initial controller 19881/PGID19881 naturally failed at assembly because the old runtime venv lacks pybind11. The original successful build receipt identified `/workspace/venv/bin/python`; a new isolated r2 attempt used it without modifying the original environment. Successful controller 19925/PGID19925, ticks3221525, argvSHA184622d29e8a88fb05ddccd8b7db70e6771452417782d8b7375e896619d0f674 naturally finished with all children reaped. Both detached NV controller handles remain terminal zombies parented by PID1, and are not running; no init/daemon intervention was attempted. GCU controller355840/PGID355840 ticks998352105 naturally completed; none of its recorded processes remain. Receipt budget2400s is a planned budget; actual subprocess waits are capped at600s each /900s audit. Actual elapsed final NV80.0s, GCU64.4s.

GCU first CPU audit ran the inherited314-test suite and passed with3 optional skips. Before the later complete compiler regression audit, the harness was corrected to copy the native CPU test to the new prefix; the unchanged oracle then writes its receipt only there. Final GCU `audit-v2.py` runs330 tests and writes independent `audit-v2/` results. NV's final first audit also ran330 tests using the corrected copy. Do not treat the GCU first314 as the complete final suite. The initially executed GCU audit script hash was not separately frozen; the exact final supplementary script and output are retained.

The initial GCU inherited native CPU test inadvertently appended14 rows to the old `native-host-results-ec75a9f.json`. Original3394B/SHA7dcd2429a646d853188e1ca26039c01dbc67d4b8151902f0827d772786a62d33 was independently recovered from the indexed preexisting r13 package archive; affected6757B/SHA4519eba743bca4eef8b0531e1220653b3f1b0beb783e08d4934d434dbf361546 was preserved first. The original14 rows are an exact prefix of the28-row parsed array;3391 original byte-prefix bytes match (JSON append replaces the closing bracket). The old file was explicitly restored byte-for-byte to the trusted indexed original, under root authorization. Before/trusted/after hashes and all added rows are retained in history-restoration-receipt.json. NVIDIA's old3338B/SHA512011e8a21b43e6448fafcc1c2c28905394e60f95ca3367aaec85ae92c6a1b1 was verified unchanged. This is a real harness correction, not a claim that no historical file was touched.

Parent metadata: Enflame old parent actual Git HEAD is add842f2c495a3974944733ea6b07ff6b5bfcee8 with the existing three patched backend files. The copied parent's complete file hashes and native members match it, but excluding `.git` causes official setup's wheel distribution suffix to become `0.7.0+enflame` instead of `0.7.0+enflame.gitadd842f2`. This metadata suffix difference is explicit; it does not represent a changed parent backend source/ABI. NVIDIA's original existing parent directories have no usable Git metadata; this task relies on their actual same-byte source/dependency/link bridge rather than fabricating a live Git identity.

Evidence archives and locally verified indexes:

- NVIDIA `nvidia-evidence.tgz`:695478B, SHAd90b3d45c129c2ab621570fe0732609592ad820533fa042b8d24bd1e289a0dd3;38 indexed files.
- Enflame `gcu-evidence.tgz`:809512B, SHAa93276ad55d4e6bcb377ae19f91954fe5146a936cdde3a1f63e077ea97a6c089;55 indexed files.
- `local-evidence-audit.json`: local offline verification of every archive member/index hash/length, component source bytes, installed audit status and exact CPU counts.
- `history-trusted-original-provenance.json`: original preexisting r13 archive SHA and indexed historical file identities.
- `*-parent-provenance.json`: actual parent identity observations, original receipt hashes and wheel distribution versions; generated after archive collection and retained as separate evidence.
