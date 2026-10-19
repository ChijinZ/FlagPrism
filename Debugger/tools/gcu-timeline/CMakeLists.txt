cmake_minimum_required(VERSION 3.20)
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
  project(FlagPrismGcuTimeline LANGUAGES C CXX)
  find_package(MLIR REQUIRED CONFIG)
endif()
list(APPEND CMAKE_MODULE_PATH "${MLIR_CMAKE_DIR}" "${LLVM_CMAKE_DIR}")
include(AddLLVM)
include(AddMLIR)
add_executable(flagprism-gcu-timeline
  main.cpp ../../lib/Instrumentation/GcuTimeline.cpp)
target_compile_features(flagprism-gcu-timeline PRIVATE cxx_std_17)
target_include_directories(flagprism-gcu-timeline PRIVATE
  ../../include ${LLVM_INCLUDE_DIRS} ${MLIR_INCLUDE_DIRS})
separate_arguments(FLAGPRISM_LLVM_DEFINITIONS NATIVE_COMMAND "${LLVM_DEFINITIONS}")
target_compile_options(flagprism-gcu-timeline PRIVATE ${FLAGPRISM_LLVM_DEFINITIONS} -fno-rtti)
target_link_libraries(flagprism-gcu-timeline PRIVATE
  MLIRParser MLIRIR MLIRArithDialect MLIRFuncDialect MLIRMemRefDialect
  MLIRSCFDialect MLIRGPUDialect MLIRLLVMDialect MLIRVectorDialect LLVMSupport)

if(FLAGPRISM_PYTHON_DIR)
  set_target_properties(flagprism-gcu-timeline PROPERTIES
    OUTPUT_NAME "gcu-timeline"
    RUNTIME_OUTPUT_DIRECTORY "${FLAGPRISM_PYTHON_DIR}/flagtree/debugger/_bin")
endif()
