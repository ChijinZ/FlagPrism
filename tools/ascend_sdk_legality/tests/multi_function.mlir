// A successful fallback in one AIV function must not end the module pass.
func.func @fallback_only(%input: memref<63xf32>, %output: memref<63xf32>)
    attributes {hivm.func_core_type = #hivm.func_core_type<AIV>,
                hivm.part_of_mix} {
  %view = bufferization.to_tensor %input restrict writable : memref<63xf32>
  %empty = tensor.empty() : tensor<63xf32>
  %value = hivm.hir.load ins(%view : tensor<63xf32>) outs(%empty : tensor<63xf32>) -> tensor<63xf32>
  hivm.hir.store ins(%value : tensor<63xf32>) outs(%output : memref<63xf32>)
  return
}

func.func @tile_after_fallback(%input: memref<64xf32>, %output: memref<64xf32>)
    attributes {hivm.func_core_type = #hivm.func_core_type<AIV>,
                hivm.part_of_mix} {
  %view = bufferization.to_tensor %input restrict writable : memref<64xf32>
  %empty = tensor.empty() : tensor<64xf32>
  %value = hivm.hir.load ins(%view : tensor<64xf32>) outs(%empty : tensor<64xf32>) -> tensor<64xf32>
  hivm.hir.store ins(%value : tensor<64xf32>) outs(%output : memref<64xf32>)
  return
}
