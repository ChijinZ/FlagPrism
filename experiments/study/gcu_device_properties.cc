#include <tops/tops_runtime_api.h>
#include <cstdio>
int main() {
  int count=0;auto count_status=topsGetDeviceCount(&count);
  topsDeviceProp_t prop{};auto status=topsGetDeviceProperties(&prop,1);
  std::printf("{\"device\":1,\"count_status\":%d,\"count\":%d,\"status\":%d,\"name\":\"%s\",\"arch\":\"%s\",\"clockRate_kHz\":%d,\"clockInstructionRate_kHz\":%d}\n",int(count_status),count,int(status),prop.name,prop.gcuArchName,prop.clockRate,prop.clockInstructionRate);
  return int(status);
}
