// -----// IR Dump After GraphSyncSolver (hivm-graph-sync-solver) //----- //
func.func @softmax_regions(%arg0: i64 {hacc.arg_type = #hacc.arg_type<ffts_base_address>}, %arg1: memref<?xi8, #hivm.address_space<gm>> {hacc.arg_type = #hacc.arg_type<sync_block_lock>}, %arg2: memref<?xi8, #hivm.address_space<gm>> {hacc.arg_type = #hacc.arg_type<workspace>}, %arg3: memref<?xf32, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 0 : i32}, %arg4: memref<?xf32, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 1 : i32}, %arg5: memref<?xi32, #hivm.address_space<gm>> {tt.divisibility = 16 : i32, tt.tensor_kind = 1 : i32}, %arg6: i32, %arg7: i32, %arg8: i32) attributes {SyncBlockLockArgIdx = 0 : i64, WorkspaceArgIdx = 1 : i64, func_dyn_memref_args = dense<[false, true, true, true, true, true, false, false, false]> : vector<9xi1>, hacc.entry, hacc.function_kind = #hacc.function_kind<DEVICE>, hivm.func_core_type = #hivm.func_core_type<AIV>, hivm.storage_aligned, mix_mode = "aiv", parallel_mode = "simd"} {
  %c2080_i64 = arith.constant 2080 : i64
  %c2048_i64 = arith.constant 2048 : i64
  %c2016_i64 = arith.constant 2016 : i64
  %c1984_i64 = arith.constant 1984 : i64
  %c1952_i64 = arith.constant 1952 : i64
  %c1920_i64 = arith.constant 1920 : i64
  %c1408_i64 = arith.constant 1408 : i64
  %c1376_i64 = arith.constant 1376 : i64
  %c1120_i64 = arith.constant 1120 : i64
  %c1088_i64 = arith.constant 1088 : i64
  %c64_i64 = arith.constant 64 : i64
  %c32_i64 = arith.constant 32 : i64
  %c0_i64 = arith.constant 0 : i64
  %cst = arith.constant 0.000000e+00 : f32
  %c1_i32 = arith.constant 1 : i32
  %c0 = arith.constant 0 : index
  %cst_0 = arith.constant 0xFF800000 : f32
  %c1 = arith.constant 1 : index
  %c256 = arith.constant 256 : index
  %c256_i32 = arith.constant 256 : i32
  %c32_i32 = arith.constant 32 : i32
  %c8_i32 = arith.constant 8 : i32
  %c0_i32 = arith.constant 0 : i32
  hivm.hir.set_mask_norm
  %0 = arith.muli %arg6, %arg7 : i32
  %1 = arith.muli %0, %arg8 : i32
  annotation.mark %1 {logical_block_num} : i32
  %2 = hivm.hir.get_block_idx -> i64
  %3 = arith.trunci %2 : i64 to i32
  %4 = arith.muli %arg8, %arg7 : i32
  %5 = arith.divsi %3, %4 : i32
  %6 = arith.remsi %5, %arg6 : i32
  %7 = hivm.hir.pointer_cast(%c0_i64) : memref<1xi32, #hivm.address_space<ub>>
  memref.store %c1_i32, %7[%c0] : memref<1xi32, #hivm.address_space<ub>>
  %8 = hivm.hir.pointer_cast(%c32_i64) : memref<1xi32, #hivm.address_space<ub>>
  memref.store %c0_i32, %8[%c0] : memref<1xi32, #hivm.address_space<ub>>
  %9 = arith.muli %6, %c8_i32 : i32
  %10 = llvm.inline_asm has_side_effects asm_dialect = att "MOV $0, SYS_CNT", "=l"  : () -> i64
  %11 = arith.trunci %10 : i64 to i32
  %12 = arith.cmpi slt, %6, %c32_i32 : i32
  %13 = arith.muli %6, %c256_i32 : i32
  %14 = arith.index_cast %13 : i32 to index
  %reinterpret_cast = memref.reinterpret_cast %arg3 to offset: [%14], sizes: [1, 256], strides: [256, 1] : memref<?xf32, #hivm.address_space<gm>> to memref<1x256xf32, strided<[256, 1], offset: ?>, #hivm.address_space<gm>>
  %15 = hivm.hir.pointer_cast(%c64_i64) : memref<1x256xf32, #hivm.address_space<ub>>
  %16 = arith.index_castui %12 : i1 to index
  %17 = affine.min affine_map<()[s0] -> (1, s0)>()[%16]
  %18 = affine.min affine_map<()[s0] -> (256, s0 * 256)>()[%16]
  %19 = arith.cmpi slt, %17, %c1 : index
  %20 = arith.cmpi slt, %18, %c256 : index
  %21 = arith.ori %19, %20 : i1
  %subview = memref.subview %reinterpret_cast[0, 0] [%17, %18] [1, 1] : memref<1x256xf32, strided<[256, 1], offset: ?>, #hivm.address_space<gm>> to memref<?x?xf32, strided<[256, 1], offset: ?>, #hivm.address_space<gm>>
  %subview_1 = memref.subview %15[0, 0] [%17, %18] [1, 1] : memref<1x256xf32, #hivm.address_space<ub>> to memref<?x?xf32, strided<[256, 1]>, #hivm.address_space<ub>>
  scf.if %21 {
    %collapse_shape_18 = memref.collapse_shape %15 [[0, 1]] : memref<1x256xf32, #hivm.address_space<ub>> into memref<256xf32, #hivm.address_space<ub>>
    hivm.hir.vbrc ins(%cst_0 : f32) outs(%collapse_shape_18 : memref<256xf32, #hivm.address_space<ub>>)
    hivm.hir.set_flag[<PIPE_V>, <PIPE_MTE2>, <EVENT_ID0>]
    hivm.hir.wait_flag[<PIPE_V>, <PIPE_MTE2>, <EVENT_ID0>]
  } {hivm.unlikely_condition}
  hivm.hir.load ins(%subview : memref<?x?xf32, strided<[256, 1], offset: ?>, #hivm.address_space<gm>>) outs(%subview_1 : memref<?x?xf32, strided<[256, 1]>, #hivm.address_space<ub>>) pad_mode = <PadValue> pad_value = %cst_0 : f32 left_padding_num = %c0 : index init_out_buffer = false may_implicit_transpose_with_last_axis = false
  hivm.hir.set_flag[<PIPE_MTE2>, <PIPE_V>, <EVENT_ID0>]
  %22 = hivm.hir.pointer_cast(%c1088_i64) : memref<1x1xf32, #hivm.address_space<ub>>
  %collapse_shape = memref.collapse_shape %15 [[0, 1]] : memref<1x256xf32, #hivm.address_space<ub>> into memref<256xf32, #hivm.address_space<ub>>
  %collapse_shape_2 = memref.collapse_shape %22 [[0, 1]] : memref<1x1xf32, #hivm.address_space<ub>> into memref<1xf32, #hivm.address_space<ub>>
  %23 = hivm.hir.pointer_cast(%c1120_i64) : memref<64xf32, #hivm.address_space<ub>>
  hivm.hir.wait_flag[<PIPE_MTE2>, <PIPE_V>, <EVENT_ID0>]
  hivm.hir.vreduce <max> ins(%collapse_shape : memref<256xf32, #hivm.address_space<ub>>) outs(%collapse_shape_2 : memref<1xf32, #hivm.address_space<ub>>) temp_buffer(%23 : memref<64xf32, #hivm.address_space<ub>>) reduce_dims = [0]
  hivm.hir.set_flag[<PIPE_V>, <PIPE_S>, <EVENT_ID0>]
  hivm.hir.wait_flag[<PIPE_V>, <PIPE_S>, <EVENT_ID0>]
  %24 = memref.load %22[%c0, %c0] : memref<1x1xf32, #hivm.address_space<ub>>
  %25 = hivm.hir.pointer_cast(%c64_i64) : memref<1x256xf32, #hivm.address_space<ub>>
  %26 = arith.subf %cst, %24 : f32
  %collapse_shape_3 = memref.collapse_shape %25 [[0, 1]] : memref<1x256xf32, #hivm.address_space<ub>> into memref<256xf32, #hivm.address_space<ub>>
  hivm.hir.vadd ins(%collapse_shape, %26 : memref<256xf32, #hivm.address_space<ub>>, f32) outs(%collapse_shape_3 : memref<256xf32, #hivm.address_space<ub>>)
  %27 = hivm.hir.pointer_cast(%c64_i64) : memref<1x256xf32, #hivm.address_space<ub>>
  %collapse_shape_4 = memref.collapse_shape %27 [[0, 1]] : memref<1x256xf32, #hivm.address_space<ub>> into memref<256xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vexp ins(%collapse_shape_3 : memref<256xf32, #hivm.address_space<ub>>) outs(%collapse_shape_4 : memref<256xf32, #hivm.address_space<ub>>)
  %28 = hivm.hir.pointer_cast(%c1376_i64) : memref<1x1xf32, #hivm.address_space<ub>>
  %collapse_shape_5 = memref.collapse_shape %28 [[0, 1]] : memref<1x1xf32, #hivm.address_space<ub>> into memref<1xf32, #hivm.address_space<ub>>
  %29 = hivm.hir.pointer_cast(%c1408_i64) : memref<128xf32, #hivm.address_space<ub>>
  hivm.hir.pipe_barrier[<PIPE_V>]
  hivm.hir.vreduce <sum> ins(%collapse_shape_4 : memref<256xf32, #hivm.address_space<ub>>) outs(%collapse_shape_5 : memref<1xf32, #hivm.address_space<ub>>) temp_buffer(%29 : memref<128xf32, #hivm.address_space<ub>>) reduce_dims = [0]
  hivm.hir.set_flag[<PIPE_V>, <PIPE_S>, <EVENT_ID0>]
  %30 = llvm.inline_asm has_side_effects asm_dialect = att "MOV $0, SYS_CNT", "=l"  : () -> i64
  %31 = arith.trunci %30 : i64 to i32
  hivm.hir.wait_flag[<PIPE_V>, <PIPE_S>, <EVENT_ID0>]
  %32 = memref.load %28[%c0, %c0] : memref<1x1xf32, #hivm.address_space<ub>>
  %33 = hivm.hir.pointer_cast(%c64_i64) : memref<1x256xf32, #hivm.address_space<ub>>
  %collapse_shape_6 = memref.collapse_shape %33 [[0, 1]] : memref<1x256xf32, #hivm.address_space<ub>> into memref<256xf32, #hivm.address_space<ub>>
  %34 = hivm.hir.pointer_cast(%c1920_i64) : memref<8xf32, #hivm.address_space<ub>>
  hivm.hir.vdiv ins(%collapse_shape_4, %32 : memref<256xf32, #hivm.address_space<ub>>, f32) outs(%collapse_shape_6 : memref<256xf32, #hivm.address_space<ub>>) temp_buffer(%34 : memref<8xf32, #hivm.address_space<ub>>)
  hivm.hir.set_flag[<PIPE_V>, <PIPE_MTE3>, <EVENT_ID0>]
  %reinterpret_cast_7 = memref.reinterpret_cast %arg4 to offset: [%14], sizes: [1, 256], strides: [256, 1] : memref<?xf32, #hivm.address_space<gm>> to memref<1x256xf32, strided<[256, 1], offset: ?>, #hivm.address_space<gm>>
  %subview_8 = memref.subview %33[0, 0] [%17, %18] [1, 1] : memref<1x256xf32, #hivm.address_space<ub>> to memref<?x?xf32, strided<[256, 1]>, #hivm.address_space<ub>>
  %subview_9 = memref.subview %reinterpret_cast_7[0, 0] [%17, %18] [1, 1] : memref<1x256xf32, strided<[256, 1], offset: ?>, #hivm.address_space<gm>> to memref<?x?xf32, strided<[256, 1], offset: ?>, #hivm.address_space<gm>>
  hivm.hir.wait_flag[<PIPE_V>, <PIPE_MTE3>, <EVENT_ID0>]
  hivm.hir.store ins(%subview_8 : memref<?x?xf32, strided<[256, 1]>, #hivm.address_space<ub>>) outs(%subview_9 : memref<?x?xf32, strided<[256, 1], offset: ?>, #hivm.address_space<gm>>)
  hivm.hir.pipe_barrier[<PIPE_ALL>]
  %35 = llvm.inline_asm has_side_effects asm_dialect = att "MOV $0, SYS_CNT", "=l"  : () -> i64
  %36 = arith.trunci %35 : i64 to i32
  %37 = llvm.inline_asm has_side_effects asm_dialect = att "MOV $0, SYS_CNT", "=l"  : () -> i64
  %38 = arith.trunci %37 : i64 to i32
  %39 = arith.index_cast %9 : i32 to index
  %40 = hivm.hir.pointer_cast(%c1952_i64) : memref<1xi32, #hivm.address_space<ub>>
  memref.store %11, %40[%c0] : memref<1xi32, #hivm.address_space<ub>>
  hivm.hir.set_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  %reinterpret_cast_10 = memref.reinterpret_cast %arg5 to offset: [%39], sizes: [1], strides: [1] : memref<?xi32, #hivm.address_space<gm>> to memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>
  hivm.hir.wait_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  hivm.hir.store ins(%40 : memref<1xi32, #hivm.address_space<ub>>) outs(%reinterpret_cast_10 : memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>)
  %41 = affine.apply affine_map<()[s0] -> (s0 + 1)>()[%39]
  %42 = hivm.hir.pointer_cast(%c1984_i64) : memref<1xi32, #hivm.address_space<ub>>
  memref.store %38, %42[%c0] : memref<1xi32, #hivm.address_space<ub>>
  hivm.hir.set_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  %reinterpret_cast_11 = memref.reinterpret_cast %arg5 to offset: [%41], sizes: [1], strides: [1] : memref<?xi32, #hivm.address_space<gm>> to memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>
  hivm.hir.wait_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  hivm.hir.pipe_barrier[<PIPE_MTE3>]
  hivm.hir.store ins(%42 : memref<1xi32, #hivm.address_space<ub>>) outs(%reinterpret_cast_11 : memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>)
  %43 = affine.apply affine_map<()[s0] -> (s0 + 2)>()[%39]
  %44 = hivm.hir.pointer_cast(%c2016_i64) : memref<1xi32, #hivm.address_space<ub>>
  memref.store %31, %44[%c0] : memref<1xi32, #hivm.address_space<ub>>
  hivm.hir.set_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  %reinterpret_cast_12 = memref.reinterpret_cast %arg5 to offset: [%43], sizes: [1], strides: [1] : memref<?xi32, #hivm.address_space<gm>> to memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>
  hivm.hir.wait_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  hivm.hir.pipe_barrier[<PIPE_MTE3>]
  hivm.hir.store ins(%44 : memref<1xi32, #hivm.address_space<ub>>) outs(%reinterpret_cast_12 : memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>)
  %45 = affine.apply affine_map<()[s0] -> (s0 + 3)>()[%39]
  %46 = hivm.hir.pointer_cast(%c2048_i64) : memref<1xi32, #hivm.address_space<ub>>
  memref.store %36, %46[%c0] : memref<1xi32, #hivm.address_space<ub>>
  hivm.hir.set_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  %reinterpret_cast_13 = memref.reinterpret_cast %arg5 to offset: [%45], sizes: [1], strides: [1] : memref<?xi32, #hivm.address_space<gm>> to memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>
  hivm.hir.wait_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  hivm.hir.pipe_barrier[<PIPE_MTE3>]
  hivm.hir.store ins(%46 : memref<1xi32, #hivm.address_space<ub>>) outs(%reinterpret_cast_13 : memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>)
  %47 = affine.apply affine_map<()[s0] -> (s0 + 4)>()[%39]
  %48 = hivm.hir.pointer_cast(%c2080_i64) : memref<1xi32, #hivm.address_space<ub>>
  memref.store %6, %48[%c0] : memref<1xi32, #hivm.address_space<ub>>
  hivm.hir.set_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  %reinterpret_cast_14 = memref.reinterpret_cast %arg5 to offset: [%47], sizes: [1], strides: [1] : memref<?xi32, #hivm.address_space<gm>> to memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>
  hivm.hir.wait_flag[<PIPE_S>, <PIPE_MTE3>, <EVENT_ID0>]
  hivm.hir.pipe_barrier[<PIPE_MTE3>]
  hivm.hir.store ins(%48 : memref<1xi32, #hivm.address_space<ub>>) outs(%reinterpret_cast_14 : memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>)
  %49 = affine.apply affine_map<()[s0] -> (s0 + 5)>()[%39]
  %reinterpret_cast_15 = memref.reinterpret_cast %arg5 to offset: [%49], sizes: [1], strides: [1] : memref<?xi32, #hivm.address_space<gm>> to memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>
  hivm.hir.pipe_barrier[<PIPE_MTE3>]
  hivm.hir.store ins(%8 : memref<1xi32, #hivm.address_space<ub>>) outs(%reinterpret_cast_15 : memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>)
  %50 = affine.apply affine_map<()[s0] -> (s0 + 6)>()[%39]
  %reinterpret_cast_16 = memref.reinterpret_cast %arg5 to offset: [%50], sizes: [1], strides: [1] : memref<?xi32, #hivm.address_space<gm>> to memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>
  hivm.hir.pipe_barrier[<PIPE_MTE3>]
  hivm.hir.store ins(%7 : memref<1xi32, #hivm.address_space<ub>>) outs(%reinterpret_cast_16 : memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>)
  %51 = affine.apply affine_map<()[s0] -> (s0 + 7)>()[%39]
  %reinterpret_cast_17 = memref.reinterpret_cast %arg5 to offset: [%51], sizes: [1], strides: [1] : memref<?xi32, #hivm.address_space<gm>> to memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>
  hivm.hir.pipe_barrier[<PIPE_MTE3>]
  hivm.hir.store ins(%8 : memref<1xi32, #hivm.address_space<ub>>) outs(%reinterpret_cast_17 : memref<1xi32, strided<[1], offset: ?>, #hivm.address_space<gm>>)
  hivm.hir.pipe_barrier[<PIPE_ALL>]
  return
}

warning: linking module '/tmp/tmp1koruys6/kernel.ll': Linking two modules of different data layouts: '/usr/local/python3.11.15/lib/python3.11/site-packages/triton/backends/ascend/lib/libdevice.10.bc' is 'e-i1:8:32-i8:8:32-i16:16:32-i64:64-f16:16:32-v16:16-v32:32-n8:16:32:64-S64' whereas '/tmp/tmp1koruys6/kernel.ll' is 'e-i1:8:32-i8:8:32-i16:16:32-i64:64-f16:16:32-v16:16-v32:32-n64-S64'
 [-Wlinker-warnings]
1 warning generated.
warning: overriding the module target triple with aarch64-unknown-linux-gnu [-Woverride-module]
1 warning generated.
warning: overriding the module target triple with aarch64-unknown-linux-gnu [-Woverride-module]
1 warning generated.
