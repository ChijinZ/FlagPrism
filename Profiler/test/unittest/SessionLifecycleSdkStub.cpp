// Only the device discovery SDK boundary is replaced in the CPU lifecycle test.
// Session.cpp, SessionManager, Data::dump and Profiler state are production code.
#include "Device.h"
#include <stdexcept>
namespace proton {
Device getDevice(DeviceType, uint64_t) {
  throw std::runtime_error("Device SDK discovery is outside the CPU lifecycle test");
}
const std::string getDeviceTypeString(DeviceType) { return "cpu-lifecycle-test"; }
} // namespace proton
