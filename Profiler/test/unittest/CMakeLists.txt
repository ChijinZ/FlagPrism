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
