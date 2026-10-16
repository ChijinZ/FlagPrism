// Public compiler regression: every memory effect is visible in this file.
// The f32 output can be partitioned; the scalar read/modify/write cannot.
func.func @mixed_store(%input: memref<16xf32>, %output: memref<16xf32>,
                       %counter: memref<1xi32>)
    attributes {hivm.func_core_type = #hivm.func_core_type<AIV>,
                hivm.part_of_mix} {
  %zero = arith.constant 0 : index
  %one = arith.constant 1 : i32
  %empty = tensor.empty() : tensor<16xf32>
  %view = bufferization.to_tensor %input restrict writable : memref<16xf32>
  %value = hivm.hir.load ins(%view : tensor<16xf32>)
      outs(%empty : tensor<16xf32>) -> tensor<16xf32>
  hivm.hir.store ins(%value : tensor<16xf32>) outs(%output : memref<16xf32>)
  %old = memref.load %counter[%zero] : memref<1xi32>
  %next = arith.addi %old, %one : i32
  %scalar = tensor.empty() : tensor<1xi32>
  %updated = tensor.insert %next into %scalar[%zero] : tensor<1xi32>
  hivm.hir.store ins(%updated : tensor<1xi32>) outs(%counter : memref<1xi32>)
  return
}
