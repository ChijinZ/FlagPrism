# Ascend LLVM analysis tools

`FlagPrismAscendLateObserver.so` is the existing upstream LLVM15 plugin run
outside the vendor compiler. The SDK receives its actual adapted actor input.

`flagprism-ascend-structure` is a read-only LLVM15 indexer for that exact input:

```sh
cmake -S Profiler/llvm -B build/ascend-observer -G Ninja \
  -DLLVM_DIR=/usr/lib/llvm-15/lib/cmake/llvm
cmake --build build/ascend-observer --target flagprism-ascend-structure
build/ascend-observer/flagprism-ascend-structure adapted-actor.ll > structure.json
```

It parses and verifies the input, then records its SHA, typed SSA operands,
block successors, PHI incoming edges, actual inline assembly and direct calls,
integer overflow flags, volatile memory operations, debug locations, and LLVM
natural-loop membership. Integer constants wider than 64 bits, poison,
undefined values, other constants, and indirect calls remain explicitly
uninterpreted. Aggregate types are opaque; scalar integer widths and pointer
address spaces are encoded without recursive type expansion.

The tool limits input to 16 MiB, output to 32 MiB, definitions to 64 functions,
each function to 8192 blocks, SSA identities to 300000, structural work to one
million units, individual text fields to 4096 bytes and cumulative text to
8 MiB. It exits unsuccessfully for invalid IR or exceeded bounds. It writes
the complete JSON only after successful analysis.

This tool supplies facts for source-region rules under development. It does
not certify a source interval, record tuple, loop iteration, final machine
schedule, native issue prefix, clock unit, or exclusive cost. It does not
modify LLVM, compile an SDK object, launch a kernel, or replay an application.
Automatic capture/offline rule integration is not implemented by this target.

The native CLI checks run in a server Docker with an explicit built tool:

```sh
python -I tests/timeline/p01_ascend_structure_cli.py \
  --tool "$PWD/build/ascend-observer/flagprism-ascend-structure" \
  --output /tmp/ascend-structure-tests
```

Use a fresh output directory for the optimized Python mode as well. These
checks exercise real LLVM parsing, invalid CFG/PHI rejection, endpoint SSA
identity, poison, and indirect calls; they do not replace actual actor-input
or device acceptance.

The internal Python `timeline_ascend_regions.bind_record_endpoints` consumer
associates these facts with the declared actor function and explicit trace
argument from its compiler ABI. It checks a contiguous volatile eight-word
record, site/semantic descriptor, actual start/end clock definitions, the
tick-or-zero start PHI, and the commit expression over the recorded fields.
Missing/ambiguous tuples remain unverified. Scan exhaustion aborts the result;
it cannot certify an earlier match as unique.

Its `llvm_tuple_endpoints_bound` result concerns that association only.
Selection, source-body containment, actor-role semantics, loop paths and final
native scheduling remain explicitly unverified. This internal rule is not yet
connected to normal capture/offline inspection. `ascend_record_rule_cases.py`
contains endpoint, field, pointer, descriptor, duplicate and interrupted-scan
faults applied to a real actor graph by the retained-input runner.
