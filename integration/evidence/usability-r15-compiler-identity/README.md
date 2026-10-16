# Ascend compiler identity: independent installation checkpoint

Source `a829a3312af69c1b961919025053829d7096a2b1` was assembled through the
public `integration/patches/ascend/build_automatic_wheel.py` entry and installed
into a fresh venv under `/tmp/chijin-r15-compiler-identity-install-v2` in the
existing Ascend Docker. This is an explicitly audited Python-only refresh of
matching native artifacts, with no native compilation or NPU initialization.

The wheel SHA256 is
`bbd3ff08a15f2cb174be3d63d527540935f2811d8a0356772d7749a85b1a7a14`.
Actual installed CPU tests: **56 passed, 0 skipped**, 2.01 seconds. Both actual
JIT implementations use installed compiler/helper bytes; the two linalg driver
boundaries execute deterministic CPU compiler fixtures. The driver receipt test's
explicit source loader is relocated to installed source, with all other test
logic retained. This is CPU integration evidence, not SDK device qualification.

Before reuse, the controller re-read and compared 3,549 actual native source
files, 2,748 unique compile dependencies, 1,272 link inputs, and the recorded
native artifacts. Changed objects from the earlier r13 build are resolved by
its explicit object-audit old/new hash and path fields, then checked against the
actual successful link argv. No path substitution is guessed. The wheel retains
107 native/header/tool members byte-for-byte from the ec75 wheel.

The installed audit binds 1,049 extracted component files to their exact Git
blobs. It then verifies 380 package files and all 249 Python sources through
source, standard stage, wheel ZIP and installed bytes. The new compiler identity
helper, compiler selection/capability code, both JIT paths and profile driver
receipt source are included. All product imports resolve inside the fresh venv;
there is no developer `PYTHONPATH` fallback. Terminal checks confirm the
controller and all 14 recorded child PIDs have exited with no live or zombie
process remaining in its process group.

| Retained file | Purpose |
| --- | --- |
| `installed-audit.json` | Exact source/wheel/import paths and verified counts |
| `install-receipt.json` | Frozen script/source identities, bounded commands/PIDs/exits, native reuse gate |
| `wheel-result.json` | Official source assembler's source/stage/ZIP identity manifest |
| `package-python-source-index.json` | Every verified Python source and package member SHA256 |
| `native-byte-audit.tgz` | Complete source, compile dependency, link input and previous-wheel native byte bridges |
| `installed-56-cpu.log` | Actual installed pytest result |
| `terminal-confirmation.json` | Finite completion and process-group check |
| `evidence-index.json` | Hashes for the complete external archive and retained local evidence |

The complete archive, scripts, source snapshots, original failures and logs are
also retained at `artifacts/usability/run-013/compiler-identity/` in the shared
workspace. `install-v2-evidence.tgz` has SHA256
`ffbe5dddad9195715413701050c84ddffb6cc7fd94e2699a3ca7e49b51b55afb`.
The initial stat-only implementation's two real-JIT failures and the symlink
capability regression remain preserved. The earlier exact-2ddb installation
attempt failed an audit path mapping and its resumed controller was explicitly
terminated for the compatibility fix; neither is counted as this installation.

Executable identity covers the selected executable bytes. It does not claim a
complete SDK dependency fingerprint. At this checkpoint, the standalone SDK source build and the original
scalar-state qualification failures remain open. The SDK fix and original
ordinary/profile device regression are separate root-controlled work; this
checkpoint makes no hardware qualification claim.

The subsequent C3 portability fix makes the CPU compiler fixtures use the
active `sys.executable` instead of a machine-specific Python path. Its affected
14 tests passed against this same installed wheel in the Ascend Docker; see
`portable-fixture-14-cpu.log`. No installed product or native bytes changed.
