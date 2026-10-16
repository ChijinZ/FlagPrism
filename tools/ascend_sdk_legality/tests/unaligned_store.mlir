// Existing global dimension analysis rejects odd-sized load/store partitioning.
// Preserve its valid fallback for both ordinary non-scalar external stores.
func.func @mixed_unaligned_store(%even: memref<64xf32>, %odd: memref<63xf32>,
                                %out_even: memref<64xf32>, %out_odd: memref<63xf32>)
    attributes {hivm.func_core_type = #hivm.func_core_type<AIV>,
                hivm.part_of_mix} {
  %a = bufferization.to_tensor %even restrict writable : memref<64xf32>
  %b = bufferization.to_tensor %odd restrict writable : memref<63xf32>
  %ea = tensor.empty() : tensor<64xf32>
  %eb = tensor.empty() : tensor<63xf32>
  %va = hivm.hir.load ins(%a : tensor<64xf32>) outs(%ea : tensor<64xf32>) -> tensor<64xf32>
  %vb = hivm.hir.load ins(%b : tensor<63xf32>) outs(%eb : tensor<63xf32>) -> tensor<63xf32>
  hivm.hir.store ins(%va : tensor<64xf32>) outs(%out_even : memref<64xf32>)
  hivm.hir.store ins(%vb : tensor<63xf32>) outs(%out_odd : memref<63xf32>)
  return
}
