# NVIDIA outlined-counter engineering checkpoint (T019 / r012)

This is real automatic raw capture and static-object evidence, **not complete P01,
source-region certification, ns qualification, Perfetto or independent-math acceptance**.
No paper or old Study data changed. All builds/imports/tests/oracles/tool execution
ran inside NVIDIA Docker `chijin-study-pro6000` on the existing PRO 6000 server.
Workstation checks only inspect retained bytes with Python stdlib.

## Delivered and tested

- Native source `4f5b2bff76ec61537bcec6d98075639d7f9ef731`: timeline boundary ABI 2
  emits explicit internal noinline clock helpers with value dependencies and
  site/phase markers. Legacy count/interval paths keep their semantics. The real
  incremental native build succeeded; wheel SHA
  `8d94918a0a14572a807c7354ecbcf135eacc87683eea48c1928d6514c766b185`.
- Python/component freeze `61ea33060f84c0e513107f95ff6992e270f5662d`: exact explicit
  symbols bind nested helpers with nonzero starts inside the parent code section.
  The mapper validates executable ELF extents, instruction coverage and disjoint
  function bodies. It retains section/function-relative positions, rather than
  inferring ownership from the nearest PC or a symbol prefix.
- Fresh installed wheel SHA
  `b7c3aaf220dd4e97f2caa867bf5dca110b4e27fd3d3e4bf0843429c519b1f22b`;
  all 607 installed members checked. Seven native members match the new native
  wheel byte for byte during Python-only packaging. Older installations remain.
- Actual interpreter:
  `/workspace/chijin-timeline-r012/runs/install-v1/output/venv/bin/python`.
- Docker CPU contracts: 20 machine-map methods, four public-interface tests and
  12 native ABI rejection actions in each normal/`-O` mode; native positive path
  has 34 anchors / 17 dependent reads. Three legacy hook tests also passed.
  Rejected old/invalid ABI tests deliberately emit compiler diagnostic logs.
- Five public ordinary dtype calls (FP16/BF16/FP32/FP64/int64) preserve exact CPU
  math/input/tail/once state and produce 320 canonical intervals. The public
  API/CLI regression also checks runtime loops, async GEMM, loaded-handle cache,
  two streams, zero grid, overflow, no-replay export recovery and legacy count.
- Total raw audit: 26 captures, 11,456 retained physical records, 5,720 paired
  intervals, 16 incomplete endpoints, 400 logical groups and 12,352 overwritten
  records. Loss is reported; endpoints and physical generations are not guessed.
- Actual nvdisasm 13.2.86 maps all seven cubins / 140 static getter PCs. The
  separate [object inspection](object-inspection.json) retains full actual CFGs,
  explicit direct calls and helper-relative addresses. No MEMBAR was found in
  these specific development objects. This is not a universal ban on user fences
  and not proof of a source region's hardware completion or participant boundary.

## Receipts and original bytes

[Raw artifact index](raw-artifact-index.json) lists all 860 original members:
`artifacts/timeline/run-012/preflight/outlined-final-original-evidence.tgz`,
6,241,355 bytes, SHA256
`079f43e6f8169a9eebc627a9e16c5ce198beafd100aa336f76485e056c37c7b8`.
The archive stays outside Git; selected build/install/math/tool/owner receipts are
included here. It contains raw records, compiled artifacts, actual disassembly
and CFG bytes, executed scripts and the installed mapper. This does not depend
on an untracked `PYTHONPATH` override.

Reproduce the byte audit from the workspace root (no product import/oracle/GPU):

```bash
python FlagPrism-method/integration/evidence/timeline-outlined-r012/audit-retained-bytes.py \
  --archive artifacts/timeline/run-012/preflight/outlined-final-original-evidence.tgz \
  --repo FlagPrism-method \
  --output /tmp/flagprism-outlined-byte-audit.json
```

[Independent byte audit](retained-byte-audit.json) recomputes physical payloads,
canonical identity/pairing, loss, compile/source hashes, actual helper getter PCs
and artifact references without importing the product. [Owned final state](owned-final.json)
checks seven completed build/install/device/tool jobs by PID/startticks: workers
are missing, historical controller processes are zombies left for PID1. Actual
capture and inspection child commands completed through their owning processes.
Final GPU state is retained in [target state](final-target-state.txt).

The preceding hand-written forwarded/read-only call primitive is retained in
`artifacts/timeline/run-012/preflight/call-primitives-v3-original.tgz` with its
original earlier compile failure. It motivated this implementation; it is not
substituted for the public automatic regression above.

## Tool assets and remaining work

Pinned standard Perfetto UI v57.2-da1d152cf assets are now actually extracted
inside Docker; [asset receipt](ui-assets-install.json) lists exact member hashes.
The downloaded zip is 15,402,304 bytes / SHA256
`3d4043c4451faaddec8f382b1a0efae4c33ca9b168ec037da32e53c1cc308408`.
This resolves asset acquisition only; a real browser/trace UI test remains.
Previously downloaded Trace Processor is runnable, not yet a profile SQL pass.

Every capture remains `partial_clock_unverified`; counter maps retain false
region/clock certificates. Still required: actual site/control-path/participant
boundary proof, applicable scale/endpoint error/epoch evidence, physical reuse,
GCU/Ascend producers and complete P01, shared ns/Perfetto export with actual SQL
and UI, independent new math and the final extra three specified code reviewers.
Static calls, positive ticks, build success and this checkpoint cannot fill those
requirements. Goal remains active.

## Additional ordinary-control investigation (not passed)

After the successful raw/object checkpoint above, a new compile-only control
compared the same source/config ordinary recurrence and GEMM with the profiled
objects. Output canaries and state remained unchanged, confirming no requested
math launch. The original strict static-barrier equality test **failed** for
GEMM; [terminal](unprofiled-first-terminal.json) and [result](unprofiled-first-result.json)
are preserved. Recurrence has no barriers in either object. Ordinary GEMM has
10 commits / 9 block barriers / 4 waits; profiled static code has 6 / 5 / 2.

The ordinary final math is fully unrolled (12 HMMA), while the profiled object
retains a loop (4 HMMA per body). Retained induction instructions suggest three
iterations. Expanding that candidate loop makes the selected opcode counts match,
but **copy/wait/dot interleaving still differs**. [Investigation](unprofiled-investigation.json)
preserves both sequences and actual loop-control instructions. This is not a
passed schedule-preservation check; static count equality would be insufficient
even if it held. Do not silently delete the failing criterion or certify the
original pipeline from this result. Next assess actual mechanism/control paths,
which dependencies remain and which ordering changes arise from observation,
including the planned sparse/dense comparison. No clock/region/P01 qualification
is granted. This is an implementation investigation, not an environment blocker.

The additional [artifact index](unprofiled-artifact-index.json) binds the actual
ordinary IR/ISA/CFG and failed job. It is separate from the immutable 860-member
primary archive; the primary successful raw audit retains its original scope.
