#ifdef FLAGPRISM_BACKEND_ENFLAME
#include <tops/tops_runtime.h>
#endif
#include "Device.h"
#if defined(FLAGPRISM_BACKEND_METAX) || defined(FLAGPRISM_HAS_METAX)
#include <mcr/mc_runtime_api.h>
#endif
#if !defined(FLAGPRISM_BACKEND_METAX) && \
    !defined(FLAGPRISM_BACKEND_ENFLAME) &&                                     \
    !defined(FLAGPRISM_BACKEND_TIANSHU) &&                                     \
    !defined(FLAGPRISM_BACKEND_MTHREADS)
#include "Driver/Ascend/AscendApi.h"
#endif
#if FLAGTREE_PROFILER_GPU_RUNTIME
#include "Driver/GPU/CudaApi.h"
#include "Driver/GPU/HipApi.h"
#endif
#if !defined(FLAGPRISM_BACKEND_METAX) && \
    !defined(FLAGPRISM_BACKEND_ENFLAME) &&                                     \
    !defined(FLAGPRISM_BACKEND_ASCEND) && !defined(FLAGPRISM_BACKEND_MTHREADS)
#include "Driver/Tianshu/TianshuApi.h"
#endif
#if !defined(FLAGPRISM_BACKEND_METAX) && \
    !defined(FLAGPRISM_BACKEND_ENFLAME) &&                                     \
    !defined(FLAGPRISM_BACKEND_ASCEND) && !defined(FLAGPRISM_BACKEND_TIANSHU)
#include "Driver/Mthreads/MthreadsApi.h"
#endif
// FlagPrism end

#include "Utility/Errors.h"

namespace proton {

Device getDevice(DeviceType type, uint64_t index) {
  // FlagPrism：use MACA device limits and clocks, not CUDA defaults.
#if defined(FLAGPRISM_BACKEND_METAX) || defined(FLAGPRISM_HAS_METAX)
  if (type == DeviceType::METAX) {
    mcDeviceProp_t prop{};
    if (mcGetDeviceProperties(&prop, index) != mcSuccess)
      throw std::runtime_error("mcGetDeviceProperties failed");
    return Device(type, index, prop.clockRate, prop.memoryClockRate,
                  prop.memoryBusWidth, prop.multiProcessorCount, prop.name);
  }
#endif
  // FlagPrism end
#ifdef FLAGPRISM_BACKEND_ENFLAME
  if (type == DeviceType::ENFLAME) {
    topsDeviceProp_t prop{};
    if (topsGetDeviceProperties(&prop, index) != topsSuccess)
      throw std::runtime_error("topsGetDeviceProperties failed");
    return Device(type, index, prop.clockRate, prop.memoryClockRate,
                  prop.memoryBusWidth, prop.multiProcessorCount,
                  prop.gcuArchName);
  }
#endif
#if FLAGTREE_PROFILER_GPU_RUNTIME
  if (type == DeviceType::CUDA) {
    return cuda::getDevice(index);
  }
  if (type == DeviceType::HIP) {
    return hip::getDevice(index);
  }
#endif
// FlagPrism：exclude unrelated SDKs in MetaX builds.
#if !defined(FLAGPRISM_BACKEND_METAX) &&                                       \
    !defined(FLAGPRISM_BACKEND_ENFLAME) &&                                     \
    !defined(FLAGPRISM_BACKEND_TIANSHU) &&                                     \
    !defined(FLAGPRISM_BACKEND_MTHREADS)
  if (type == DeviceType::ASCEND) {
    return ascend::getDevice(index);
  }
#endif
#if !defined(FLAGPRISM_BACKEND_METAX) && \
    !defined(FLAGPRISM_BACKEND_ENFLAME) &&                                     \
    !defined(FLAGPRISM_BACKEND_ASCEND) && !defined(FLAGPRISM_BACKEND_MTHREADS)
  if (type == DeviceType::TIANSHU) {
    return tianshu::getDevice(index);
  }
#endif
#if !defined(FLAGPRISM_BACKEND_METAX) && \
    !defined(FLAGPRISM_BACKEND_ENFLAME) &&                                     \
    !defined(FLAGPRISM_BACKEND_ASCEND) && !defined(FLAGPRISM_BACKEND_TIANSHU)
  if (type == DeviceType::MTHREADS) {
    return mthreads::getDevice(index);
  }
#endif
  // FlagPrism end
  throw std::runtime_error("DeviceType not supported");
}

const std::string getDeviceTypeString(DeviceType type) {
  // FlagPrism：include MetaX in portable report metadata.
  if (type == DeviceType::METAX)
    return DeviceTraits<DeviceType::METAX>::name;
  // FlagPrism end
  if (type == DeviceType::ENFLAME)
    return DeviceTraits<DeviceType::ENFLAME>::name;
  if (type == DeviceType::CUDA) {
    return DeviceTraits<DeviceType::CUDA>::name;
  }
  if (type == DeviceType::HIP) {
    return DeviceTraits<DeviceType::HIP>::name;
  }
// FlagPrism：exclude unrelated SDKs in MetaX builds.
#if !defined(FLAGPRISM_BACKEND_METAX) &&                                       \
    !defined(FLAGPRISM_BACKEND_ENFLAME) &&                                     \
    !defined(FLAGPRISM_BACKEND_TIANSHU) &&                                     \
    !defined(FLAGPRISM_BACKEND_MTHREADS)
  if (type == DeviceType::ASCEND) {
    return DeviceTraits<DeviceType::ASCEND>::name;
  }
#endif
// FlagPrism end
// FlagPrism：exclude unrelated SDKs in MetaX builds.
#if !defined(FLAGPRISM_BACKEND_METAX) &&                                       \
    !defined(FLAGPRISM_BACKEND_ENFLAME) &&                                     \
    !defined(FLAGPRISM_BACKEND_ASCEND) && !defined(FLAGPRISM_BACKEND_MTHREADS)
  if (type == DeviceType::TIANSHU) {
    return DeviceTraits<DeviceType::TIANSHU>::name;
  }
#endif
  // FlagPrism end
  if (type == DeviceType::MTHREADS) {
    return DeviceTraits<DeviceType::MTHREADS>::name;
  }
  throw std::runtime_error("DeviceType not supported");
}

} // namespace proton
