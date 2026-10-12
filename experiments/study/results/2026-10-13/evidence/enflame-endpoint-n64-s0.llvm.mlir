"builtin.module"() ({
  "gpu.module"() <{sym_name = "triton", targets = [#gcu.target]}> ({
    "llvm.func"() <{CConv = #llvm.cconv<ccc>, function_type = !llvm.func<void (ptr, ptr, ptr, i32)>, linkage = #llvm.linkage<external>, sym_name = "tops_memcpy_async", visibility_ = 0 : i64}> ({
    }) : () -> ()
    "llvm.func"() <{CConv = #llvm.cconv<ccc>, function_type = !llvm.func<void ()>, linkage = #llvm.linkage<external>, sym_name = "tops_mfence", visibility_ = 0 : i64}> ({
    }) : () -> ()
    "llvm.func"() <{CConv = #llvm.cconv<ccc>, function_type = !llvm.func<i32 (i32)>, linkage = #llvm.linkage<external>, sym_name = "tops_get_thread_id", visibility_ = 0 : i64}> ({
    }) : () -> ()
    "llvm.func"() <{CConv = #llvm.cconv<ccc>, function_type = !llvm.func<void (ptr, ptr, i32, ptr, i32, i32)>, linkage = #llvm.linkage<external>, sym_name = "tops_deslice_async_1_fp32", visibility_ = 0 : i64}> ({
    }) : () -> ()
    "llvm.func"() <{CConv = #llvm.cconv<ccc>, function_type = !llvm.func<i64 ()>, linkage = #llvm.linkage<external>, sym_name = "tops_clock_end", visibility_ = 0 : i64}> ({
    }) : () -> ()
    "llvm.func"() <{CConv = #llvm.cconv<ccc>, function_type = !llvm.func<void (ptr)>, linkage = #llvm.linkage<external>, sym_name = "tops_wait_dte", visibility_ = 0 : i64}> ({
    }) : () -> ()
    "llvm.func"() <{CConv = #llvm.cconv<ccc>, function_type = !llvm.func<i64 ()>, linkage = #llvm.linkage<external>, sym_name = "tops_clock_begin", visibility_ = 0 : i64}> ({
    }) : () -> ()
    "llvm.func"() <{CConv = #llvm.cconv<ccc>, function_type = !llvm.func<void ()>, linkage = #llvm.linkage<external>, sym_name = "tops_syncthreads", visibility_ = 0 : i64}> ({
    }) : () -> ()
    "llvm.func"() <{CConv = #llvm.cconv<ccc>, function_type = !llvm.func<void (ptr, ptr, i32, ptr, i32, i32, f32)>, linkage = #llvm.linkage<external>, sym_name = "tops_slice_async_1_fp32", visibility_ = 0 : i64}> ({
    }) : () -> ()
    "llvm.func"() <{CConv = #llvm.cconv<ccc>, function_type = !llvm.func<ptr ()>, linkage = #llvm.linkage<external>, sym_name = "tops_get_local_memory", visibility_ = 0 : i64}> ({
    }) : () -> ()
    "llvm.func"() <{CConv = #llvm.cconv<ccc>, function_type = !llvm.func<void (ptr)>, linkage = #llvm.linkage<external>, sym_name = "tops_private_dte_ctr", visibility_ = 0 : i64}> ({
    }) : () -> ()
    "llvm.func"() <{CConv = #llvm.cconv<ccc>, function_type = !llvm.func<i32 (i64)>, linkage = #llvm.linkage<external>, sym_name = "tops_trunci_ui64_to_ui32", visibility_ = 0 : i64}> ({
    }) : () -> ()
    "llvm.func"() <{CConv = #llvm.cconv<ccc>, function_type = !llvm.func<vector<128xf32> (vector<128xf32>, vector<128xf32>, vector<128xf32>)>, linkage = #llvm.linkage<external>, sym_name = "tops_mac_v4_fp32", visibility_ = 0 : i64}> ({
    }) : () -> ()
    "llvm.func"() <{CConv = #llvm.cconv<ccc>, function_type = !llvm.func<void (ptr, ptr, ptr)>, linkage = #llvm.linkage<internal>, sym_name = "probe_triton_internal__", visibility_ = 0 : i64}> ({
    ^bb0(%arg3: !llvm.ptr, %arg4: !llvm.ptr, %arg5: !llvm.ptr):
      %0 = "llvm.mlir.constant"() <{value = 64 : i32}> : () -> i32
      %1 = "llvm.mlir.constant"() <{value = 1 : i32}> : () -> i32
      %2 = "llvm.mlir.constant"() <{value = 0 : i32}> : () -> i32
      %3 = "llvm.mlir.constant"() <{value = 0.000000e+00 : f32}> : () -> f32
      %4 = "llvm.mlir.constant"() <{value = 1 : index}> : () -> i32
      %5 = "llvm.mlir.constant"() <{value = 128 : index}> : () -> i32
      %6 = "llvm.mlir.constant"() <{value = 0 : index}> : () -> i32
      %7 = "llvm.mlir.constant"() <{value = dense<9.990000e-01> : vector<128xf32>}> : () -> vector<128xf32>
      %8 = "llvm.mlir.constant"() <{value = dense<1.000000e-03> : vector<128xf32>}> : () -> vector<128xf32>
      %9 = "llvm.mlir.constant"() <{value = 4 : i64}> : () -> i64
      %10 = "llvm.mlir.constant"() <{value = 8 : i64}> : () -> i64
      %11 = "llvm.mlir.constant"() <{value = 12 : i64}> : () -> i64
      %12 = "llvm.mlir.poison"() : () -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %13 = "llvm.mlir.constant"() <{value = 4 : index}> : () -> i32
      %14 = "llvm.mlir.constant"() <{value = 2 : index}> : () -> i32
      %15 = "llvm.mlir.constant"() <{value = 768 : index}> : () -> i32
      %16 = "llvm.alloca"(%15) <{alignment = 128 : i64, elem_type = i8}> : (i32) -> !llvm.ptr<5>
      %17 = "llvm.alloca"(%15) <{alignment = 128 : i64, elem_type = i8}> : (i32) -> !llvm.ptr<5>
      %18 = "llvm.alloca"(%14) <{elem_type = !llvm.ptr}> : (i32) -> !llvm.ptr
      %19 = "llvm.addrspacecast"(%17) : (!llvm.ptr<5>) -> !llvm.ptr
      "llvm.call"(%19) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_private_dte_ctr, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 1, 0>}> : (!llvm.ptr) -> ()
      "llvm.store"(%19, %18) <{ordering = 0 : i64}> : (!llvm.ptr, !llvm.ptr) -> ()
      %20 = "llvm.addrspacecast"(%16) : (!llvm.ptr<5>) -> !llvm.ptr
      "llvm.call"(%20) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_private_dte_ctr, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 1, 0>}> : (!llvm.ptr) -> ()
      %21 = "llvm.getelementptr"(%18) <{elem_type = !llvm.ptr, rawConstantIndices = array<i32: 1>}> : (!llvm.ptr) -> !llvm.ptr
      "llvm.store"(%20, %21) <{ordering = 0 : i64}> : (!llvm.ptr, !llvm.ptr) -> ()
      %22 = "llvm.ptrtoint"(%arg3) : (!llvm.ptr) -> i64
      %23 = "llvm.inttoptr"(%22) : (i64) -> !llvm.ptr
      %24 = "llvm.call"() <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_get_local_memory, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 0, 0>}> : () -> !llvm.ptr
      %25 = "llvm.insertvalue"(%12, %24) <{position = array<i64: 0>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, !llvm.ptr) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %26 = "llvm.insertvalue"(%25, %24) <{position = array<i64: 1>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, !llvm.ptr) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %27 = "llvm.insertvalue"(%26, %6) <{position = array<i64: 2>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, i32) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %28 = "llvm.insertvalue"(%27, %5) <{position = array<i64: 3, 0>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, i32) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %29 = "llvm.insertvalue"(%28, %4) <{position = array<i64: 4, 0>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, i32) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %30 = "llvm.getelementptr"(%18) <{elem_type = !llvm.ptr, rawConstantIndices = array<i32: 1>}> : (!llvm.ptr) -> !llvm.ptr
      %31 = "llvm.load"(%30) <{ordering = 0 : i64}> : (!llvm.ptr) -> !llvm.ptr
      %32 = "llvm.trunc"(%5) <{overflowFlags = #llvm.overflow<none>}> : (i32) -> i32
      %33 = "llvm.trunc"(%5) <{overflowFlags = #llvm.overflow<none>}> : (i32) -> i32
      "llvm.call"(%31, %24, %32, %23, %33, %2, %3) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_slice_async_1_fp32, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 7, 0>}> : (!llvm.ptr, !llvm.ptr, i32, !llvm.ptr, i32, i32, f32) -> ()
      "llvm.call"() <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_syncthreads, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 0, 0>}> : () -> ()
      %34 = "llvm.call"() <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_clock_begin, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 0, 0>}> : () -> i64
      %35 = "llvm.call"(%34) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_trunci_ui64_to_ui32, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 1, 0>}> : (i64) -> i32
      %36 = "llvm.getelementptr"(%18) <{elem_type = !llvm.ptr, rawConstantIndices = array<i32: 1>}> : (!llvm.ptr) -> !llvm.ptr
      %37 = "llvm.load"(%36) <{ordering = 0 : i64}> : (!llvm.ptr) -> !llvm.ptr
      "llvm.call"(%37) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_wait_dte, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 1, 0>}> : (!llvm.ptr) -> ()
      %38 = "llvm.getelementptr"(%24) <{elem_type = i8, rawConstantIndices = array<i32: 512>}> : (!llvm.ptr) -> !llvm.ptr
      %39 = "llvm.insertvalue"(%12, %24) <{position = array<i64: 0>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, !llvm.ptr) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %40 = "llvm.insertvalue"(%39, %38) <{position = array<i64: 1>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, !llvm.ptr) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %41 = "llvm.insertvalue"(%40, %6) <{position = array<i64: 2>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, i32) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %42 = "llvm.insertvalue"(%41, %5) <{position = array<i64: 3, 0>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, i32) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %43 = "llvm.insertvalue"(%42, %4) <{position = array<i64: 4, 0>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, i32) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      "llvm.br"(%2, %29)[^bb1] : (i32, !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>) -> ()
    ^bb1(%44: i32, %45: !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>):  // 2 preds: ^bb0, ^bb2
      %46 = "llvm.icmp"(%44, %0) <{predicate = 2 : i64}> : (i32, i32) -> i1
      "llvm.cond_br"(%46)[^bb2, ^bb3] <{operandSegmentSizes = array<i32: 1, 0, 0>}> : (i1) -> ()
    ^bb2:  // pred: ^bb1
      %47 = "llvm.extractvalue"(%45) <{position = array<i64: 1>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>) -> !llvm.ptr
      %48 = "llvm.load"(%47) <{alignment = 512 : i64, ordering = 0 : i64}> : (!llvm.ptr) -> vector<128xf32>
      %49 = "llvm.call"(%48, %7, %8) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_mac_v4_fp32, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 3, 0>}> : (vector<128xf32>, vector<128xf32>, vector<128xf32>) -> vector<128xf32>
      "llvm.store"(%49, %38) <{alignment = 512 : i64, ordering = 0 : i64}> : (vector<128xf32>, !llvm.ptr) -> ()
      %50 = "llvm.add"(%44, %1) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      "llvm.br"(%50, %43)[^bb1] : (i32, !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>) -> ()
    ^bb3:  // pred: ^bb1
      %51 = "llvm.call"() <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_clock_end, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 0, 0>}> : () -> i64
      %52 = "llvm.call"(%51) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_trunci_ui64_to_ui32, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 1, 0>}> : (i64) -> i32
      %53 = "llvm.ptrtoint"(%arg4) : (!llvm.ptr) -> i64
      %54 = "llvm.inttoptr"(%53) : (i64) -> !llvm.ptr
      %55 = "llvm.load"(%18) <{ordering = 0 : i64}> : (!llvm.ptr) -> !llvm.ptr
      %56 = "llvm.extractvalue"(%45) <{position = array<i64: 1>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>) -> !llvm.ptr
      %57 = "llvm.trunc"(%5) <{overflowFlags = #llvm.overflow<none>}> : (i32) -> i32
      %58 = "llvm.extractvalue"(%45) <{position = array<i64: 3, 0>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>) -> i32
      %59 = "llvm.trunc"(%58) <{overflowFlags = #llvm.overflow<none>}> : (i32) -> i32
      "llvm.call"(%55, %54, %57, %56, %59, %2) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_deslice_async_1_fp32, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 6, 0>}> : (!llvm.ptr, !llvm.ptr, i32, !llvm.ptr, i32, i32) -> ()
      %60 = "llvm.load"(%18) <{ordering = 0 : i64}> : (!llvm.ptr) -> !llvm.ptr
      "llvm.call"(%60) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_wait_dte, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 1, 0>}> : (!llvm.ptr) -> ()
      "llvm.store"(%35, %24) <{ordering = 0 : i64}> : (i32, !llvm.ptr) -> ()
      %61 = "llvm.call"(%6) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_get_thread_id, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 1, 0>}> : (i32) -> i32
      %62 = "llvm.icmp"(%61, %6) <{predicate = 0 : i64}> : (i32, i32) -> i1
      "llvm.call"() <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_mfence, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 0, 0>}> : () -> ()
      "llvm.cond_br"(%62)[^bb4, ^bb5] <{operandSegmentSizes = array<i32: 1, 0, 0>}> : (i1) -> ()
    ^bb4:  // pred: ^bb3
      %63 = "llvm.load"(%18) <{ordering = 0 : i64}> : (!llvm.ptr) -> !llvm.ptr
      %64 = "llvm.mul"(%4, %6) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %65 = "llvm.add"(%64, %6) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %66 = "llvm.mul"(%4, %6) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %67 = "llvm.add"(%66, %6) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %68 = "llvm.getelementptr"(%arg5, %65) <{elem_type = i32, rawConstantIndices = array<i32: -2147483648>}> : (!llvm.ptr, i32) -> !llvm.ptr
      %69 = "llvm.getelementptr"(%24, %67) <{elem_type = i32, rawConstantIndices = array<i32: -2147483648>}> : (!llvm.ptr, i32) -> !llvm.ptr
      %70 = "llvm.trunc"(%4) <{overflowFlags = #llvm.overflow<none>}> : (i32) -> i32
      %71 = "llvm.mul"(%70, %13) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      "llvm.call"(%63, %68, %69, %71) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_memcpy_async, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 4, 0>}> : (!llvm.ptr, !llvm.ptr, !llvm.ptr, i32) -> ()
      %72 = "llvm.load"(%18) <{ordering = 0 : i64}> : (!llvm.ptr) -> !llvm.ptr
      "llvm.call"(%72) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_wait_dte, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 1, 0>}> : (!llvm.ptr) -> ()
      "llvm.br"()[^bb5] : () -> ()
    ^bb5:  // 2 preds: ^bb3, ^bb4
      %73 = "llvm.ptrtoint"(%arg5) : (!llvm.ptr) -> i64
      %74 = "llvm.add"(%73, %9) <{overflowFlags = #llvm.overflow<none>}> : (i64, i64) -> i64
      %75 = "llvm.inttoptr"(%74) : (i64) -> !llvm.ptr
      "llvm.store"(%52, %24) <{ordering = 0 : i64}> : (i32, !llvm.ptr) -> ()
      "llvm.call"() <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_mfence, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 0, 0>}> : () -> ()
      "llvm.cond_br"(%62)[^bb6, ^bb7] <{operandSegmentSizes = array<i32: 1, 0, 0>}> : (i1) -> ()
    ^bb6:  // pred: ^bb5
      %76 = "llvm.load"(%18) <{ordering = 0 : i64}> : (!llvm.ptr) -> !llvm.ptr
      %77 = "llvm.mul"(%4, %6) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %78 = "llvm.add"(%77, %6) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %79 = "llvm.mul"(%4, %6) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %80 = "llvm.add"(%79, %6) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %81 = "llvm.getelementptr"(%75, %78) <{elem_type = i32, rawConstantIndices = array<i32: -2147483648>}> : (!llvm.ptr, i32) -> !llvm.ptr
      %82 = "llvm.getelementptr"(%24, %80) <{elem_type = i32, rawConstantIndices = array<i32: -2147483648>}> : (!llvm.ptr, i32) -> !llvm.ptr
      %83 = "llvm.trunc"(%4) <{overflowFlags = #llvm.overflow<none>}> : (i32) -> i32
      %84 = "llvm.mul"(%83, %13) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      "llvm.call"(%76, %81, %82, %84) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_memcpy_async, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 4, 0>}> : (!llvm.ptr, !llvm.ptr, !llvm.ptr, i32) -> ()
      %85 = "llvm.load"(%18) <{ordering = 0 : i64}> : (!llvm.ptr) -> !llvm.ptr
      "llvm.call"(%85) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_wait_dte, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 1, 0>}> : (!llvm.ptr) -> ()
      "llvm.br"()[^bb7] : () -> ()
    ^bb7:  // 2 preds: ^bb5, ^bb6
      %86 = "llvm.add"(%73, %10) <{overflowFlags = #llvm.overflow<none>}> : (i64, i64) -> i64
      %87 = "llvm.inttoptr"(%86) : (i64) -> !llvm.ptr
      "llvm.store"(%2, %24) <{ordering = 0 : i64}> : (i32, !llvm.ptr) -> ()
      "llvm.call"() <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_mfence, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 0, 0>}> : () -> ()
      "llvm.cond_br"(%62)[^bb8, ^bb9] <{operandSegmentSizes = array<i32: 1, 0, 0>}> : (i1) -> ()
    ^bb8:  // pred: ^bb7
      %88 = "llvm.load"(%18) <{ordering = 0 : i64}> : (!llvm.ptr) -> !llvm.ptr
      %89 = "llvm.mul"(%4, %6) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %90 = "llvm.add"(%89, %6) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %91 = "llvm.mul"(%4, %6) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %92 = "llvm.add"(%91, %6) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %93 = "llvm.getelementptr"(%87, %90) <{elem_type = i32, rawConstantIndices = array<i32: -2147483648>}> : (!llvm.ptr, i32) -> !llvm.ptr
      %94 = "llvm.getelementptr"(%24, %92) <{elem_type = i32, rawConstantIndices = array<i32: -2147483648>}> : (!llvm.ptr, i32) -> !llvm.ptr
      %95 = "llvm.trunc"(%4) <{overflowFlags = #llvm.overflow<none>}> : (i32) -> i32
      %96 = "llvm.mul"(%95, %13) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      "llvm.call"(%88, %93, %94, %96) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_memcpy_async, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 4, 0>}> : (!llvm.ptr, !llvm.ptr, !llvm.ptr, i32) -> ()
      %97 = "llvm.load"(%18) <{ordering = 0 : i64}> : (!llvm.ptr) -> !llvm.ptr
      "llvm.call"(%97) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_wait_dte, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 1, 0>}> : (!llvm.ptr) -> ()
      "llvm.br"()[^bb9] : () -> ()
    ^bb9:  // 2 preds: ^bb7, ^bb8
      %98 = "llvm.add"(%73, %11) <{overflowFlags = #llvm.overflow<none>}> : (i64, i64) -> i64
      %99 = "llvm.inttoptr"(%98) : (i64) -> !llvm.ptr
      "llvm.store"(%2, %24) <{ordering = 0 : i64}> : (i32, !llvm.ptr) -> ()
      "llvm.call"() <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_mfence, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 0, 0>}> : () -> ()
      "llvm.cond_br"(%62)[^bb10, ^bb11] <{operandSegmentSizes = array<i32: 1, 0, 0>}> : (i1) -> ()
    ^bb10:  // pred: ^bb9
      %100 = "llvm.load"(%18) <{ordering = 0 : i64}> : (!llvm.ptr) -> !llvm.ptr
      %101 = "llvm.mul"(%4, %6) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %102 = "llvm.add"(%101, %6) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %103 = "llvm.mul"(%4, %6) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %104 = "llvm.add"(%103, %6) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %105 = "llvm.getelementptr"(%99, %102) <{elem_type = i32, rawConstantIndices = array<i32: -2147483648>}> : (!llvm.ptr, i32) -> !llvm.ptr
      %106 = "llvm.getelementptr"(%24, %104) <{elem_type = i32, rawConstantIndices = array<i32: -2147483648>}> : (!llvm.ptr, i32) -> !llvm.ptr
      %107 = "llvm.trunc"(%4) <{overflowFlags = #llvm.overflow<none>}> : (i32) -> i32
      %108 = "llvm.mul"(%107, %13) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      "llvm.call"(%100, %105, %106, %108) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_memcpy_async, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 4, 0>}> : (!llvm.ptr, !llvm.ptr, !llvm.ptr, i32) -> ()
      %109 = "llvm.load"(%18) <{ordering = 0 : i64}> : (!llvm.ptr) -> !llvm.ptr
      "llvm.call"(%109) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_wait_dte, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 1, 0>}> : (!llvm.ptr) -> ()
      "llvm.br"()[^bb11] : () -> ()
    ^bb11:  // 2 preds: ^bb9, ^bb10
      "llvm.return"() : () -> ()
    }) : () -> ()
    "llvm.func"() <{CConv = #llvm.cconv<ccc>, function_type = !llvm.func<void (ptr, ptr, ptr)>, linkage = #llvm.linkage<external>, sym_name = "probe", visibility_ = 0 : i64}> ({
    ^bb0(%arg0: !llvm.ptr, %arg1: !llvm.ptr, %arg2: !llvm.ptr):
      "llvm.call"(%arg0, %arg1, %arg2) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @probe_triton_internal__, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 3, 0>}> : (!llvm.ptr, !llvm.ptr, !llvm.ptr) -> ()
      "llvm.return"() : () -> ()
    }) {dtu_kernel, gcu.local_memory_size = 1024 : i64, gcu.shared_memory_size = 0 : i64, gpu.kernel} : () -> ()
  }) : () -> ()
}) {"ttg.cluster-dims-x" = 1 : i32, "ttg.cluster-dims-y" = 1 : i32, "ttg.cluster-dims-z" = 1 : i32, "ttg.num-ctas" = 1 : i32, "ttg.num-warps" = 1 : i32, ttg.target = "gcu:gcu300", "ttg.threads-per-warp" = 1 : i32} : () -> ()
