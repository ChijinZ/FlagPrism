#ifndef PROTON_PROFILER_CUPTI_PROFILER_H_
#define PROTON_PROFILER_CUPTI_PROFILER_H_

#include "Data/Artifacts.h"
#include "Profiler/GPUProfiler.h"
#include <mutex>
#include <unordered_map>

namespace proton {

class CuptiProfiler : public GPUProfiler<CuptiProfiler> {
public:
  CuptiProfiler();
  virtual ~CuptiProfiler();

  // Capability probing must preserve a live collector and retry any probe
  // resource cleanup before querying context or enabling PC sampling again.
  void validatePCSamplingSupport(const std::string &libPath,
                                 const std::string &mode = {});

  // Session membership is captured at API entry, before asynchronous buffers
  // arrive. The name of the kernel is descriptive, never an association key.
  VendorProfileArtifact collectActivityArtifact(const std::string &sessionPath);
  void registerActivityLaunch(uint32_t correlationId, size_t scopeId,
                              const std::set<Data *> &dataSet,
                              bool graphInstanceCountUnknown = false);
  void recordActivityKernel(const void *activity);
  void recordActivityDropped(size_t count);
  void beginActivityCapture();

private:
  struct ActivityLaunch {
    size_t scopeId;
    uint64_t epoch;
    bool graphInstanceCountUnknown{false};
    std::set<std::string> sessions;
  };
  size_t activityDropped{0};
  uint64_t activityEpoch{0};
  std::mutex activityMutex;
  std::unordered_map<uint32_t, ActivityLaunch> activityLaunches;
  struct ScopedActivity {
    VendorMetricAssociation association;
    std::set<std::string> sessions;
  };
  std::vector<ScopedActivity> activityEvents;

private:
  struct CuptiProfilerPimpl;
};

} // namespace proton

#endif // PROTON_PROFILER_CUPTI_PROFILER_H_
