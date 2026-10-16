#ifndef FLAGPRISM_CUPTI_SDK_TEST_SHIM_H_
#define FLAGPRISM_CUPTI_SDK_TEST_SHIM_H_
extern "C" {
void r7Fail(const char *operation, int count);
int r7Calls(const char *operation);
int r7LiveResources();
void r7ExternalSubscriber(int active);
void r7Context(int active);
void r7StallReasons(int count);
}
#endif
