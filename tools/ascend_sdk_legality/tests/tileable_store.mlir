// Positive control: the fix must preserve successful two-subblock tiling.
func.func @tileable_store(%input: memref<16xf32>, %output: memref<16xf32>)
    attributes {hivm.func_core_type = #hivm.func_core_type<AIV>,
                hivm.part_of_mix} {
  %empty = tensor.empty() : tensor<16xf32>
  %view = bufferization.to_tensor %input restrict writable : memref<16xf32>
  %value = hivm.hir.load ins(%view : tensor<16xf32>)
      outs(%empty : tensor<16xf32>) -> tensor<16xf32>
  hivm.hir.store ins(%value : tensor<16xf32>) outs(%output : memref<16xf32>)
  return
}
