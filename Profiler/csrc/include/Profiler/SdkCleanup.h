#ifndef PROTON_PROFILER_SDK_CLEANUP_H_
#define PROTON_PROFILER_SDK_CLEANUP_H_
#include <cstdio>
#include <exception>
namespace proton {
// Try every independent resource cleanup. Callers erase ownership only when
// attempt() succeeds; unresolved resources remain available for a later retry.
class SdkCleanup {
public:
  explicit SdkCleanup(std::exception_ptr original = {}) : first(original) {}
  template <typename Action> bool attempt(Action &&action) {
    try {
      action();
      return true;
    } catch (...) {
      if (!first) {
        first = std::current_exception();
      } else {
        // Keep the original exception type/identity. Secondary errors are
        // diagnostics, never a replacement for the application's first error.
        try {
          throw;
        } catch (const std::exception &error) {
          std::fprintf(stderr, "FlagPrism secondary SDK cleanup failure: %s\n",
                       error.what());
        } catch (...) {
          std::fputs("FlagPrism secondary SDK cleanup failure\n", stderr);
        }
      }
      return false;
    }
  }
  void rethrow() const {
    if (first)
      std::rethrow_exception(first);
  }

private:
  std::exception_ptr first;
};
} // namespace proton
#endif
