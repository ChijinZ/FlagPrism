# Native late record fields and control payloads (r043)

This delta ties tag/begin/end/payload source fields to actual SM120 STG.E.64
instructions, their coalesced relative displacement and stable common native
address/descriptor registers. Tags and literal payloads are checked through all
native reaching definitions; timer fields use r042's actual getter-value rules.
Wait payloads match the actual DEPBAR group limit. Reserved-zero commit/barrier
payloads require their corresponding checked native control boundary. There are
no operator names, fixed sites/PCs, shapes or source paths selecting the rules.

## Actual installed path

The default hook retains static `relative_record_fields` within
`native_boundary_control_file`. Invocation-specific `native_control_payload_file`
is separate: every decoded native wait/commit/barrier payload is compared with
the freshly derived native operand, retaining actual program/actor/native
ordinal and exact tag/payload raw byte spans. A second call cannot replace a
binary-wide report with its own dynamic data. The public offline exporter adds
these facts to its versioned immutable control report without replaying kernels.
Unknown or mismatched cases retain explicit unverified diagnostics, including
rule fingerprints; unrelated counter units remain separate.

## Execution evidence

All imports, packaging, numerical/device tests, CPU-only negative fixtures,
actual Trace Processor and offline export ran in existing NVIDIA Docker
`chijin-study-pro6000`. Full cached precommit fixed point and AST preservation
ran in existing GCU Docker `flagprism-enflame-dev`. The workstation only edited,
used Git, orchestrated calls and inspected/hashed retained artifacts with the
standard library.

The first source probe checked all 43 sites in both retained real captures.
Source contracts passed in normal and optimized Python. An actual independent
wheel then passed default API numerical/canary/input/multicall/stream checks,
runtime-K GEMM, compiler/derive/copy failure and recovery, prior wait/value/native
boundary contracts and new field/raw-control contracts in normal and optimized
Python. Both actual default captures contain all 43 checked sites and distinct
invocation/raw-bound control reports. Raw spans are independently compared with
actual eight-byte words. Layout/stride/overlap/descriptor clobber/control bypass,
wrong literals, ambiguous wide literals, dynamic payload mismatch, incomplete
raw, wrong binary and failed-rule fingerprint checks are CPU-only negatives;
no unsafe fixture is run as a device kernel.

Public retained-only reexport in three processes and actual Trace Processor
passed. Sixteen original isolated traces remained byte-identical. r042 private
originals still exactly match their archived SHA map. Core r024 and standalone
r036 source/executables were reused with actual byte bridges, not rebuilt or
overlaid. See `verification.json` for exact source/wheel/archive SHA, counts,
terminal receipts and actual inactive process identities. The archive retains
raw/guards, original compiler objects, both disassemblies, initial source probe,
all installed/contract inputs, new static/dynamic reports and SQL outputs.

## Remaining obligations

The proof is relative field layout and decoded control value agreement. Absolute
allocation/program/ordinal address expressions and variable shared-address /
valid-size payload provenance remain unverified. Full raw provenance, physical
overlap, source cost, engine busy and temporal flows are not granted. No common
encoder/canonical or UI changed and no new browser run is claimed. Complete
three-backend pipelines, independent mathematical qualification, controlled
cases and three fresh final code reviewers remain required. Paper/Study files
are untouched.
