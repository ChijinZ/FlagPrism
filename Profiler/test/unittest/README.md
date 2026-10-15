# CPU launch receipt and startup contracts

On Linux with GCC or Clang, configure the normal FlagTree/FlagPrism build with
`TRITON_BUILD_UT=ON`, then run:

```sh
cmake --build <build> --target CannLaunchReceiptRegistry
ctest --test-dir <build> -R 'CannLaunchReceiptTest|ProfilerStartRecoveryTest' --output-on-failure
```

The target compiles the complete production `CannProfiler.cpp` with function/data
sections and linker section GC. No implementation is extracted or substituted,
no SDK library is mocked, and no device or collector is opened. Constructed worker
PODs and explicit seal strings test the registry's schema, reference ownership,
concurrency, epoch separation and close/seal state machine. They do not validate
SDK directory discovery, SDK queries, NPU launches, or SDK clock alignment.

`ProfilerStartRecoveryTest` uses a derived test profiler to exercise the real
base class's throw/retry, idempotence, stop/restart and recursive-entry behavior.
Runtime exception support is enabled only for this test target, preserving the
compiler passes' existing exception policy.
