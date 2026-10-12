// -----// IR Dump After GraphSyncSolver (hivm-graph-sync-solver) //----- //
func.func @matmul_regions_mix_aic(%arg0: i64 {hacc.arg_type = #hacc.arg_type<ffts_base_address>}, %arg1: memref<?xi8, #hivm.address_space<gm>> {hacc.arg_type = #hacc.arg_type<sync_block_lock>}, %arg2: memref<?xi8, #hivm.address_space<gm>> {hacc.arg_type = #hacc.arg_type<workspace>}, %arg3: memref<?xf16, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 0 : i32}, %arg4: memref<?xf16, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 0 : i32}, %arg5: memref<?xf32, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 0 : i32}, %arg6: memref<?xf32, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 1 : i32}, %arg7: memref<?xi32, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 1 : i32}, %arg8: i32, %arg9: i32, %arg10: i32) attributes {SyncBlockLockArgIdx = 0 : i64, WorkspaceArgIdx = 1 : i64, func_dyn_memref_args = dense<[false, true, true, true, true, true, true, true, false, false, false]> : vector<11xi1>, hacc.entry, hacc.function_kind = #hacc.function_kind<DEVICE>, hivm.func_core_type = #hivm.func_core_type<AIC>, hivm.part_of_mix, hivm.storage_aligned, mix_mode = "mix", parallel_mode = "simd"} {
  %c2_i64 = arith.constant 2 : i64
  %c1_i64 = arith.constant 1 : i64
  %c0_i64 = arith.constant 0 : i64
  %c1_i64_0 = arith.constant 1 : i64
  %c512_i64 = arith.constant 512 : i64
  %c0_i64_1 = arith.constant 0 : i64
  %c0_i32 = arith.constant 0 : i32
  %c8_i32 = arith.constant 8 : i32
  %c16_i32 = arith.constant 16 : i32
  %c16 = arith.constant 16 : index
  %cst = arith.constant 0.000000e+00 : f16
  %c0 = arith.constant 0 : index
  %c1_i32 = arith.constant 1 : i32
  hivm.hir.set_ffts_base_addr %arg0
  hivm.hir.set_mask_norm
  %0 = arith.muli %arg8, %arg9 : i32
  %1 = arith.muli %0, %arg10 : i32
  annotation.mark %1 {logical_block_num} : i32
  %2 = hivm.hir.get_block_idx -> i64
  %3 = arith.trunci %2 : i64 to i32
  %4 = arith.divsi %3, %arg10 : i32
  %5 = arith.remsi %4, %arg9 : i32
  %6 = arith.muli %arg10, %arg9 : i32
  %7 = arith.divsi %3, %6 : i32
  %8 = arith.remsi %7, %arg8 : i32
  %9 = llvm.inline_asm has_side_effects asm_dialect = att "MOV $0, SYS_CNT", "=l"  : () -> i64
  %10 = arith.muli %8, %c16_i32 : i32
  %11 = arith.muli %5, %c16_i32 : i32
  %12 = arith.index_cast %10 : i32 to index
  %13 = affine.max affine_map<()[s0] -> (128, s0)>()[%12]
  %14 = affine.min affine_map<()[s0, s1] -> (s1 + 16, s0)>()[%13, %12]
  %15 = affine.min affine_map<()[s0, s1] -> (16, s0 - s1)>()[%14, %12]
  %16 = arith.cmpi slt, %15, %c16 : index
  %17 = arith.index_cast %11 : i32 to index
  %18 = affine.max affine_map<()[s0] -> (128, s0)>()[%17]
  %19 = affine.min affine_map<()[s0, s1] -> (s1 + 16, s0)>()[%18, %17]
  %20 = affine.min affine_map<()[s0, s1] -> (16, s0 - s1)>()[%19, %17]
  %21 = arith.cmpi slt, %20, %c16 : index
  %22 = hivm.hir.pointer_cast(%c0_i64_1) : memref<1x1x16x16xf32, #hivm.address_space<cc>>
  %cast = memref.cast %22 : memref<1x1x16x16xf32, #hivm.address_space<cc>> to memref<?x?x?x?xf32, #hivm.address_space<cc>>
  hivm.hir.set_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID1>]
  hivm.hir.set_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID2>]
  scf.for %arg11 = %c0_i32 to %c8_i32 step %c1_i32  : i32 {
    %27 = arith.index_cast %arg11 : i32 to index
    %28 = arith.index_cast %c0_i32 : i32 to index
    %29 = arith.index_cast %c8_i32 : i32 to index
    %30 = arith.index_cast %c1_i32 : i32 to index
    %31 = affine.apply affine_map<()[s0, s1, s2] -> ((s0 - s1) floordiv s2)>()[%27, %28, %30]
    %32 = arith.index_cast %31 : index to i64
    %33 = arith.muli %arg11, %c16_i32 : i32
    %34 = arith.index_cast %33 : i32 to index
    %35 = affine.apply affine_map<()[s0, s1] -> (s0 + s1 * 128)>()[%34, %12]
    %reinterpret_cast = memref.reinterpret_cast %arg3 to offset: [%35], sizes: [16, 16], strides: [128, 1] : memref<?xf16, #hivm.address_space<gm>> to memref<16x16xf16, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>
    %36 = hivm.hir.pointer_cast(%c0_i64_1) : memref<1x1x16x16xf16, #hivm.address_space<cbuf>>
    %cast_2 = memref.cast %36 : memref<1x1x16x16xf16, #hivm.address_space<cbuf>> to memref<?x?x?x?xf16, #hivm.address_space<cbuf>>
    %37 = affine.max affine_map<()[s0] -> (128, s0)>()[%34]
    %38 = affine.min affine_map<()[s0, s1] -> (s1 + 16, s0)>()[%37, %34]
    %39 = affine.min affine_map<()[s0, s1] -> (16, s0 - s1)>()[%38, %34]
    %40 = arith.cmpi slt, %39, %c16 : index
    %41 = arith.ori %16, %40 : i1
    %subview = memref.subview %reinterpret_cast[0, 0] [%15, %39] [1, 1] : memref<16x16xf16, strided<[128, 1], offset: ?>, #hivm.address_space<gm>> to memref<?x?xf16, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>
    %42 = affine.apply affine_map<()[s0] -> ((s0 + 15) floordiv 16)>()[%15]
    %43 = affine.apply affine_map<()[s0] -> ((s0 + 15) floordiv 16)>()[%39]
    %subview_3 = memref.subview %36[0, 0, 0, 0] [%43, %42, 16, 16] [1, 1, 1, 1] : memref<1x1x16x16xf16, #hivm.address_space<cbuf>> to memref<?x?x16x16xf16, strided<[256, 256, 16, 1]>, #hivm.address_space<cbuf>>
    %cast_4 = memref.cast %subview_3 : memref<?x?x16x16xf16, strided<[256, 256, 16, 1]>, #hivm.address_space<cbuf>> to memref<?x?x?x?xf16, strided<[?, ?, ?, 1], offset: ?>, #hivm.address_space<cbuf>>
    scf.if %41 {
      hivm.hir.set_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID0>]
      %collapse_shape = memref.collapse_shape %36 [[0, 1, 2, 3]] : memref<1x1x16x16xf16, #hivm.address_space<cbuf>> into memref<256xf16, #hivm.address_space<cbuf>>
      hivm.hir.wait_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID0>]
      hivm.hir.vbrc ins(%cst : f16) outs(%collapse_shape : memref<256xf16, #hivm.address_space<cbuf>>)
      hivm.hir.pipe_barrier[<PIPE_MTE2>]
    } {hivm.unlikely_condition}
    hivm.hir.wait_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID1>]
    hivm.hir.nd2nz {dst_continuous} ins(%subview : memref<?x?xf16, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>) outs(%cast_4 : memref<?x?x?x?xf16, strided<[?, ?, ?, 1], offset: ?>, #hivm.address_space<cbuf>>) init_out_buffer = false
    hivm.hir.set_flag[<PIPE_MTE2>, <PIPE_MTE1>, <EVENT_ID0>]
    %44 = affine.apply affine_map<()[s0, s1] -> (s0 + s1 * 128)>()[%17, %34]
    %reinterpret_cast_5 = memref.reinterpret_cast %arg4 to offset: [%44], sizes: [16, 16], strides: [128, 1] : memref<?xf16, #hivm.address_space<gm>> to memref<16x16xf16, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>
    %45 = hivm.hir.pointer_cast(%c512_i64) : memref<1x1x16x16xf16, #hivm.address_space<cbuf>>
    %cast_6 = memref.cast %45 : memref<1x1x16x16xf16, #hivm.address_space<cbuf>> to memref<?x?x?x?xf16, #hivm.address_space<cbuf>>
    %46 = arith.ori %40, %21 : i1
    %subview_7 = memref.subview %reinterpret_cast_5[0, 0] [%39, %20] [1, 1] : memref<16x16xf16, strided<[128, 1], offset: ?>, #hivm.address_space<gm>> to memref<?x?xf16, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>
    %47 = affine.apply affine_map<()[s0] -> ((s0 + 15) floordiv 16)>()[%20]
    %subview_8 = memref.subview %45[0, 0, 0, 0] [%47, %43, 16, 16] [1, 1, 1, 1] : memref<1x1x16x16xf16, #hivm.address_space<cbuf>> to memref<?x?x16x16xf16, strided<[256, 256, 16, 1]>, #hivm.address_space<cbuf>>
    %cast_9 = memref.cast %subview_8 : memref<?x?x16x16xf16, strided<[256, 256, 16, 1]>, #hivm.address_space<cbuf>> to memref<?x?x?x?xf16, strided<[?, ?, ?, 1], offset: ?>, #hivm.address_space<cbuf>>
    scf.if %46 {
      hivm.hir.set_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID0>]
      %collapse_shape = memref.collapse_shape %45 [[0, 1, 2, 3]] : memref<1x1x16x16xf16, #hivm.address_space<cbuf>> into memref<256xf16, #hivm.address_space<cbuf>>
      hivm.hir.wait_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID0>]
      hivm.hir.vbrc ins(%cst : f16) outs(%collapse_shape : memref<256xf16, #hivm.address_space<cbuf>>)
      hivm.hir.pipe_barrier[<PIPE_MTE2>]
    } {hivm.unlikely_condition}
    hivm.hir.wait_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID2>]
    hivm.hir.nd2nz {dst_continuous} ins(%subview_7 : memref<?x?xf16, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>) outs(%cast_9 : memref<?x?x?x?xf16, strided<[?, ?, ?, 1], offset: ?>, #hivm.address_space<cbuf>>) init_out_buffer = false
    hivm.hir.set_flag[<PIPE_MTE2>, <PIPE_MTE1>, <EVENT_ID1>]
    %48 = arith.cmpi eq, %arg11, %c0_i32 : i32
    %c-1_i64 = arith.constant -1 : i64
    hivm.hir.mmadL1 {fixpipe_already_inserted = true} ins(%cast_2, %cast_6, %48, %15, %39, %20 : memref<?x?x?x?xf16, #hivm.address_space<cbuf>>, memref<?x?x?x?xf16, #hivm.address_space<cbuf>>, i1, index, index, index) outs(%cast : memref<?x?x?x?xf32, #hivm.address_space<cc>>) sync_related_args(%c0_i64, %c1_i64_0, %c1_i64, %c2_i64, %32, %c-1_i64, %c-1_i64 : i64, i64, i64, i64, i64, i64, i64)
  }
  hivm.hir.wait_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID1>]
  hivm.hir.wait_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID2>]
  hivm.hir.set_flag[<PIPE_M>, <PIPE_FIX>, <EVENT_ID0>]
  %23 = memref_ext.alloc_workspace() from %arg2 offset = [%c0] : from memref<?xi8, #hivm.address_space<gm>> to memref<16x16xf32, #hivm.address_space<gm>>
  hivm.hir.wait_flag[<PIPE_M>, <PIPE_FIX>, <EVENT_ID0>]
  hivm.hir.fixpipe {dma_mode = #hivm.dma_mode<nz2nd>} ins(%cast : memref<?x?x?x?xf32, #hivm.address_space<cc>>) outs(%23 : memref<16x16xf32, #hivm.address_space<gm>>)
  annotation.mark %23 : memref<16x16xf32, #hivm.address_space<gm>>
  hivm.hir.sync_block_set[<CUBE>, <PIPE_FIX>, <PIPE_S>] flag = 0
  %24 = llvm.inline_asm has_side_effects asm_dialect = att "MOV $0, SYS_CNT", "=l"  : () -> i64
  hivm.hir.pipe_barrier[<PIPE_ALL>]
  %25 = llvm.inline_asm has_side_effects asm_dialect = att "MOV $0, SYS_CNT", "=l"  : () -> i64
  %26 = llvm.inline_asm has_side_effects asm_dialect = att "MOV $0, SYS_CNT", "=l"  : () -> i64
  hivm.hir.pipe_barrier[<PIPE_ALL>]
  return
}

// -----// IR Dump After GraphSyncSolver (hivm-graph-sync-solver) //----- //
func.func @matmul_regions_mix_aiv(%arg0: i64 {hacc.arg_type = #hacc.arg_type<ffts_base_address>}, %arg1: memref<?xi8, #hivm.address_space<gm>> {hacc.arg_type = #hacc.arg_type<sync_block_lock>}, %arg2: memref<?xi8, #hivm.address_space<gm>> {hacc.arg_type = #hacc.arg_type<workspace>}, %arg3: memref<?xf16, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 0 : i32}, %arg4: memref<?xf16, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 0 : i32}, %arg5: memref<?xf32, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 0 : i32}, %arg6: memref<?xf32, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 1 : i32}, %arg7: memref<?xi32, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 1 : i32}, %arg8: i32, %arg9: i32, %arg10: i32) attributes {SyncBlockLockArgIdx = 0 : i64, WorkspaceArgIdx = 1 : i64, func_dyn_memref_args = dense<[false, true, true, true, true, true, true, true, false, false, false]> : vector<11xi1>, hacc.entry, hacc.function_kind = #hacc.function_kind<DEVICE>, hivm.func_core_type = #hivm.func_core_type<AIV>, hivm.part_of_mix, hivm.storage_aligned, mix_mode = "mix", parallel_mode = "simd"} {
  %c1824_i64 = arith.constant 1824 : i64
  %c1792_i64 = arith.constant 1792 : i64
  %c1760_i64 = arith.constant 1760 : i64
  %c1728_i64 = arith.constant 1728 : i64
  %c1696_i64 = arith.constant 1696 : i64
  %c1664_i64 = arith.constant 1664 : i64
  %c1152_i64 = arith.constant 1152 : i64
  %c1088_i64 = arith.constant 1088 : i64
  %c576_i64 = arith.constant 576 : i64
  %c64_i64 = arith.constant 64 : i64
  %c32_i64 = arith.constant 32 : i64
  %c0_i64 = arith.constant 0 : i64
  %cst = arith.constant -1.000000e+00 : f32
  %c1_i32 = arith.constant 1 : i32
  %c16 = arith.constant 16 : index
  %cst_0 = arith.constant 2.000000e+00 : f32
  %cst_1 = arith.constant 1.000000e+00 : f32
  %cst_2 = arith.constant -2.000000e+00 : f32
  %cst_3 = arith.constant 5.000000e-01 : f32
  %cst_4 = arith.constant 0.797884583 : f32
  %cst_5 = arith.constant 4.471500e-02 : f32
  %cst_6 = arith.constant 0.000000e+00 : f32
  %c16_i32 = arith.constant 16 : i32
  %c8_i32 = arith.constant 8 : i32
  %c0_i32 = arith.constant 0 : i32
  %c0 = arith.constant 0 : index
  %0 = arith.muli %arg8, %arg9 : i32
  %1 = arith.muli %0, %arg10 : i32
  %2 = hivm.hir.get_block_idx -> i64
  %3 = arith.trunci %2 : i64 to i32
  %4 = arith.muli %arg10, %arg9 : i32
  %5 = hivm.hir.pointer_cast(%c0_i64) : memref<1xi32, #hivm.address_space<ub>>
  memref.store %c1_i32, %5[%c0] : memref<1xi32, #hivm.address_space<ub>>
  %6 = hivm.hir.pointer_cast(%c32_i64) : memref<1xi32, #hivm.address_space<ub>>
  memref.store %c0_i32, %6[%c0] : memref<1xi32, #hivm.address_space<ub>>
  %7 = hivm.hir.pointer_cast(%c64_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape = memref.collapse_shape %7 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.vbrc ins(%cst_0 : f32) outs(%collapse_shape : memref<128xf32, #hivm.address_space<ub>>)
  %8 = hivm.hir.get_sub_block_idx -> i64
  %9 = arith.index_cast %8 : i64 to index
  %10 = affine.apply affine_map<()[s0] -> (s0 * 8)>()[%9]
  hivm.hir.set_ffts_base_addr %arg0
  hivm.hir.set_mask_norm
  annotation.mark %1 {logical_block_num} : i32
  %11 = arith.divsi %3, %arg10 : i32
  %12 = arith.remsi %11, %arg9 : i32
  %13 = arith.divsi %3, %4 : i32
  %14 = arith.remsi %13, %arg8 : i32
  %15 = arith.muli %14, %c8_i32 : i32
  %16 = arith.addi %15, %12 : i32
  %17 = arith.muli %16, %c8_i32 : i32
  %18 = llvm.inline_asm has_side_effects asm_dialect = att "MOV $0, SYS_CNT", "=l"  : () -> i64
  %19 = arith.trunci %18 : i64 to i32
  %20 = arith.muli %14, %c16_i32 : i32
  %21 = arith.muli %12, %c16_i32 : i32
  %22 = arith.index_cast %20 : i32 to index
  %23 = affine.max affine_map<()[s0] -> (128, s0)>()[%22]
  %24 = affine.min affine_map<()[s0, s1] -> (s1 + 16, s0)>()[%23, %22]
  %25 = affine.min affine_map<()[s0, s1] -> (16, s0 - s1)>()[%24, %22]
  %26 = memref_ext.alloc_workspace() from %arg2 offset = [%c0] : from memref<?xi8, #hivm.address_space<gm>> to memref<16x16xf32, #hivm.address_space<gm>>
  hivm.hir.sync_block_wait[<VECTOR>, <PIPE_FIX>, <PIPE_S>] flag = 0
  %subview = memref.subview %26[%10, 0] [8, 16] [1, 1] : memref<16x16xf32, #hivm.address_space<gm>> to memref<8x16xf32, strided<[16, 1], offset: ?>, #hivm.address_space<gm>>
  %27 = hivm.hir.pointer_cast(%c576_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_7 = memref.collapse_shape %subview [[0, 1]] : memref<8x16xf32, strided<[16, 1], offset: ?>, #hivm.address_space<gm>> into memref<128xf32, strided<[1], offset: ?>, #hivm.address_space<gm>>
  %collapse_shape_8 = memref.collapse_shape %27 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.load ins(%collapse_shape_7 : memref<128xf32, strided<[1], offset: ?>, #hivm.address_space<gm>>) outs(%collapse_shape_8 : memref<128xf32, #hivm.address_space<ub>>) init_out_buffer = false may_implicit_transpose_with_last_axis = false
  %28 = llvm.inline_asm has_side_effects asm_dialect = att "MOV $0, SYS_CNT", "=l"  : () -> i64
  %29 = arith.trunci %28 : i64 to i32
  %30 = arith.index_cast %21 : i32 to index
  %reinterpret_cast = memref.reinterpret_cast %arg5 to offset: [%30], sizes: [1, 16], strides: [16, 1] : memref<?xf32, #hivm.address_space<gm>> to memref<1x16xf32, strided<[16, 1], offset: ?>, #hivm.address_space<gm>>
  %31 = affine.apply affine_map<()[s0, s1] -> (s0 + s1 * 128)>()[%30, %22]
  %32 = affine.max affine_map<()[s0] -> (128, s0)>()[%30]
  %33 = affine.min affine_map<()[s0, s1] -> (s1 + 16, s0)>()[%32, %30]
  %34 = affine.min affine_map<()[s0, s1] -> (16, s0 - s1)>()[%33, %30]
  %35 = affine.apply affine_map<()[s0, s1] -> (s0 - s1)>()[%33, %30]
  %36 = hivm.hir.pointer_cast(%c1088_i64) : memref<1x16xf32, #hivm.address_space<ub>>
  %37 = arith.cmpi slt, %35, %c16 : index
  %subview_9 = memref.subview %reinterpret_cast[0, 0] [1, %35] [1, 1] : memref<1x16xf32, strided<[16, 1], offset: ?>, #hivm.address_space<gm>> to memref<1x?xf32, strided<[16, 1], offset: ?>, #hivm.address_space<gm>>
  %subview_10 = memref.subview %36[0, 0] [1, %35] [1, 1] : memref<1x16xf32, #hivm.address_space<ub>> to memref<1x?xf32, strided<[16, 1]>, #hivm.address_space<ub>>
  scf.if %37 {
    %collapse_shape_39 = memref.collapse_shape %36 [[0, 1]] : memref<1x16xf32, #hivm.address_space<ub>> into memref<16xf32, #hivm.address_space<ub>>
    hivm.hir.vbrc ins(%cst_6 : f32) outs(%collapse_shape_39 : memref<16xf32, #hivm.address_space<ub>>)
    hivm.hir.set_flag[<PIPE_V>, <PIPE_MTE2>, <EVENT_ID0>]
    hivm.hir.wait_flag[<PIPE_V>, <PIPE_MTE2>, <EVENT_ID0>]
  } {hivm.unlikely_condition}
  %collapse_shape_11 = memref.collapse_shape %subview_9 [[0, 1]] : memref<1x?xf32, strided<[16, 1], offset: ?>, #hivm.address_space<gm>> into memref<?xf32, strided<[1], offset: ?>, #hivm.address_space<gm>>
  %collapse_shape_12 = memref.collapse_shape %subview_10 [[0, 1]] : memref<1x?xf32, strided<[16, 1]>, #hivm.address_space<ub>> into memref<?xf32, strided<[1]>, #hivm.address_space<ub>>
  hivm.hir.load ins(%collapse_shape_11 : memref<?xf32, strided<[1], offset: ?>, #hivm.address_space<gm>>) outs(%collapse_shape_12 : memref<?xf32, strided<[1]>, #hivm.address_space<ub>>) pad_mode = <PadValue> pad_value = %cst_6 : f32 left_padding_num = %c0 : index init_out_buffer = false may_implicit_transpose_with_last_axis = false
  hivm.hir.set_flag[<PIPE_MTE2>, <PIPE_V>, <EVENT_ID0>]
  %38 = hivm.hir.pointer_cast(%c576_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  hivm.hir.wait_flag[<PIPE_MTE2>, <PIPE_V>, <EVENT_ID0>]
  hivm.hir.vadd ins(%27, %36 : memref<8x16xf32, #hivm.address_space<ub>>, memref<1x16xf32, #hivm.address_space<ub>>) outs(%38 : memref<8x16xf32, #hivm.address_space<ub>>) broadcast = [0]
  %39 = hivm.hir.pointer_cast(%c1152_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_13 = memref.collapse_shape %38 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  %collapse_shape_14 = memref.collapse_shape %39 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vmul ins(%collapse_shape_13, %cst_5 : memref<128xf32, #hivm.address_space<ub>>, f32) outs(%collapse_shape_14 : memref<128xf32, #hivm.address_space<ub>>)
  %40 = hivm.hir.pointer_cast(%c1152_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_15 = memref.collapse_shape %40 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vmul ins(%collapse_shape_14, %collapse_shape_13 : memref<128xf32, #hivm.address_space<ub>>, memref<128xf32, #hivm.address_space<ub>>) outs(%collapse_shape_15 : memref<128xf32, #hivm.address_space<ub>>)
  %41 = hivm.hir.pointer_cast(%c1152_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_16 = memref.collapse_shape %41 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vmul ins(%collapse_shape_15, %collapse_shape_13 : memref<128xf32, #hivm.address_space<ub>>, memref<128xf32, #hivm.address_space<ub>>) outs(%collapse_shape_16 : memref<128xf32, #hivm.address_space<ub>>)
  %42 = hivm.hir.pointer_cast(%c1152_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_17 = memref.collapse_shape %42 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vadd ins(%collapse_shape_13, %collapse_shape_16 : memref<128xf32, #hivm.address_space<ub>>, memref<128xf32, #hivm.address_space<ub>>) outs(%collapse_shape_17 : memref<128xf32, #hivm.address_space<ub>>)
  %43 = hivm.hir.pointer_cast(%c1152_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_18 = memref.collapse_shape %43 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vmul ins(%collapse_shape_17, %cst_4 : memref<128xf32, #hivm.address_space<ub>>, f32) outs(%collapse_shape_18 : memref<128xf32, #hivm.address_space<ub>>)
  %44 = hivm.hir.pointer_cast(%c576_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_19 = memref.collapse_shape %44 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.vmul ins(%collapse_shape_13, %cst_3 : memref<128xf32, #hivm.address_space<ub>>, f32) outs(%collapse_shape_19 : memref<128xf32, #hivm.address_space<ub>>)
  %45 = hivm.hir.pointer_cast(%c1152_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_20 = memref.collapse_shape %45 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vmul ins(%collapse_shape_18, %cst_2 : memref<128xf32, #hivm.address_space<ub>>, f32) outs(%collapse_shape_20 : memref<128xf32, #hivm.address_space<ub>>)
  %46 = hivm.hir.pointer_cast(%c1152_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_21 = memref.collapse_shape %46 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vexp ins(%collapse_shape_20 : memref<128xf32, #hivm.address_space<ub>>) outs(%collapse_shape_21 : memref<128xf32, #hivm.address_space<ub>>)
  %47 = hivm.hir.pointer_cast(%c1152_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_22 = memref.collapse_shape %47 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vadd ins(%collapse_shape_21, %cst_1 : memref<128xf32, #hivm.address_space<ub>>, f32) outs(%collapse_shape_22 : memref<128xf32, #hivm.address_space<ub>>)
  %48 = hivm.hir.pointer_cast(%c1152_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_23 = memref.collapse_shape %48 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vdiv ins(%collapse_shape, %collapse_shape_22 : memref<128xf32, #hivm.address_space<ub>>, memref<128xf32, #hivm.address_space<ub>>) outs(%collapse_shape_23 : memref<128xf32, #hivm.address_space<ub>>)
  %49 = hivm.hir.pointer_cast(%c1152_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_24 = memref.collapse_shape %49 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vadd ins(%collapse_shape_23, %cst : memref<128xf32, #hivm.address_space<ub>>, f32) outs(%collapse_shape_24 : memref<128xf32, #hivm.address_space<ub>>)
  %50 = hivm.hir.pointer_cast(%c1152_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_25 = memref.collapse_shape %50 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vadd ins(%collapse_shape_24, %cst_1 : memref<128xf32, #hivm.address_space<ub>>, f32) outs(%collapse_shape_25 : memref<128xf32, #hivm.address_space<ub>>)
  %51 = hivm.hir.pointer_cast(%c1152_i64) : memref<8x16xf32, #hivm.address_space<ub>>
  %collapse_shape_26 = memref.collapse_shape %51 [[0, 1]] : memref<8x16xf32, #hivm.address_space<ub>> into memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vmul ins(%collapse_shape_19, %collapse_shape_25 : memref<128xf32, #hivm.address_space<ub>>, memref<128xf32, #hivm.address_space<ub>>) outs(%collapse_shape_26 : memref<128xf32, #hivm.address_space<ub>>)
  hivm.hir.set_flag[<PIPE_V>, <PIPE_MTE3>, <EVENT_ID0>]
  %reinterpret_cast_27 = memref.reinterpret_cast %arg6 to offset: [%31], sizes: [16, 16], strides: [128, 1] : memref<?xf32, #hivm.address_space<gm>> to memref<16x16xf32, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>
  %subview_28 = memref.subview %reinterpret_cast_27[%10, 0] [8, 16] [1, 1] {to_be_bubbled_slice} : memref<16x16xf32, strided<[128, 1], offset: ?>, #hivm.address_space<gm>> to memref<8x16xf32, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>
  %52 = affine.min affine_map<()[s0, s1, s2] -> (16, s1 - s2, s0 * 8)>()[%9, %24, %22]
  %53 = affine.min affine_map<()[s0, s1] -> (8, s0 - s1)>()[%25, %52]
  %subview_29 = memref.subview %51[0, 0] [%53, %34] [1, 1] : memref<8x16xf32, #hivm.address_space<ub>> to memref<?x?xf32, strided<[16, 1]>, #hivm.address_space<ub>>
  %subview_30 = memref.subview %subview_28[0, 0] [%53, %34] [1, 1] : memref<8x16xf32, strided<[128, 1], offset: ?>, #hivm.address_space<gm>> to memref<?x?xf32, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>
  hivm.hir.wait_flag[<PIPE_V>, <PIPE_MTE3>, <EVENT_ID0>]
  hivm.hir.store ins(%subview_29 : memref<?x?xf32, strided<[16, 1]>, #hivm.address_space<ub>>) outs(%subview_30 : memref<?x?xf32, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>) {tiled_op}
  hivm.hir.pipe_barrier[<PIPE_ALL>]
  %54 = llvm.inline_asm has_side_effects asm_dialect = att "MOV $0, SYS_CNT", "=l"  : () -> i64
  %55 = arith.trunci %54 : i64 to i32
  %56 = llvm.inline_asm has_side_effects asm_dialect = att "MOV $0, SYS_CNT", "=l"  : () -> i64
  %57 = arith.trunci %56 : i64 to i32
  %58 = arith.index_cast %17 : i32 to index
  %59 = affine.apply affine_map<()[s0] -> (s0 + 7)>()[%58]
  %60 = affine.apply affine_map<()[s0] -> (s0 + 6)>()[%58]
  %61 = affine.apply affine_map<()[s0] -> (s0 + 5)>()[%58]
  %62 = affine.apply affine_map<()[s0] -> (s0 + 4)>()[%58]
  %63 = affine.apply affine_map<()[s0] -> (s0 + 3)>()[%58]
  %64 = affine.apply affine_map<()[s0] -> (s0 + 2)>()[%58]
  %65 = affine.apply affine_map<()[s0] -> (s0 + 1)>()[%58]
  %66 = hivm.hir.pointer_cast(%c1664_i64) : memref<1xi32, #hivm.address_space<ub>>
  memref.store %19, %66[%c0] : memref<1xi32, #hivm.address_space<ub>>
  hivm.hir.set_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  %reinterpret_cast_31 = memref.reinterpret_cast %arg7 to offset: [%58], sizes: [1], strides: [1] : memref<?xi32, #hivm.address_space<gm>> to memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>
  hivm.hir.wait_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  hivm.hir.store ins(%66 : memref<1xi32, #hivm.address_space<ub>>) outs(%reinterpret_cast_31 : memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>)
  %67 = hivm.hir.pointer_cast(%c1696_i64) : memref<1xi32, #hivm.address_space<ub>>
  memref.store %57, %67[%c0] : memref<1xi32, #hivm.address_space<ub>>
  hivm.hir.set_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  %reinterpret_cast_32 = memref.reinterpret_cast %arg7 to offset: [%65], sizes: [1], strides: [1] : memref<?xi32, #hivm.address_space<gm>> to memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>
  hivm.hir.wait_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  hivm.hir.pipe_barrier[<PIPE_MTE3>]
  hivm.hir.store ins(%67 : memref<1xi32, #hivm.address_space<ub>>) outs(%reinterpret_cast_32 : memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>)
  %68 = hivm.hir.pointer_cast(%c1728_i64) : memref<1xi32, #hivm.address_space<ub>>
  memref.store %29, %68[%c0] : memref<1xi32, #hivm.address_space<ub>>
  hivm.hir.set_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  %reinterpret_cast_33 = memref.reinterpret_cast %arg7 to offset: [%64], sizes: [1], strides: [1] : memref<?xi32, #hivm.address_space<gm>> to memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>
  hivm.hir.wait_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  hivm.hir.pipe_barrier[<PIPE_MTE3>]
  hivm.hir.store ins(%68 : memref<1xi32, #hivm.address_space<ub>>) outs(%reinterpret_cast_33 : memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>)
  %69 = hivm.hir.pointer_cast(%c1760_i64) : memref<1xi32, #hivm.address_space<ub>>
  memref.store %55, %69[%c0] : memref<1xi32, #hivm.address_space<ub>>
  hivm.hir.set_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  %reinterpret_cast_34 = memref.reinterpret_cast %arg7 to offset: [%63], sizes: [1], strides: [1] : memref<?xi32, #hivm.address_space<gm>> to memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>
  hivm.hir.wait_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  hivm.hir.pipe_barrier[<PIPE_MTE3>]
  hivm.hir.store ins(%69 : memref<1xi32, #hivm.address_space<ub>>) outs(%reinterpret_cast_34 : memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>)
  %70 = hivm.hir.pointer_cast(%c1792_i64) : memref<1xi32, #hivm.address_space<ub>>
  memref.store %14, %70[%c0] : memref<1xi32, #hivm.address_space<ub>>
  hivm.hir.set_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  %reinterpret_cast_35 = memref.reinterpret_cast %arg7 to offset: [%62], sizes: [1], strides: [1] : memref<?xi32, #hivm.address_space<gm>> to memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>
  hivm.hir.wait_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  hivm.hir.pipe_barrier[<PIPE_MTE3>]
  hivm.hir.store ins(%70 : memref<1xi32, #hivm.address_space<ub>>) outs(%reinterpret_cast_35 : memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>)
  %71 = hivm.hir.pointer_cast(%c1824_i64) : memref<1xi32, #hivm.address_space<ub>>
  memref.store %12, %71[%c0] : memref<1xi32, #hivm.address_space<ub>>
  hivm.hir.set_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  %reinterpret_cast_36 = memref.reinterpret_cast %arg7 to offset: [%61], sizes: [1], strides: [1] : memref<?xi32, #hivm.address_space<gm>> to memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>
  hivm.hir.wait_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  hivm.hir.pipe_barrier[<PIPE_MTE3>]
  hivm.hir.store ins(%71 : memref<1xi32, #hivm.address_space<ub>>) outs(%reinterpret_cast_36 : memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>)
  %reinterpret_cast_37 = memref.reinterpret_cast %arg7 to offset: [%60], sizes: [1], strides: [1] : memref<?xi32, #hivm.address_space<gm>> to memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>
  hivm.hir.pipe_barrier[<PIPE_MTE3>]
  hivm.hir.store ins(%5 : memref<1xi32, #hivm.address_space<ub>>) outs(%reinterpret_cast_37 : memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>)
  %reinterpret_cast_38 = memref.reinterpret_cast %arg7 to offset: [%59], sizes: [1], strides: [1] : memref<?xi32, #hivm.address_space<gm>> to memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>
  hivm.hir.pipe_barrier[<PIPE_MTE3>]
  hivm.hir.store ins(%6 : memref<1xi32, #hivm.address_space<ub>>) outs(%reinterpret_cast_38 : memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>)
  hivm.hir.pipe_barrier[<PIPE_ALL>]
  return
}

warning: linking module '/tmp/tmpm4j3if8_/kernel.mix_aic.ll': Linking two modules of different data layouts: '/usr/local/python3.11.15/lib/python3.11/site-packages/triton/backends/ascend/lib/libdevice.10.bc' is 'e-i1:8:32-i8:8:32-i16:16:32-i64:64-f16:16:32-v16:16-v32:32-n8:16:32:64-S64' whereas '/tmp/tmpm4j3if8_/kernel.mix_aic.ll' is 'e-i1:8:32-i8:8:32-i16:16:32-i64:64-f16:16:32-v16:16-v32:32-n64-S64'
 [-Wlinker-warnings]
1 warning generated.
warning: linking module '/tmp/tmpm4j3if8_/kernel.mix_aiv.ll': Linking two modules of different data layouts: '/usr/local/python3.11.15/lib/python3.11/site-packages/triton/backends/ascend/lib/libdevice.10.bc' is 'e-i1:8:32-i8:8:32-i16:16:32-i64:64-f16:16:32-v16:16-v32:32-n8:16:32:64-S64' whereas '/tmp/tmpm4j3if8_/kernel.mix_aiv.ll' is 'e-i1:8:32-i8:8:32-i16:16:32-i64:64-f16:16:32-v16:16-v32:32-n64-S64'
 [-Wlinker-warnings]
1 warning generated.
ld.lld: warning: -z separate-code and -z separate-loadable-segments will be ignored
warning: overriding the module target triple with aarch64-unknown-linux-gnu [-Woverride-module]
1 warning generated.
warning: overriding the module target triple with aarch64-unknown-linux-gnu [-Woverride-module]
1 warning generated.
