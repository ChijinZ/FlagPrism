// CPU state-machine tests of the real Profiler base; no SDK is simulated.
#include "Profiler/Profiler.h"
#include "gtest/gtest.h"

namespace proton {
namespace {

struct StartFailure {
  const void *identity;
};

class CountingProfiler : public Profiler {
public:
  int starts{0};
  int stops{0};
  bool failNext{false};
  bool reenter{false};
  const void *failureIdentity{this};

private:
  void doStart() override {
    ++starts;
    if (reenter)
      EXPECT_EQ(start(), this);
    if (failNext) {
      failNext = false;
      throw StartFailure{failureIdentity};
    }
  }
  void doStop() override { ++stops; }
  void doFlush() override {}
};

TEST(ProfilerStartRecoveryTest, OriginalFailureRetrySuccessAndStopRestart) {
  CountingProfiler profiler;
  profiler.failNext = true;
  bool caught = false;
  try {
    profiler.start();
  } catch (const StartFailure &failure) {
    caught = true;
    EXPECT_EQ(failure.identity, profiler.failureIdentity);
  }
  ASSERT_TRUE(caught);
  EXPECT_EQ(profiler.starts, 1);
  EXPECT_EQ(profiler.stops, 0);
  EXPECT_EQ(profiler.start(), &profiler);
  EXPECT_EQ(profiler.starts, 2);
  EXPECT_EQ(profiler.start(), &profiler);
  EXPECT_EQ(profiler.starts, 2);
  profiler.stop();
  EXPECT_EQ(profiler.stops, 1);
  profiler.stop();
  EXPECT_EQ(profiler.stops, 1);
  profiler.start();
  EXPECT_EQ(profiler.starts, 3);
}

TEST(ProfilerStartRecoveryTest, RecursiveEntryDoesNotRunStartTwice) {
  CountingProfiler profiler;
  profiler.reenter = true;
  profiler.start();
  EXPECT_EQ(profiler.starts, 1);
  profiler.stop();
  profiler.start();
  EXPECT_EQ(profiler.starts, 2);
}

TEST(ProfilerStartRecoveryTest, RecursiveFailureStillAllowsNextAttempt) {
  CountingProfiler profiler;
  profiler.reenter = true;
  profiler.failNext = true;
  EXPECT_THROW(profiler.start(), StartFailure);
  EXPECT_EQ(profiler.starts, 1);
  EXPECT_EQ(profiler.start(), &profiler);
  EXPECT_EQ(profiler.starts, 2);
}

} // namespace
} // namespace proton
