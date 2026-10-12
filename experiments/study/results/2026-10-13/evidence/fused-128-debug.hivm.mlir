// -----// IR Dump After GraphSyncSolver (hivm-graph-sync-solver) //----- //
func.func @matmul_mix_aic(%arg0: i64 {hacc.arg_type = #hacc.arg_type<ffts_base_address>}, %arg1: memref<?xi8, #hivm.address_space<gm>> {hacc.arg_type = #hacc.arg_type<sync_block_lock>}, %arg2: memref<?xi8, #hivm.address_space<gm>> {hacc.arg_type = #hacc.arg_type<workspace>}, %arg3: memref<?xf16, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 0 : i32}, %arg4: memref<?xf16, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 0 : i32}, %arg5: memref<?xf32, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 0 : i32}, %arg6: memref<?xf32, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 1 : i32}, %arg7: i32, %arg8: i32, %arg9: i32) attributes {SyncBlockLockArgIdx = 0 : i64, WorkspaceArgIdx = 1 : i64, func_dyn_memref_args = dense<[false, true, true, true, true, true, true, false, false, false]> : vector<10xi1>, hacc.entry, hacc.function_kind = #hacc.function_kind<DEVICE>, hivm.func_core_type = #hivm.func_core_type<AIC>, hivm.part_of_mix, hivm.storage_aligned, mix_mode = "mix", parallel_mode = "simd"} {
  %c2_i64 = arith.constant 2 : i64
  %c1_i64 = arith.constant 1 : i64
  %c0_i64 = arith.constant 0 : i64
  %c1_i64_0 = arith.constant 1 : i64
  %c512_i64 = arith.constant 512 : i64
  %c0_i64_1 = arith.constant 0 : i64
  %c16_i32 = arith.constant 16 : i32
  %c0_i32 = arith.constant 0 : i32
  %c8_i32 = arith.constant 8 : i32
  %c16 = arith.constant 16 : index
  %cst = arith.constant 0.000000e+00 : f16
  %c0 = arith.constant 0 : index
  %c1_i32 = arith.constant 1 : i32
  hivm.hir.set_ffts_base_addr %arg0
  hivm.hir.set_mask_norm
  %0 = arith.muli %arg7, %arg8 : i32
  %1 = arith.muli %0, %arg9 : i32
  annotation.mark %1 {logical_block_num} : i32
  %2 = hivm.hir.get_block_idx -> i64
  %3 = arith.trunci %2 : i64 to i32
  %4 = arith.divsi %3, %arg9 : i32
  %5 = arith.remsi %4, %arg8 : i32
  %6 = arith.muli %arg9, %arg8 : i32
  %7 = arith.divsi %3, %6 : i32
  %8 = arith.remsi %7, %arg7 : i32
  %9 = arith.muli %8, %c16_i32 : i32
  %10 = arith.muli %5, %c16_i32 : i32
  %11 = arith.index_cast %9 : i32 to index
  %12 = affine.max affine_map<()[s0] -> (128, s0)>()[%11]
  %13 = affine.min affine_map<()[s0, s1] -> (s1 + 16, s0)>()[%12, %11]
  %14 = affine.min affine_map<()[s0, s1] -> (16, s0 - s1)>()[%13, %11]
  %15 = arith.cmpi slt, %14, %c16 : index
  %16 = arith.index_cast %10 : i32 to index
  %17 = affine.max affine_map<()[s0] -> (128, s0)>()[%16]
  %18 = affine.min affine_map<()[s0, s1] -> (s1 + 16, s0)>()[%17, %16]
  %19 = affine.min affine_map<()[s0, s1] -> (16, s0 - s1)>()[%18, %16]
  %20 = arith.cmpi slt, %19, %c16 : index
  %21 = hivm.hir.pointer_cast(%c0_i64_1) : memref<1x1x16x16xf32, #hivm.address_space<cc>>
  %cast = memref.cast %21 : memref<1x1x16x16xf32, #hivm.address_space<cc>> to memref<?x?x?x?xf32, #hivm.address_space<cc>>
  hivm.hir.set_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID1>]
  hivm.hir.set_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID2>]
  scf.for %arg10 = %c0_i32 to %c8_i32 step %c1_i32  : i32 {
    %23 = arith.index_cast %arg10 : i32 to index
    %24 = arith.index_cast %c0_i32 : i32 to index
    %25 = arith.index_cast %c8_i32 : i32 to index
    %26 = arith.index_cast %c1_i32 : i32 to index
    %27 = affine.apply affine_map<()[s0, s1, s2] -> ((s0 - s1) floordiv s2)>()[%23, %24, %26]
    %28 = arith.index_cast %27 : index to i64
    %29 = arith.muli %arg10, %c16_i32 : i32
    %30 = arith.index_cast %29 : i32 to index
    %31 = affine.apply affine_map<()[s0, s1] -> (s0 + s1 * 128)>()[%30, %11]
    %reinterpret_cast = memref.reinterpret_cast %arg3 to offset: [%31], sizes: [16, 16], strides: [128, 1] : memref<?xf16, #hivm.address_space<gm>> to memref<16x16xf16, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>
    %32 = hivm.hir.pointer_cast(%c0_i64_1) : memref<1x1x16x16xf16, #hivm.address_space<cbuf>>
    %cast_2 = memref.cast %32 : memref<1x1x16x16xf16, #hivm.address_space<cbuf>> to memref<?x?x?x?xf16, #hivm.address_space<cbuf>>
    %33 = affine.max affine_map<()[s0] -> (128, s0)>()[%30]
    %34 = affine.min affine_map<()[s0, s1] -> (s1 + 16, s0)>()[%33, %30]
    %35 = affine.min affine_map<()[s0, s1] -> (16, s0 - s1)>()[%34, %30]
    %36 = arith.cmpi slt, %35, %c16 : index
    %37 = arith.ori %15, %36 : i1
    %subview = memref.subview %reinterpret_cast[0, 0] [%14, %35] [1, 1] : memref<16x16xf16, strided<[128, 1], offset: ?>, #hivm.address_space<gm>> to memref<?x?xf16, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>
    %38 = affine.apply affine_map<()[s0] -> ((s0 + 15) floordiv 16)>()[%14]
    %39 = affine.apply affine_map<()[s0] -> ((s0 + 15) floordiv 16)>()[%35]
    %subview_3 = memref.subview %32[0, 0, 0, 0] [%39, %38, 16, 16] [1, 1, 1, 1] : memref<1x1x16x16xf16, #hivm.address_space<cbuf>> to memref<?x?x16x16xf16, strided<[256, 256, 16, 1]>, #hivm.address_space<cbuf>>
    %cast_4 = memref.cast %subview_3 : memref<?x?x16x16xf16, strided<[256, 256, 16, 1]>, #hivm.address_space<cbuf>> to memref<?x?x?x?xf16, strided<[?, ?, ?, 1], offset: ?>, #hivm.address_space<cbuf>>
    scf.if %37 {
      hivm.hir.set_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID0>]
      %collapse_shape = memref.collapse_shape %32 [[0, 1, 2, 3]] : memref<1x1x16x16xf16, #hivm.address_space<cbuf>> into memref<256xf16, #hivm.address_space<cbuf>>
      hivm.hir.wait_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID0>]
      hivm.hir.vbrc ins(%cst : f16) outs(%collapse_shape : memref<256xf16, #hivm.address_space<cbuf>>)
      hivm.hir.pipe_barrier[<PIPE_MTE2>]
    } {hivm.unlikely_condition}
    hivm.hir.wait_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID1>]
    hivm.hir.nd2nz {dst_continuous} ins(%subview : memref<?x?xf16, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>) outs(%cast_4 : memref<?x?x?x?xf16, strided<[?, ?, ?, 1], offset: ?>, #hivm.address_space<cbuf>>) init_out_buffer = false
    hivm.hir.set_flag[<PIPE_MTE2>, <PIPE_MTE1>, <EVENT_ID0>]
    %40 = affine.apply affine_map<()[s0, s1] -> (s0 + s1 * 128)>()[%16, %30]
    %reinterpret_cast_5 = memref.reinterpret_cast %arg4 to offset: [%40], sizes: [16, 16], strides: [128, 1] : memref<?xf16, #hivm.address_space<gm>> to memref<16x16xf16, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>
    %41 = hivm.hir.pointer_cast(%c512_i64) : memref<1x1x16x16xf16, #hivm.address_space<cbuf>>
    %cast_6 = memref.cast %41 : memref<1x1x16x16xf16, #hivm.address_space<cbuf>> to memref<?x?x?x?xf16, #hivm.address_space<cbuf>>
    %42 = arith.ori %36, %20 : i1
    %subview_7 = memref.subview %reinterpret_cast_5[0, 0] [%35, %19] [1, 1] : memref<16x16xf16, strided<[128, 1], offset: ?>, #hivm.address_space<gm>> to memref<?x?xf16, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>
    %43 = affine.apply affine_map<()[s0] -> ((s0 + 15) floordiv 16)>()[%19]
    %subview_8 = memref.subview %41[0, 0, 0, 0] [%43, %39, 16, 16] [1, 1, 1, 1] : memref<1x1x16x16xf16, #hivm.address_space<cbuf>> to memref<?x?x16x16xf16, strided<[256, 256, 16, 1]>, #hivm.address_space<cbuf>>
    %cast_9 = memref.cast %subview_8 : memref<?x?x16x16xf16, strided<[256, 256, 16, 1]>, #hivm.address_space<cbuf>> to memref<?x?x?x?xf16, strided<[?, ?, ?, 1], offset: ?>, #hivm.address_space<cbuf>>
    scf.if %42 {
      hivm.hir.set_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID0>]
      %collapse_shape = memref.collapse_shape %41 [[0, 1, 2, 3]] : memref<1x1x16x16xf16, #hivm.address_space<cbuf>> into memref<256xf16, #hivm.address_space<cbuf>>
      hivm.hir.wait_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID0>]
      hivm.hir.vbrc ins(%cst : f16) outs(%collapse_shape : memref<256xf16, #hivm.address_space<cbuf>>)
      hivm.hir.pipe_barrier[<PIPE_MTE2>]
    } {hivm.unlikely_condition}
    hivm.hir.wait_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID2>]
    hivm.hir.nd2nz {dst_continuous} ins(%subview_7 : memref<?x?xf16, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>) outs(%cast_9 : memref<?x?x?x?xf16, strided<[?, ?, ?, 1], offset: ?>, #hivm.address_space<cbuf>>) init_out_buffer = false
    hivm.hir.set_flag[<PIPE_MTE2>, <PIPE_MTE1>, <EVENT_ID1>]
    %44 = arith.cmpi eq, %arg10, %c0_i32 : i32
    %c-1_i64 = arith.constant -1 : i64
    hivm.hir.mmadL1 {fixpipe_already_inserted = true} ins(%cast_2, %cast_6, %44, %14, %35, %19 : memref<?x?x?x?xf16, #hivm.address_space<cbuf>>, memref<?x?x?x?xf16, #hivm.address_space<cbuf>>, i1, index, index, index) outs(%cast : memref<?x?x?x?xf32, #hivm.address_space<cc>>) sync_related_args(%c0_i64, %c1_i64_0, %c1_i64, %c2_i64, %28, %c-1_i64, %c-1_i64 : i64, i64, i64, i64, i64, i64, i64)
  }
  hivm.hir.wait_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID1>]
  hivm.hir.wait_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID2>]
  hivm.hir.set_flag[<PIPE_M>, <PIPE_FIX>, <EVENT_ID0>]
  %22 = memref_ext.alloc_workspace() from %arg2 offset = [%c0] : from memref<?xi8, #hivm.address_space<gm>> to memref<16x16xf32, #hivm.address_space<gm>>
  hivm.hir.wait_flag[<PIPE_M>, <PIPE_FIX>, <EVENT_ID0>]
  hivm.hir.fixpipe {dma_mode = #hivm.dma_mode<nz2nd>} ins(%cast : memref<?x?x?x?xf32, #hivm.address_space<cc>>) outs(%22 : memref<16x16xf32, #hivm.address_space<gm>>)
  annotation.mark %22 : memref<16x16xf32, #hivm.address_space<gm>>
  hivm.hir.sync_block_set[<CUBE>, <PIPE_FIX>, <PIPE_S>] flag = 0
  hivm.hir.pipe_barrier[<PIPE_ALL>]
  return
}

// -----// IR Dump After GraphSyncSolver (hivm-graph-sync-solver) //----- //
func.func @matmul_mix_aiv(%arg0: i64 {hacc.arg_type = #hacc.arg_type<ffts_base_address>}, %arg1: memref<?xi8, #hivm.address_space<gm>> {hacc.arg_type = #hacc.arg_type<sync_block_lock>}, %arg2: memref<?xi8, #hivm.address_space<gm>> {hacc.arg_type = #hacc.arg_type<workspace>}, %arg3: memref<?xf16, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 0 : i32}, %arg4: memref<?xf16, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 0 : i32}, %arg5: memref<?xf32, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 0 : i32}, %arg6: memref<?xf32, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 1 : i32}, %arg7: i32, %arg8: i32, %arg9: i32) attributes {SyncBlockLockArgIdx = 0 : i64, WorkspaceArgIdx = 1 : i64, func_dyn_memref_args = dense<[false, true, true, true, true, true, true, false, false, false]> : vector<10xi1>, hacc.entry, hacc.function_kind = #hacc.function_kind<DEVICE>, hivm.func_core_type = #hivm.func_core_type<AIV>, hivm.part_of_mix, hivm.storage_aligned, mix_mode = "mix", parallel_mode = "simd"} {
  %c1088_i64 = arith.constant 1088 : i64
  %c1024_i64 = arith.constant 1024 : i64
  %c512_i64 = arith.constant 512 : i64
  %c0_i64 = arith.constant 0 : i64
  %cst = arith.constant -1.000000e+00 : f32
  %c16 = arith.constant 16 : index
  %cst_0 = arith.constant 5.000000e-01 : f32
  %cst_1 = arith.constant 2.000000e+00 : f32
  %cst_2 = arith.constant 1.000000e+00 : f32
  %cst_3 = arith.constant -2.000000e+00 : f32
  %cst_4 = arith.constant 0.797884583 : f32
  %cst_5 = arith.constant 4.471500e-02 : f32
  %c16_i32 = arith.constant 16 : i32
  %cst_6 = arith.constant 0.000000e+00 : f32
  %c0 = arith.constant 0 : index
  %0 = arith.muli %arg7, %arg8 : i32
  %1 = arith.muli %0, %arg9 : i32
  %2 = hivm.hir.get_block_idx -> i64
  %3 = arith.trunci %2 : i64 to i32
  %4 = arith.muli %arg9, %arg8 : i32
  %5 = hivm.hir.pointer_cast(%c0_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape = memref.collapse_shape %5 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.vbrc ins(%cst_1 : f32) outs(%collapse_shape : memref<128xf32, #hivm.address_space<ub>>)
  %6 = hivm.hir.get_sub_block_idx -> i64
  %7 = arith.index_cast %6 : i64 to index
  %8 = affine.apply affine_map<()[s0] -> (s0 * 8)>()[%7]
  hivm.hir.set_ffts_base_addr %arg0
  hivm.hir.set_mask_norm
  annotation.mark %1 {logical_block_num} : i32
  %9 = arith.divsi %3, %arg9 : i32
  %10 = arith.remsi %9, %arg8 : i32
  %11 = arith.divsi %3, %4 : i32
  %12 = arith.remsi %11, %arg7 : i32
  %13 = arith.muli %12, %c16_i32 : i32
  %14 = arith.muli %10, %c16_i32 : i32
  %15 = arith.index_cast %13 : i32 to index
  %16 = affine.max affine_map<()[s0] -> (128, s0)>()[%15]
  %17 = affine.min affine_map<()[s0, s1] -> (s1 + 16, s0)>()[%16, %15]
  %18 = affine.min affine_map<()[s0, s1] -> (16, s0 - s1)>()[%17, %15]
  %19 = memref_ext.alloc_workspace() from %arg2 offset = [%c0] : from memref<?xi8, #hivm.address_space<gm>> to memref<16x16xf32, #hivm.address_space<gm>>
  hivm.hir.sync_block_wait[<VECTOR>, <PIPE_FIX>, <PIPE_S>] flag = 0
  %subview = memref.subview %19[%8, 0] [8, 16] [1, 1] : memref<16x16xf32, #hivm.address_space<gm>> to memref<8x16xf32, strided<[16, 1], offset: ?>, #hivm.address_space<gm>>
  %20 = hivm.hir.pointer_cast(%c512_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_7 = memref.collapse_shape %subview [[0, 1]] : memref<8x16xf32, strided<[16, 1], offset: ?>, #hivm.address_space<gm>> into memref<128xf32, strided<[1], offset: ?>, #hivm.address_space<gm>>
  %collapse_shape_8 = memref.collapse_shape %20 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.load ins(%collapse_shape_7 : memref<128xf32, strided<[1], offset: ?>, #hivm.address_space<gm>>) outs(%collapse_shape_8 : memref<128xf32, #hivm.address_space<ub>>) init_out_buffer = false may_implicit_transpose_with_last_axis = false
  %21 = arith.index_cast %14 : i32 to index
  %reinterpret_cast = memref.reinterpret_cast %arg5 to offset: [%21], sizes: [1, 16], strides: [16, 1] : memref<?xf32, #hivm.address_space<gm>> to memref<1x16xf32, strided<[16, 1], offset: ?>, #hivm.address_space<gm>>
  %22 = affine.apply affine_map<()[s0, s1] -> (s0 + s1 * 128)>()[%21, %15]
  %23 = affine.max affine_map<()[s0] -> (128, s0)>()[%21]
  %24 = affine.min affine_map<()[s0, s1] -> (s1 + 16, s0)>()[%23, %21]
  %25 = affine.min affine_map<()[s0, s1] -> (16, s0 - s1)>()[%24, %21]
  %26 = affine.apply affine_map<()[s0, s1] -> (s0 - s1)>()[%24, %21]
  %27 = hivm.hir.pointer_cast(%c1024_i64) : memref<1x16xf32, #hivm.address_space<ub>>
  %28 = arith.cmpi slt, %26, %c16 : index
  %subview_9 = memref.subview %reinterpret_cast[0, 0] [1, %26] [1, 1] : memref<1x16xf32, strided<[16, 1], offset: ?>, #hivm.address_space<gm>> to memref<1x?xf32, strided<[16, 1], offset: ?>, #hivm.address_space<gm>>
  %subview_10 = memref.subview %27[0, 0] [1, %26] [1, 1] : memref<1x16xf32, #hivm.address_space<ub>> to memref<1x?xf32, strided<[16, 1]>, #hivm.address_space<ub>>
  scf.if %28 {
    %collapse_shape_31 = memref.collapse_shape %27 [[0, 1]] : memref<1x16xf32, #hivm.address_space<ub>> into memref<16xf32, #hivm.address_space<ub>>
    hivm.hir.vbrc ins(%cst_6 : f32) outs(%collapse_shape_31 : memref<16xf32, #hivm.address_space<ub>>)
    hivm.hir.set_flag[<PIPE_V>, <PIPE_MTE2>, <EVENT_ID0>]
    hivm.hir.wait_flag[<PIPE_V>, <PIPE_MTE2>, <EVENT_ID0>]
  } {hivm.unlikely_condition}
  %collapse_shape_11 = memref.collapse_shape %subview_9 [[0, 1]] : memref<1x?xf32, strided<[16, 1], offset: ?>, #hivm.address_space<gm>> into memref<?xf32, strided<[1], offset: ?>, #hivm.address_space<gm>>
  %collapse_shape_12 = memref.collapse_shape %subview_10 [[0, 1]] : memref<1x?xf32, strided<[16, 1]>, #hivm.address_space<ub>> into memref<?xf32, strided<[1]>, #hivm.address_space<ub>>
  hivm.hir.load ins(%collapse_shape_11 : memref<?xf32, strided<[1], offset: ?>, #hivm.address_space<gm>>) outs(%collapse_shape_12 : memref<?xf32, strided<[1]>, #hivm.address_space<ub>>) pad_mode = <PadValue> pad_value = %cst_6 : f32 left_padding_num = %c0 : index init_out_buffer = false may_implicit_transpose_with_last_axis = false
  hivm.hir.set_flag[<PIPE_MTE2>, <PIPE_V>, <EVENT_ID0>]
  %29 = hivm.hir.pointer_cast(%c512_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  hivm.hir.wait_flag[<PIPE_MTE2>, <PIPE_V>, <EVENT_ID0>]
  hivm.hir.vadd ins(%20, %27 : memref<8x16xf32, #hivm.address_space<ub>>, memref<1x16xf32, #hivm.address_space<ub>>) outs(%29 : memref<8x16xf32, #hivm.address_space<ub>>) broadcast = [0]
  %30 = hivm.hir.pointer_cast(%c1088_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_13 = memref.collapse_shape %29 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  %collapse_shape_14 = memref.collapse_shape %30 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vmul ins(%collapse_shape_13, %cst_5 : memref<128xf32, #hivm.address_space<ub>>, f32) outs(%collapse_shape_14 : memref<128xf32, #hivm.address_space<ub>>)
  %31 = hivm.hir.pointer_cast(%c1088_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_15 = memref.collapse_shape %31 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vmul ins(%collapse_shape_14, %collapse_shape_13 : memref<128xf32, #hivm.address_space<ub>>, memref<128xf32, #hivm.address_space<ub>>) outs(%collapse_shape_15 : memref<128xf32, #hivm.address_space<ub>>)
  %32 = hivm.hir.pointer_cast(%c1088_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_16 = memref.collapse_shape %32 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vmul ins(%collapse_shape_15, %collapse_shape_13 : memref<128xf32, #hivm.address_space<ub>>, memref<128xf32, #hivm.address_space<ub>>) outs(%collapse_shape_16 : memref<128xf32, #hivm.address_space<ub>>)
  %33 = hivm.hir.pointer_cast(%c1088_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_17 = memref.collapse_shape %33 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vadd ins(%collapse_shape_13, %collapse_shape_16 : memref<128xf32, #hivm.address_space<ub>>, memref<128xf32, #hivm.address_space<ub>>) outs(%collapse_shape_17 : memref<128xf32, #hivm.address_space<ub>>)
  %34 = hivm.hir.pointer_cast(%c1088_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_18 = memref.collapse_shape %34 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vmul ins(%collapse_shape_17, %cst_4 : memref<128xf32, #hivm.address_space<ub>>, f32) outs(%collapse_shape_18 : memref<128xf32, #hivm.address_space<ub>>)
  %35 = hivm.hir.pointer_cast(%c1088_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_19 = memref.collapse_shape %35 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vmul ins(%collapse_shape_18, %cst_3 : memref<128xf32, #hivm.address_space<ub>>, f32) outs(%collapse_shape_19 : memref<128xf32, #hivm.address_space<ub>>)
  %36 = hivm.hir.pointer_cast(%c1088_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_20 = memref.collapse_shape %36 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vexp ins(%collapse_shape_19 : memref<128xf32, #hivm.address_space<ub>>) outs(%collapse_shape_20 : memref<128xf32, #hivm.address_space<ub>>)
  %37 = hivm.hir.pointer_cast(%c1088_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_21 = memref.collapse_shape %37 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vadd ins(%collapse_shape_20, %cst_2 : memref<128xf32, #hivm.address_space<ub>>, f32) outs(%collapse_shape_21 : memref<128xf32, #hivm.address_space<ub>>)
  %38 = hivm.hir.pointer_cast(%c1088_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_22 = memref.collapse_shape %38 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vdiv ins(%collapse_shape, %collapse_shape_21 : memref<128xf32, #hivm.address_space<ub>>, memref<128xf32, #hivm.address_space<ub>>) outs(%collapse_shape_22 : memref<128xf32, #hivm.address_space<ub>>)
  %39 = hivm.hir.pointer_cast(%c1088_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_23 = memref.collapse_shape %39 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vadd ins(%collapse_shape_22, %cst : memref<128xf32, #hivm.address_space<ub>>, f32) outs(%collapse_shape_23 : memref<128xf32, #hivm.address_space<ub>>)
  %40 = hivm.hir.pointer_cast(%c512_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_24 = memref.collapse_shape %40 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.vmul ins(%collapse_shape_13, %cst_0 : memref<128xf32, #hivm.address_space<ub>>, f32) outs(%collapse_shape_24 : memref<128xf32, #hivm.address_space<ub>>)
  %41 = hivm.hir.pointer_cast(%c1088_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_25 = memref.collapse_shape %41 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vadd ins(%collapse_shape_23, %cst_2 : memref<128xf32, #hivm.address_space<ub>>, f32) outs(%collapse_shape_25 : memref<128xf32, #hivm.address_space<ub>>)
  %42 = hivm.hir.pointer_cast(%c512_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_26 = memref.collapse_shape %42 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vmul ins(%collapse_shape_24, %collapse_shape_25 : memref<128xf32, #hivm.address_space<ub>>, memref<128xf32, #hivm.address_space<ub>>) outs(%collapse_shape_26 : memref<128xf32, #hivm.address_space<ub>>)
  hivm.hir.set_flag[<PIPE_V>, <PIPE_MTE3>, <EVENT_ID0>]
  %reinterpret_cast_27 = memref.reinterpret_cast %arg6 to offset: [%22], sizes: [16, 16], strides: [128, 1] : memref<?xf32, #hivm.address_space<gm>> to memref<16x16xf32, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>
  %subview_28 = memref.subview %reinterpret_cast_27[%8, 0] [8, 16] [1, 1] {to_be_bubbled_slice} : memref<16x16xf32, strided<[128, 1], offset: ?>, #hivm.address_space<gm>> to memref<8x16xf32, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>
  %43 = affine.min affine_map<()[s0, s1, s2] -> (16, s1 - s2, s0 * 8)>()[%7, %17, %15]
  %44 = affine.min affine_map<()[s0, s1] -> (8, s0 - s1)>()[%18, %43]
  %subview_29 = memref.subview %42[0, 0] [%44, %25] [1, 1] : memref<8x16xf32, #hivm.address_space<ub>> to memref<?x?xf32, strided<[16, 1]>, #hivm.address_space<ub>>
  %subview_30 = memref.subview %subview_28[0, 0] [%44, %25] [1, 1] : memref<8x16xf32, strided<[128, 1], offset: ?>, #hivm.address_space<gm>> to memref<?x?xf32, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>
  hivm.hir.wait_flag[<PIPE_V>, <PIPE_MTE3>, <EVENT_ID0>]
  hivm.hir.store ins(%subview_29 : memref<?x?xf32, strided<[16, 1]>, #hivm.address_space<ub>>) outs(%subview_30 : memref<?x?xf32, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>) {tiled_op}
  hivm.hir.pipe_barrier[<PIPE_ALL>]
  return
}

warning: linking module '/tmp/tmpliwm5a8x/kernel.mix_aic.ll': Linking two modules of different data layouts: '/usr/local/python3.11.15/lib/python3.11/site-packages/triton/backends/ascend/lib/libdevice.10.bc' is 'e-i1:8:32-i8:8:32-i16:16:32-i64:64-f16:16:32-v16:16-v32:32-n8:16:32:64-S64' whereas '/tmp/tmpliwm5a8x/kernel.mix_aic.ll' is 'e-i1:8:32-i8:8:32-i16:16:32-i64:64-f16:16:32-v16:16-v32:32-n64-S64'
 [-Wlinker-warnings]
1 warning generated.
warning: linking module '/tmp/tmpliwm5a8x/kernel.mix_aiv.ll': Linking two modules of different data layouts: '/usr/local/python3.11.15/lib/python3.11/site-packages/triton/backends/ascend/lib/libdevice.10.bc' is 'e-i1:8:32-i8:8:32-i16:16:32-i64:64-f16:16:32-v16:16-v32:32-n8:16:32:64-S64' whereas '/tmp/tmpliwm5a8x/kernel.mix_aiv.ll' is 'e-i1:8:32-i8:8:32-i16:16:32-i64:64-f16:16:32-v16:16-v32:32-n64-S64'
 [-Wlinker-warnings]
1 warning generated.
ld.lld: warning: -z separate-code and -z separate-loadable-segments will be ignored
warning: overriding the module target triple with aarch64-unknown-linux-gnu [-Woverride-module]
1 warning generated.
warning: overriding the module target triple with aarch64-unknown-linux-gnu [-Woverride-module]
1 warning generated.
