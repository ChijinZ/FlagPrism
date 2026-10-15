add_subdirectory(TraceDataIO)

# Compile the complete production CANN translation unit without loading an SDK.
# Section GC retains the registry exercised here and removes unused collector
# dependencies. This target proves CPU ownership/state contracts, not NPU capture.
if(CMAKE_SYSTEM_NAME STREQUAL "Linux" AND
   CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  add_triton_ut(
    NAME CannLaunchReceiptRegistry
    SRCS CannLaunchReceiptTest.cpp ProfilerStartRecoveryTest.cpp
         ../../csrc/lib/Profiler/Vendor/CannProfiler.cpp
  )
  target_include_directories(CannLaunchReceiptRegistry PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/../../csrc/include"
    "${PROFILER_COMMON_DIR}/include"
    "${JSON_INCLUDE_DIR}"
  )
  # These are runtime tests containing intentional throw/retry cases; compiler
  # pass targets keep their existing LLVM exception policy.
  target_compile_options(CannLaunchReceiptRegistry PRIVATE
    -fexceptions -ffunction-sections -fdata-sections)
  target_link_options(CannLaunchReceiptRegistry PRIVATE -Wl,--gc-sections)
  target_link_libraries(CannLaunchReceiptRegistry PRIVATE ${CMAKE_DL_LIBS})
endif()

# Real session/manager lifecycle with injected collector and export failures.
# CPU-only: no SDK or device is initialized. Dead code elimination omits the
# unrelated profiler registry, while the actual lifecycle/export code is linked.
if(CMAKE_SYSTEM_NAME STREQUAL "Linux" AND
   CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  add_triton_ut(
    NAME SessionLifecycle
    SRCS SessionLifecycleTest.cpp SessionLifecycleSdkStub.cpp
         ../../csrc/lib/Session/Session.cpp
         ../../csrc/lib/Data/Data.cpp
         ../../csrc/lib/Context/Context.cpp
  )
  target_include_directories(SessionLifecycle PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/../../csrc/include"
    "${PROFILER_COMMON_DIR}/include"
    "${JSON_INCLUDE_DIR}"
  )
  target_compile_definitions(SessionLifecycle PRIVATE FLAGTREE_PROFILER_GPU_RUNTIME=0)
  target_compile_options(SessionLifecycle PRIVATE
    -fexceptions -ffunction-sections -fdata-sections)
  target_link_options(SessionLifecycle PRIVATE -Wl,--gc-sections)
endif()
