# a829 independent Python installation alignment and public CLI regressions

Both NVIDIA and Enflame were refreshed from the already qualified native code
to Python component a829a3312af69c1b961919025053829d7096a2b1 in fresh venvs.
No native source/ABI changed and no new native compilation is claimed.
Native source, actual compile dependencies/link inputs, package source,
stage/ZIP/installed members and imports were checked; full hash manifests
remain in the retained workspace archives. Each backend passed 330 CPU tests
with three explicitly optional browser skips, which are not passes.

Root independently checked every archive index/member and canonical Git blob,
then re-read the actual remote wheel/stage/installed/source bytes using a
separate standard-library-only checker: NV 597 package members/348 Python
sources/1049 component files, GCU 438/359/1049. These receipts are included.
All installed component Python now matches the a829 candidate already installed
on Ascend. Later canonical changes are SDK tooling/tests/docs or evidence.

New installed default CLI functional regressions also passed: NV two calls /
two captures, same binary at runtime K2/5; GCU four calls / four captures,
weighted2/5 and cubic3/6. Original math/input/canary and no-replay witnesses
passed. Root independently decoded complete physical-cell flags and padding,
checked normalized rows against actual raw bytes, source/call identities and
runtime repetition counts (32 NV cells, 416 GCU cells). These are known public
development regressions, not new unseen mathematics, a new full GPU matrix,
or NVIDIA latency/throughput/overhead benchmarks.

Actual environments:
- NVIDIA: /workspace/chijin-r15-python-alignment-r2/venv,
  wheel SHA7d95df6950a2419a85186d2e654bca952b0b955c8c4825549e4b422822988f18.
- Enflame: /workspace/chijin-r15-python-alignment/venv,
  wheel SHA f24cd4cb39dc411c7c1e04ab3f7d6797a0628ae9284d3cb267b4e8e9b1645c30.

Preserved failures and boundaries:
- The first NV assembly failed because the runtime venv lacked pybind11;
  the original matching build interpreter was used for the fresh r2 attempt.
- The first GCU CPU harness appended 14 rows to an old native test receipt.
  The changed bytes and trustworthy original were retained, and exact original
  bytes restored. No product, old wheel or user-kernel evidence was changed.
  Subsequent tests write only into the new prefix. Restoration receipts and
  before/original bytes are included; the event is not erased from history.
- First GCU functional smoke failed before entering the user application:
  a wrapper prefix assertion accidentally included external SDK dependency
  triton_kernel_gcu. The exact namespace fix had CPU regression coverage;
  one separately authorized new attempt passed, preserving the first failure.
- GCU distribution metadata omits the former .gitadd842f2 suffix because the
  copied parent excludes .git. Actual parent source, VERSION, applied patches
  and native bytes are unchanged; the suffix difference is explicitly recorded.
- NV completed CPU controllers19881/19925 and smoke controller20154 remain
  terminal zombies awaiting container PID1 reaping. CLI children completed,
  were reaped, and no live/device work remains. The initial strict release
  receipt remains false; the separate terminal-Z evidence records fd0 and no
  children without falsely claiming every PID is absent. No init/daemon or
  other user's process was modified. GCU r2 controller and children are absent.

Full archives under workspace artifacts/usability/run-014/python-alignment/:
- nvidia-evidence.tgz SHA d90b3d45c129c2ab621570fe0732609592ad820533fa042b8d24bd1e289a0dd3.
- gcu-evidence.tgz SHA a93276ad55d4e6bcb377ae19f91954fe5146a936cdde3a1f63e077ea97a6c089.
- public-smoke/nvidia-smoke-evidence.tgz SHA d0194cf6d8e86bddb9ae92d7a0a2e60369c23e7ca3e0b11a51ee874adf6a2035.
- public-smoke/gcu-r2-smoke-evidence.tgz SHA21275ffdb6bf43f0ffe1c6a641ee6d5fac4cff8e2e2e976dbb1a19c806af9a8c.
Original archive indexes are retained; they describe those full archives, not
an assertion that all their members are checked into Git. This directory has
its own subset index. SDK binary/header contents and private qualification
mathematics/IR are excluded. Ascend main24/new8 full qualification is separate
and remains pending; these results do not claim complete product acceptance.
