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

# SDK failure tests use real production collectors and real installed headers;
# only SDK calls are replaced. Every case starts in a fresh process.
if(CMAKE_SYSTEM_NAME STREQUAL "Linux" AND FLAGPRISM_BACKEND STREQUAL "enflame")
  add_executable(EnflameSdkCleanupTest EnflameSdkCleanupTest.cpp
    ../../csrc/lib/Profiler/Vendor/EnflameProfiler.cpp
    ../../csrc/lib/Context/Context.cpp)
  target_include_directories(EnflameSdkCleanupTest PRIVATE
    "${PROFILER_SRC_DIR}/include" "${PROFILER_COMMON_DIR}/include"
    "${TOPS_INCLUDE_DIR}" "${TOPSPTI_INCLUDE_DIR}")
  target_compile_features(EnflameSdkCleanupTest PRIVATE cxx_std_17)
  target_compile_options(EnflameSdkCleanupTest PRIVATE -fexceptions -Werror)
  foreach(_case disable unsubscribe repeat partial external external-partial register)
    add_test(NAME EnflameSdkCleanup.${_case}
      COMMAND EnflameSdkCleanupTest ${_case})
  endforeach()
endif()

if(CMAKE_SYSTEM_NAME STREQUAL "Linux" AND FLAGTREE_PROFILER_GPU_RUNTIME)
  find_package(Python3 REQUIRED COMPONENTS Development.Embed)
  add_library(CuptiSdkTestShim SHARED CuptiSdkTestShim.cpp)
  target_include_directories(CuptiSdkTestShim PRIVATE "${CUPTI_INCLUDE_DIR}")
  target_compile_features(CuptiSdkTestShim PRIVATE cxx_std_17)
  target_compile_options(CuptiSdkTestShim PRIVATE -fexceptions -Werror)
  # Parent compiler builds can put shared libraries directly in the Python
  # package. SDK test doubles must never be emitted there or shipped in wheels.
  set_target_properties(CuptiSdkTestShim PROPERTIES
    OUTPUT_NAME R7CuptiSdkStub
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/sdk-shim")
  foreach(_config DEBUG RELEASE RELWITHDEBINFO MINSIZEREL)
    set_target_properties(CuptiSdkTestShim PROPERTIES
      LIBRARY_OUTPUT_DIRECTORY_${_config} "${CMAKE_CURRENT_BINARY_DIR}/sdk-shim")
  endforeach()
  add_custom_command(TARGET CuptiSdkTestShim POST_BUILD
    COMMAND "${CMAKE_COMMAND}" -E create_symlink
      "$<TARGET_FILE_NAME:CuptiSdkTestShim>"
      "$<TARGET_FILE_DIR:CuptiSdkTestShim>/libcupti.so"
    COMMAND "${CMAKE_COMMAND}" -E create_symlink
      "$<TARGET_FILE_NAME:CuptiSdkTestShim>"
      "$<TARGET_FILE_DIR:CuptiSdkTestShim>/libcuda.so.1")
  get_property(_sdk_runtime_libs GLOBAL PROPERTY FLAGTREE_PROFILER_LIBS)
  set(_sdk_runtime_objects "")
  foreach(_lib IN LISTS _sdk_runtime_libs)
    if(NOT _lib STREQUAL "FlagTreeProfilerBindings")
      list(APPEND _sdk_runtime_objects $<TARGET_OBJECTS:${_lib}>)
    endif()
  endforeach()
  add_executable(CuptiSdkCleanupTest CuptiSdkCleanupTest.cpp ${_sdk_runtime_objects})
  target_include_directories(CuptiSdkCleanupTest PRIVATE
    "${PROFILER_SRC_DIR}/include" "${PROFILER_COMMON_DIR}/include"
    "${CUPTI_INCLUDE_DIR}")
  target_compile_features(CuptiSdkCleanupTest PRIVATE cxx_std_17)
  target_compile_options(CuptiSdkCleanupTest PRIVATE -fexceptions -Werror)
  target_link_libraries(CuptiSdkCleanupTest PRIVATE CuptiSdkTestShim
    Python3::Python ${CMAKE_DL_LIBS})
  foreach(_case disable unsubscribe callback repeat partial external pc-finalize
                mode alias path shared pc-to-normal path-after-load pc-release external-partial
                probe-active probe-shared probe-idle probe-enable-failure
                probe-pending probe-start probe-config)
    add_test(NAME CuptiSdkCleanup.${_case}
      COMMAND "${CMAKE_COMMAND}" -E env
        "LD_LIBRARY_PATH=$<TARGET_FILE_DIR:CuptiSdkTestShim>:$ENV{LD_LIBRARY_PATH}"
        "$<TARGET_FILE:CuptiSdkCleanupTest>" ${_case}
        "$<TARGET_FILE_DIR:CuptiSdkTestShim>")
  endforeach()
endif()
