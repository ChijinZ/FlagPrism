// Finite SDK-decoder witness for the already captured public C1 recurrence.
// This host-only diagnostic is not a profiler frontend or a hardware-time test.
#include "runtime/rt.h"
#include "runtime/rt_ffts.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

static void check(rtError_t status, const char *stage) {
  if (status != RT_ERROR_NONE)
    throw std::runtime_error(std::string(stage) + " returned " +
                             std::to_string(status));
}

static void verifyModelRuntime(const std::filesystem::path &modelDirectory) {
  std::ifstream maps("/proc/self/maps");
  std::string line;
  bool found = false;
  while (std::getline(maps, line)) {
    const auto first = line.find('/');
    if (first == std::string::npos)
      continue;
    const std::filesystem::path path = line.substr(first);
    if (path.filename().string().rfind("libruntime", 0) != 0)
      continue;
    const auto actual = std::filesystem::canonical(path);
    const auto name = actual.filename().string();
    if (actual.parent_path() != std::filesystem::canonical(modelDirectory) ||
        (name != "libruntime_camodel.so" && name != "libruntime_cmodel.so"))
      throw std::runtime_error("Refuse non-model runtime: " + actual.string());
    found = true;
    std::cout << "verified_model_runtime=" << actual.string() << '\n';
  }
  if (!found)
    throw std::runtime_error("No verified Ascend910B4 model runtime loaded");
}

static void *allocate(const void *host, std::size_t bytes) {
  void *device = nullptr;
  check(rtMalloc(&device, bytes, RT_MEMORY_HBM, 0), "model rtMalloc");
  check(rtMemcpy(device, bytes, host, bytes, RT_MEMCPY_HOST_TO_DEVICE),
        "model input copy");
  return device;
}

// Same packed/aligned final ABI as the captured FlagTree launcher.
struct __attribute__((packed)) Arguments {
  void *ffts __attribute__((aligned(8)));
  void *synchronizationLock __attribute__((aligned(8)));
  void *workspace __attribute__((aligned(8)));
  void *x __attribute__((aligned(8)));
  void *y __attribute__((aligned(8)));
  void *state __attribute__((aligned(8)));
  void *steps __attribute__((aligned(8)));
  void *trace __attribute__((aligned(8)));
  std::int32_t gridX __attribute__((aligned(4)));
  std::int32_t gridY __attribute__((aligned(4)));
  std::int32_t gridZ __attribute__((aligned(4)));
};
static_assert(sizeof(Arguments) == 80, "Captured host launch ABI differs");

int main(int argc, char **argv) {
  try {
    if (argc != 5)
      throw std::runtime_error("Expected existing ELF, raw bytes, report, model library directory");
    verifyModelRuntime(argv[4]); // Before any runtime initialization or launch.
    const auto traceBytes = std::stoull(argv[2]);
    if (traceBytes == 0 || traceBytes > 8388608)
      throw std::runtime_error("Captured raw allocation exceeds the frozen bound");
    std::ifstream input(argv[1], std::ios::binary);
    std::vector<char> image((std::istreambuf_iterator<char>(input)), {});
    if (image.empty())
      throw std::runtime_error("Cannot read the existing device object");
    check(rtSetDevice(0), "model device initialization");
    rtDevBinary_t binary{};
    binary.magic = RT_DEV_BINARY_MAGIC_ELF_AIVEC;
    binary.version = 0;
    binary.data = image.data();
    binary.length = image.size();
    void *handle = nullptr;
    check(rtDevBinaryRegister(&binary, &handle), "model binary registration");
    static std::size_t stub = 0;
    check(rtFunctionRegister(handle, &stub, "recurrence_model_decode",
                             const_cast<char *>("recurrence"), 0),
          "model function registration");
    rtStream_t stream = nullptr;
    check(rtStreamCreate(&stream, 0), "model stream creation");
    std::uint64_t ffts = 0;
    std::uint32_t fftsBytes = 0;
    check(rtGetC2cCtrlAddr(&ffts, &fftsBytes), "model FFTS address");
    std::vector<float> x(257), y(261, -17.25f);
    std::vector<std::int32_t> state(257, 0);
    const std::int32_t steps = 3;
    for (std::size_t i = 0; i < x.size(); ++i)
      x[i] = -2.0f + static_cast<float>(i) / 64.0f;
    std::vector<std::uint8_t> trace(traceBytes + 128, 0);
    std::fill(trace.begin() + traceBytes, trace.end(), 165);
    void *xp = allocate(x.data(), x.size() * sizeof(float));
    void *yp = allocate(y.data(), y.size() * sizeof(float));
    void *sp = allocate(state.data(), state.size() * sizeof(std::int32_t));
    void *kp = allocate(&steps, sizeof(steps));
    void *tp = allocate(trace.data(), trace.size());
    Arguments args{reinterpret_cast<void *>(ffts), nullptr, nullptr,
                   xp, yp, sp, kp, tp, 3, 1, 1};
    check(rtKernelLaunch(&stub, 3, &args, sizeof(args), nullptr, stream),
          "one model kernel launch");
    check(rtStreamSynchronize(stream), "model launch completion");
    check(rtMemcpy(y.data(), y.size() * sizeof(float), yp,
                   y.size() * sizeof(float), RT_MEMCPY_DEVICE_TO_HOST), "model output");
    check(rtMemcpy(state.data(), state.size() * sizeof(std::int32_t), sp,
                   state.size() * sizeof(std::int32_t), RT_MEMCPY_DEVICE_TO_HOST), "model state");
    check(rtMemcpy(trace.data(), trace.size(), tp, trace.size(),
                   RT_MEMCPY_DEVICE_TO_HOST), "model guard");
    for (std::size_t i = 0; i < x.size(); ++i) {
      float expected = x[i];
      for (int j = 0; j < steps; ++j)
        expected = expected * 0.75f + 0.125f;
      if (std::fabs(y[i] - expected) > 0.000002f || state[i] != 1)
        throw std::runtime_error("Model numerical/state check failed");
    }
    for (std::size_t i = x.size(); i < y.size(); ++i)
      if (y[i] != -17.25f)
        throw std::runtime_error("Model output guard changed");
    for (std::size_t i = traceBytes; i < trace.size(); ++i)
      if (trace[i] != 165)
        throw std::runtime_error("Model trace guard changed");
    for (void *p : {xp, yp, sp, kp, tp})
      check(rtFree(p), "model free");
    check(rtStreamDestroy(stream), "model stream destruction");
    check(rtDevBinaryUnRegister(handle), "model binary unregistration");
    std::ofstream report(argv[3]);
    report << "{\"simulation_executed\":true,\"hardware_kernel_executed\":false,"
              "\"requested_original_model_kernel_launches\":1,\"model_math_state_and_guards_passed\":true,"
              "\"trace_bytes\":" << traceBytes << "}\n";
    if (!report)
      throw std::runtime_error("Cannot persist model-only result");
    return 0;
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 2;
  }
}
