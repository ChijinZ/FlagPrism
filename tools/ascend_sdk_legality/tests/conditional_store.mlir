// Preserve the source condition around a closed scalar read/modify/write.
func.func @conditional_store(%input: memref<64xf32>, %output: memref<64xf32>,
                             %counter: memref<1xi32>, %active: i1)
    attributes {hivm.func_core_type = #hivm.func_core_type<AIV>,
                hivm.part_of_mix} {
  %zero = arith.constant 0 : index
  %one = arith.constant 1 : i32
  %view = bufferization.to_tensor %input restrict writable : memref<64xf32>
  %empty = tensor.empty() : tensor<64xf32>
  %value = hivm.hir.load ins(%view : tensor<64xf32>) outs(%empty : tensor<64xf32>) -> tensor<64xf32>
  hivm.hir.store ins(%value : tensor<64xf32>) outs(%output : memref<64xf32>)
  scf.if %active {
    %old = memref.load %counter[%zero] : memref<1xi32>
    %next = arith.addi %old, %one : i32
    %scalar = tensor.empty() : tensor<1xi32>
    %updated = tensor.insert %next into %scalar[%zero] : tensor<1xi32>
    hivm.hir.store ins(%updated : tensor<1xi32>) outs(%counter : memref<1xi32>)
  }
  return
}
