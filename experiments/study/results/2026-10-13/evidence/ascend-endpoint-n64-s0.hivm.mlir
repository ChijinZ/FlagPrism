// -----// IR Dump After GraphSyncSolver (hivm-graph-sync-solver) //----- //
func.func @probe(%arg0: i64 {hacc.arg_type = #hacc.arg_type<ffts_base_address>}, %arg1: memref<?xi8, #hivm.address_space<gm>> {hacc.arg_type = #hacc.arg_type<sync_block_lock>}, %arg2: memref<?xi8, #hivm.address_space<gm>> {hacc.arg_type = #hacc.arg_type<workspace>}, %arg3: memref<?xf32, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 0 : i32}, %arg4: memref<?xf32, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 1 : i32}, %arg5: memref<?xi32, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 1 : i32}, %arg6: i32, %arg7: i32, %arg8: i32) attributes {SyncBlockLockArgIdx = 0 : i64, WorkspaceArgIdx = 1 : i64, func_dyn_memref_args = dense<[false, true, true, true, true, true, false, false, false]> : vector<9xi1>, hacc.entry, hacc.function_kind = #hacc.function_kind<DEVICE>, hivm.func_core_type = #hivm.func_core_type<AIV>, hivm.storage_aligned, mix_mode = "aiv", parallel_mode = "simd"} {
  %c1088_i64 = arith.constant 1088 : i64
  %c1056_i64 = arith.constant 1056 : i64
  %c32_i64 = arith.constant 32 : i64
  %c544_i64 = arith.constant 544 : i64
  %c0_i64 = arith.constant 0 : i64
  %c1_i32 = arith.constant 1 : i32
  %c0 = arith.constant 0 : index
  %c64_i32 = arith.constant 64 : i32
  %cst = arith.constant 1.000000e-03 : f32
  %cst_0 = arith.constant 9.990000e-01 : f32
  %c0_i32 = arith.constant 0 : i32
  hivm.hir.set_mask_norm
  %0 = arith.muli %arg6, %arg7 : i32
  %1 = arith.muli %0, %arg8 : i32
  annotation.mark %1 {logical_block_num} : i32
  %2 = hivm.hir.pointer_cast(%c0_i64) : memref<1xi32, #hivm.address_space<ub>>
  memref.store %c0_i32, %2[%c0] : memref<1xi32, #hivm.address_space<ub>>
  %reinterpret_cast = memref.reinterpret_cast %arg3 to offset: [0], sizes: [128], strides: [1] : memref<?xf32, #hivm.address_space<gm>> to memref<128xf32, strided<[1]>, #hivm.address_space<gm>>
  %3 = hivm.hir.pointer_cast(%c544_i64) : memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.load ins(%reinterpret_cast : memref<128xf32, strided<[1]>, #hivm.address_space<gm>>) outs(%3 : memref<128xf32, #hivm.address_space<ub>>) init_out_buffer = false may_implicit_transpose_with_last_axis = false
  hivm.hir.set_flag[<PIPE_MTE2>, <PIPE_V>, <EVENT_ID0>]
  hivm.hir.pipe_barrier[<PIPE_ALL>]
  %4 = llvm.inline_asm has_side_effects asm_dialect = att "MOV $0, SYS_CNT", "=l"  : () -> i64
  %5 = arith.trunci %4 : i64 to i32
  hivm.hir.wait_flag[<PIPE_MTE2>, <PIPE_V>, <EVENT_ID0>]
  %6 = scf.for %arg9 = %c0_i32 to %c64_i32 step %c1_i32 iter_args(%arg10 = %3) -> (memref<128xf32, #hivm.address_space<ub>>)  : i32 {
    %11 = hivm.hir.pointer_cast(%c32_i64) : memref<128xf32, #hivm.address_space<ub>>
    hivm.hir.pipe_barrier[<PIPE_V>]
    hivm.hir.vmul ins(%arg10, %cst_0 : memref<128xf32, #hivm.address_space<ub>>, f32) outs(%11 : memref<128xf32, #hivm.address_space<ub>>)
    %12 = hivm.hir.pointer_cast(%c544_i64) : memref<128xf32, #hivm.address_space<ub>>
    hivm.hir.pipe_barrier[<PIPE_V>]
    hivm.hir.vadd ins(%11, %cst : memref<128xf32, #hivm.address_space<ub>>, f32) outs(%12 : memref<128xf32, #hivm.address_space<ub>>)
    scf.yield %12 : memref<128xf32, #hivm.address_space<ub>>
  }
  hivm.hir.set_flag[<PIPE_V>, <PIPE_MTE3>, <EVENT_ID0>]
  %7 = llvm.inline_asm has_side_effects asm_dialect = att "MOV $0, SYS_CNT", "=l"  : () -> i64
  %8 = arith.trunci %7 : i64 to i32
  %reinterpret_cast_1 = memref.reinterpret_cast %arg4 to offset: [0], sizes: [128], strides: [1] : memref<?xf32, #hivm.address_space<gm>> to memref<128xf32, strided<[1]>, #hivm.address_space<gm>>
  hivm.hir.wait_flag[<PIPE_V>, <PIPE_MTE3>, <EVENT_ID0>]
  hivm.hir.store ins(%6 : memref<128xf32, #hivm.address_space<ub>>) outs(%reinterpret_cast_1 : memref<128xf32, strided<[1]>, #hivm.address_space<gm>>)
  %9 = hivm.hir.pointer_cast(%c1056_i64) : memref<1xi32, #hivm.address_space<ub>>
  memref.store %5, %9[%c0] : memref<1xi32, #hivm.address_space<ub>>
  hivm.hir.set_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  %reinterpret_cast_2 = memref.reinterpret_cast %arg5 to offset: [0], sizes: [1], strides: [1] : memref<?xi32, #hivm.address_space<gm>> to memref<1xi32, strided<[1]>, #hivm.address_space<gm>>
  hivm.hir.wait_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  hivm.hir.store ins(%9 : memref<1xi32, #hivm.address_space<ub>>) outs(%reinterpret_cast_2 : memref<1xi32, strided<[1]>, #hivm.address_space<gm>>)
  %10 = hivm.hir.pointer_cast(%c1088_i64) : memref<1xi32, #hivm.address_space<ub>>
  memref.store %8, %10[%c0] : memref<1xi32, #hivm.address_space<ub>>
  hivm.hir.set_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  %reinterpret_cast_3 = memref.reinterpret_cast %arg5 to offset: [1], sizes: [1], strides: [1] : memref<?xi32, #hivm.address_space<gm>> to memref<1xi32, strided<[1], offset: 1>, #hivm.address_space<gm>>
  hivm.hir.wait_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  hivm.hir.pipe_barrier[<PIPE_MTE3>]
  hivm.hir.store ins(%10 : memref<1xi32, #hivm.address_space<ub>>) outs(%reinterpret_cast_3 : memref<1xi32, strided<[1], offset: 1>, #hivm.address_space<gm>>)
  %reinterpret_cast_4 = memref.reinterpret_cast %arg5 to offset: [2], sizes: [1], strides: [1] : memref<?xi32, #hivm.address_space<gm>> to memref<1xi32, strided<[1], offset: 2>, #hivm.address_space<gm>>
  hivm.hir.pipe_barrier[<PIPE_MTE3>]
  hivm.hir.store ins(%2 : memref<1xi32, #hivm.address_space<ub>>) outs(%reinterpret_cast_4 : memref<1xi32, strided<[1], offset: 2>, #hivm.address_space<gm>>)
  %reinterpret_cast_5 = memref.reinterpret_cast %arg5 to offset: [3], sizes: [1], strides: [1] : memref<?xi32, #hivm.address_space<gm>> to memref<1xi32, strided<[1], offset: 3>, #hivm.address_space<gm>>
  hivm.hir.pipe_barrier[<PIPE_MTE3>]
  hivm.hir.store ins(%2 : memref<1xi32, #hivm.address_space<ub>>) outs(%reinterpret_cast_5 : memref<1xi32, strided<[1], offset: 3>, #hivm.address_space<gm>>)
  hivm.hir.pipe_barrier[<PIPE_ALL>]
  return
}

warning: linking module '/tmp/tmpz1gu0qwu/kernel.ll': Linking two modules of different data layouts: '/usr/local/python3.11.15/lib/python3.11/site-packages/triton/backends/ascend/lib/libdevice.10.bc' is 'e-i1:8:32-i8:8:32-i16:16:32-i64:64-f16:16:32-v16:16-v32:32-n8:16:32:64-S64' whereas '/tmp/tmpz1gu0qwu/kernel.ll' is 'e-i1:8:32-i8:8:32-i16:16:32-i64:64-f16:16:32-v16:16-v32:32-n64-S64'
 [-Wlinker-warnings]
1 warning generated.
warning: overriding the module target triple with aarch64-unknown-linux-gnu [-Woverride-module]
1 warning generated.
warning: overriding the module target triple with aarch64-unknown-linux-gnu [-Woverride-module]
1 warning generated.
