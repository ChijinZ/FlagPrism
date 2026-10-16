# Selecting an isolated Ascend compiler

Set `TRITON_ASCEND_COMPILER` to an absolute path to the compiler executable
before invoking the ordinary application or the FlagPrism CLI/session:

```sh
export TRITON_ASCEND_COMPILER=/opt/my-ascend-toolchain/bin/bishengir-compile
python my_application.py
```

The executable is resolved through symlinks and must exist, be a regular file,
and have execute permission. An empty, relative, missing or nonexecutable
explicit selection raises an error; it never silently falls back to another
compiler. Without this variable, the existing order remains: packaged
`bishengir/bin/bishengir-compile`, `bishengir-compile` on `PATH`, then
`TRITON_NPU_COMPILER_PATH/npuc`. Keep the other SDK tools and runtime libraries
required by the selected compiler available in its ordinary environment.
This selection does not replace system CANN, its libraries or the driver.

Both ordinary and profiled compilation bind the resolved executable path and
SHA256 to `NPUOptions.compiler_identity`. Both FlagTree JIT implementations
normalize this option before the in-memory specialization lookup, and the same
option reaches the persistent compilation key. Changing the selected path or
executable bytes invalidates the corresponding specialization automatically;
clearing caches or replacing imported Python modules is unnecessary. A tool
that changes between option binding and compilation is rejected with a retry
message. Compiler metadata records `ascend_compiler_identity`, and profiled
`driver.json` receipts retain that same `{path, sha256}` fingerprint alongside
the actual SDK command.

The process hashes each unchanged executable once. Hot lookups check device,
inode, size, `ctime_ns` and `mtime_ns`, and synchronously drain one nonblocking
Linux inotify descriptor. Notifications invalidate the digest even for an
in-place edit whose size and restored timestamps match the cached stat key.
There is no background thread or additional Python dependency. Hashing checks
the open file and selected path before and after reading, and retries a
changing file at most three times. The process retains at most 64 watches and
digests; it resets watches, digests and the lock after fork. If notifications
cannot be established, fail, or overflow, the process conservatively hashes on
every lookup instead of trusting a stat-only cache. This fallback can cost more
for large executables. Replace a compiler atomically when installing an upgrade;
concurrent writes during compilation can still cause an explicit retry error.

The identity describes the selected executable bytes. Shared libraries,
bitcode, and other external toolchain inputs retain their existing identities;
this mechanism does not claim to fingerprint an entire SDK installation.

CPU regression command in an installed Ascend environment:

```sh
python -m pytest -q integration/patches/ascend/test_compiler_identity.py \
  integration/patches/ascend/test_auto_blockify_cache.py \
  Profiler/test/test_ascend_compiler.py
```

These tests exercise the actual selector and both actual JIT cache entrances
with fake compilation/driver boundaries; they do not initialize an NPU. They
cover compiler-path changes, same-path edits and timestamp restoration, invalid
selection and recovery, driver receipt propagation, bounded retries, read
counts, watch failures/overflow, concurrency and fork. They complement the
separate fresh-wheel and hardware regression with an independently built SDK.
