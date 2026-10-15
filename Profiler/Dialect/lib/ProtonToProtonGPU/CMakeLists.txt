add_triton_library(ProtonToProtonGPU
  ProtonToProtonGPUPass.cpp
  AutomaticScopes.cpp

  DEPENDS
  ProtonToProtonGPUIncGen
  LINK_LIBS PUBLIC
  TritonIR
  TritonGPUIR
  ProtonIR
  ProtonGPUIR
)
