// -----// IR Dump After GraphSyncSolver (hivm-graph-sync-solver) //----- //
func.func @matmul(%arg0: i64 {hacc.arg_type = #hacc.arg_type<ffts_base_address>}, %arg1: memref<?xi8, #hivm.address_space<gm>> {hacc.arg_type = #hacc.arg_type<sync_block_lock>}, %arg2: memref<?xi8, #hivm.address_space<gm>> {hacc.arg_type = #hacc.arg_type<workspace>}, %arg3: memref<?xf16, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 0 : i32}, %arg4: memref<?xf16, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 0 : i32}, %arg5: memref<?xf32, #hivm.address_space<gm>> {tt.divisibility = 16 : i32}, %arg6: memref<?xf32, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 1 : i32}, %arg7: i32, %arg8: i32, %arg9: i32) attributes {SyncBlockLockArgIdx = 0 : i64, WorkspaceArgIdx = 1 : i64, func_dyn_memref_args = dense<[false, true, true, true, true, true, true, false, false, false]> : vector<10xi1>, hacc.entry, hacc.function_kind = #hacc.function_kind<DEVICE>, hivm.func_core_type = #hivm.func_core_type<AIC>, hivm.storage_aligned, mix_mode = "mix", parallel_mode = "simd"} {
  %c0_i64 = arith.constant 0 : i64
  %c1_i64 = arith.constant 1 : i64
  %c1536_i64 = arith.constant 1536 : i64
  %c512_i64 = arith.constant 512 : i64
  %c1024_i64 = arith.constant 1024 : i64
  %c0_i64_0 = arith.constant 0 : i64
  %c1_i32 = arith.constant 1 : i32
  %cst = arith.constant 0.000000e+00 : f16
  %c16 = arith.constant 16 : index
  %c8_i32 = arith.constant 8 : i32
  %c0_i32 = arith.constant 0 : i32
  %c16_i32 = arith.constant 16 : i32
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
  %21 = hivm.hir.pointer_cast(%c0_i64_0) : memref<1x1x16x16xf32, #hivm.address_space<cc>>
  %cast = memref.cast %21 : memref<1x1x16x16xf32, #hivm.address_space<cc>> to memref<?x?x?x?xf32, #hivm.address_space<cc>>
  hivm.hir.set_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID1>]
  hivm.hir.set_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID2>]
  hivm.hir.set_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID3>]
  hivm.hir.set_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID4>]
  scf.for %arg10 = %c0_i32 to %c8_i32 step %c1_i32  : i32 {
    %25 = arith.index_cast %arg10 : i32 to index
    %26 = arith.index_cast %c0_i32 : i32 to index
    %27 = arith.index_cast %c8_i32 : i32 to index
    %28 = arith.index_cast %c1_i32 : i32 to index
    %29 = affine.apply affine_map<()[s0, s1, s2] -> ((s0 - s1) floordiv s2)>()[%25, %26, %28]
    %30 = arith.index_cast %29 : index to i64
    %31 = arith.index_cast %arg10 : i32 to index
    %32 = arith.index_cast %c0_i32 : i32 to index
    %33 = arith.index_cast %c8_i32 : i32 to index
    %34 = arith.index_cast %c1_i32 : i32 to index
    %35 = affine.apply affine_map<()[s0, s1, s2] -> (((s0 - s1) floordiv s2) mod 2)>()[%31, %32, %34]
    %36 = arith.index_cast %35 : index to i1
    %c3_i64 = arith.constant 3 : i64
    %c4_i64 = arith.constant 4 : i64
    %37 = arith.select %36, %c3_i64, %c4_i64 : i64
    %38 = arith.index_cast %35 : index to i1
    %c1_i64_3 = arith.constant 1 : i64
    %c2_i64 = arith.constant 2 : i64
    %39 = arith.select %38, %c1_i64_3, %c2_i64 : i64
    %40 = hivm.hir.pointer_cast(%c512_i64, %c1536_i64) : memref<1x1x16x16xf16, #hivm.address_space<cbuf>>
    annotation.mark %40 {hivm.multi_buffer = 2 : i32} : memref<1x1x16x16xf16, #hivm.address_space<cbuf>>
    %41 = hivm.hir.pointer_cast(%c0_i64_0, %c1024_i64) : memref<1x1x16x16xf16, #hivm.address_space<cbuf>>
    annotation.mark %41 {hivm.multi_buffer = 2 : i32} : memref<1x1x16x16xf16, #hivm.address_space<cbuf>>
    %42 = arith.muli %arg10, %c16_i32 : i32
    %43 = arith.index_cast %42 : i32 to index
    %44 = affine.apply affine_map<()[s0, s1] -> (s0 + s1 * 128)>()[%43, %11]
    %reinterpret_cast_4 = memref.reinterpret_cast %arg3 to offset: [%44], sizes: [16, 16], strides: [128, 1] : memref<?xf16, #hivm.address_space<gm>> to memref<16x16xf16, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>
    %cast_5 = memref.cast %41 : memref<1x1x16x16xf16, #hivm.address_space<cbuf>> to memref<?x?x?x?xf16, #hivm.address_space<cbuf>>
    %45 = affine.max affine_map<()[s0] -> (128, s0)>()[%43]
    %46 = affine.min affine_map<()[s0, s1] -> (s1 + 16, s0)>()[%45, %43]
    %47 = affine.min affine_map<()[s0, s1] -> (16, s0 - s1)>()[%46, %43]
    %48 = arith.cmpi slt, %47, %c16 : index
    %49 = arith.ori %15, %48 : i1
    %subview_6 = memref.subview %reinterpret_cast_4[0, 0] [%14, %47] [1, 1] : memref<16x16xf16, strided<[128, 1], offset: ?>, #hivm.address_space<gm>> to memref<?x?xf16, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>
    %50 = affine.apply affine_map<()[s0] -> ((s0 + 15) floordiv 16)>()[%14]
    %51 = affine.apply affine_map<()[s0] -> ((s0 + 15) floordiv 16)>()[%47]
    %subview_7 = memref.subview %41[0, 0, 0, 0] [%51, %50, 16, 16] [1, 1, 1, 1] : memref<1x1x16x16xf16, #hivm.address_space<cbuf>> to memref<?x?x16x16xf16, strided<[256, 256, 16, 1]>, #hivm.address_space<cbuf>>
    %cast_8 = memref.cast %subview_7 : memref<?x?x16x16xf16, strided<[256, 256, 16, 1]>, #hivm.address_space<cbuf>> to memref<?x?x?x?xf16, strided<[?, ?, ?, 1], offset: ?>, #hivm.address_space<cbuf>>
    scf.if %49 {
      hivm.hir.set_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID0>]
      %collapse_shape = memref.collapse_shape %41 [[0, 1, 2, 3]] : memref<1x1x16x16xf16, #hivm.address_space<cbuf>> into memref<256xf16, #hivm.address_space<cbuf>>
      hivm.hir.wait_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID0>]
      hivm.hir.vbrc ins(%cst : f16) outs(%collapse_shape : memref<256xf16, #hivm.address_space<cbuf>>)
      hivm.hir.pipe_barrier[<PIPE_MTE2>]
    } {hivm.unlikely_condition}
    hivm.hir.wait_flag[<PIPE_MTE1>, <PIPE_MTE2>, %39]
    hivm.hir.nd2nz {dst_continuous} ins(%subview_6 : memref<?x?xf16, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>) outs(%cast_8 : memref<?x?x?x?xf16, strided<[?, ?, ?, 1], offset: ?>, #hivm.address_space<cbuf>>) init_out_buffer = false
    hivm.hir.set_flag[<PIPE_MTE2>, <PIPE_MTE1>, <EVENT_ID0>]
    %52 = affine.apply affine_map<()[s0, s1] -> (s0 + s1 * 128)>()[%16, %43]
    %reinterpret_cast_9 = memref.reinterpret_cast %arg4 to offset: [%52], sizes: [16, 16], strides: [128, 1] : memref<?xf16, #hivm.address_space<gm>> to memref<16x16xf16, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>
    %cast_10 = memref.cast %40 : memref<1x1x16x16xf16, #hivm.address_space<cbuf>> to memref<?x?x?x?xf16, #hivm.address_space<cbuf>>
    %53 = arith.ori %48, %20 : i1
    %subview_11 = memref.subview %reinterpret_cast_9[0, 0] [%47, %19] [1, 1] : memref<16x16xf16, strided<[128, 1], offset: ?>, #hivm.address_space<gm>> to memref<?x?xf16, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>
    %54 = affine.apply affine_map<()[s0] -> ((s0 + 15) floordiv 16)>()[%19]
    %subview_12 = memref.subview %40[0, 0, 0, 0] [%54, %51, 16, 16] [1, 1, 1, 1] : memref<1x1x16x16xf16, #hivm.address_space<cbuf>> to memref<?x?x16x16xf16, strided<[256, 256, 16, 1]>, #hivm.address_space<cbuf>>
    %cast_13 = memref.cast %subview_12 : memref<?x?x16x16xf16, strided<[256, 256, 16, 1]>, #hivm.address_space<cbuf>> to memref<?x?x?x?xf16, strided<[?, ?, ?, 1], offset: ?>, #hivm.address_space<cbuf>>
    scf.if %53 {
      hivm.hir.set_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID0>]
      %collapse_shape = memref.collapse_shape %40 [[0, 1, 2, 3]] : memref<1x1x16x16xf16, #hivm.address_space<cbuf>> into memref<256xf16, #hivm.address_space<cbuf>>
      hivm.hir.wait_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID0>]
      hivm.hir.vbrc ins(%cst : f16) outs(%collapse_shape : memref<256xf16, #hivm.address_space<cbuf>>)
      hivm.hir.pipe_barrier[<PIPE_MTE2>]
    } {hivm.unlikely_condition}
    hivm.hir.wait_flag[<PIPE_MTE1>, <PIPE_MTE2>, %37]
    hivm.hir.nd2nz {dst_continuous} ins(%subview_11 : memref<?x?xf16, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>) outs(%cast_13 : memref<?x?x?x?xf16, strided<[?, ?, ?, 1], offset: ?>, #hivm.address_space<cbuf>>) init_out_buffer = false
    hivm.hir.set_flag[<PIPE_MTE2>, <PIPE_MTE1>, <EVENT_ID1>]
    %55 = arith.cmpi eq, %arg10, %c0_i32 : i32
    %c-1_i64 = arith.constant -1 : i64
    hivm.hir.mmadL1 {fixpipe_already_inserted = true} ins(%cast_5, %cast_10, %55, %14, %47, %19 : memref<?x?x?x?xf16, #hivm.address_space<cbuf>>, memref<?x?x?x?xf16, #hivm.address_space<cbuf>>, i1, index, index, index) outs(%cast : memref<?x?x?x?xf32, #hivm.address_space<cc>>) sync_related_args(%c0_i64, %c1_i64, %39, %37, %30, %c-1_i64, %c-1_i64 : i64, i64, i64, i64, i64, i64, i64)
  }
  hivm.hir.wait_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID1>]
  hivm.hir.wait_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID2>]
  hivm.hir.wait_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID3>]
  hivm.hir.wait_flag[<PIPE_MTE1>, <PIPE_MTE2>, <EVENT_ID4>]
  hivm.hir.set_flag[<PIPE_M>, <PIPE_FIX>, <EVENT_ID0>]
  %22 = affine.apply affine_map<()[s0, s1] -> (s0 + s1 * 128)>()[%16, %11]
  %reinterpret_cast = memref.reinterpret_cast %arg6 to offset: [%22], sizes: [16, 16], strides: [128, 1] : memref<?xf32, #hivm.address_space<gm>> to memref<16x16xf32, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>
  %23 = affine.apply affine_map<()[s0] -> ((s0 + 15) floordiv 16)>()[%14]
  %24 = affine.apply affine_map<()[s0] -> ((s0 + 15) floordiv 16)>()[%19]
  %subview = memref.subview %21[0, 0, 0, 0] [%24, %23, 16, 16] [1, 1, 1, 1] : memref<1x1x16x16xf32, #hivm.address_space<cc>> to memref<?x?x16x16xf32, strided<[256, 256, 16, 1]>, #hivm.address_space<cc>>
  %cast_1 = memref.cast %subview : memref<?x?x16x16xf32, strided<[256, 256, 16, 1]>, #hivm.address_space<cc>> to memref<?x?x?x?xf32, strided<[?, ?, ?, 1], offset: ?>, #hivm.address_space<cc>>
  %subview_2 = memref.subview %reinterpret_cast[0, 0] [%14, %19] [1, 1] : memref<16x16xf32, strided<[128, 1], offset: ?>, #hivm.address_space<gm>> to memref<?x?xf32, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>
  hivm.hir.wait_flag[<PIPE_M>, <PIPE_FIX>, <EVENT_ID0>]
  hivm.hir.fixpipe {dma_mode = #hivm.dma_mode<nz2nd>} ins(%cast_1 : memref<?x?x?x?xf32, strided<[?, ?, ?, 1], offset: ?>, #hivm.address_space<cc>>) outs(%subview_2 : memref<?x?xf32, strided<[128, 1], offset: ?>, #hivm.address_space<gm>>)
  hivm.hir.pipe_barrier[<PIPE_ALL>]
  return
}

warning: linking module '/tmp/tmpo28q9l8y/kernel.ll': Linking two modules of different data layouts: '/usr/local/python3.11.15/lib/python3.11/site-packages/triton/backends/ascend/lib/libdevice.10.bc' is 'e-i1:8:32-i8:8:32-i16:16:32-i64:64-f16:16:32-v16:16-v32:32-n8:16:32:64-S64' whereas '/tmp/tmpo28q9l8y/kernel.ll' is 'e-i1:8:32-i8:8:32-i16:16:32-i64:64-f16:16:32-v16:16-v32:32-n64-S64'
 [-Wlinker-warnings]
1 warning generated.
warning: overriding the module target triple with aarch64-unknown-linux-gnu [-Woverride-module]
1 warning generated.
warning: overriding the module target triple with aarch64-unknown-linux-gnu [-Woverride-module]
1 warning generated.
