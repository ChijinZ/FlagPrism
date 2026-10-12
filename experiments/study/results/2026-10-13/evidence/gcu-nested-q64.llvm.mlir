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
      %0 = "llvm.mlir.constant"() <{value = 128 : i32}> : () -> i32
      %1 = "llvm.mlir.constant"() <{value = 64 : i32}> : () -> i32
      %2 = "llvm.mlir.constant"() <{value = 0 : i32}> : () -> i32
      %3 = "llvm.mlir.constant"() <{value = 1 : i32}> : () -> i32
      %4 = "llvm.mlir.constant"() <{value = 0.000000e+00 : f32}> : () -> f32
      %5 = "llvm.mlir.constant"() <{value = 1 : index}> : () -> i32
      %6 = "llvm.mlir.constant"() <{value = 128 : index}> : () -> i32
      %7 = "llvm.mlir.constant"() <{value = 0 : index}> : () -> i32
      %8 = "llvm.mlir.constant"() <{value = dense<9.990000e-01> : vector<128xf32>}> : () -> vector<128xf32>
      %9 = "llvm.mlir.constant"() <{value = dense<1.000000e-03> : vector<128xf32>}> : () -> vector<128xf32>
      %10 = "llvm.mlir.constant"() <{value = 4 : i64}> : () -> i64
      %11 = "llvm.mlir.constant"() <{value = 8 : i64}> : () -> i64
      %12 = "llvm.mlir.constant"() <{value = 12 : i64}> : () -> i64
      %13 = "llvm.mlir.poison"() : () -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %14 = "llvm.mlir.constant"() <{value = 4 : index}> : () -> i32
      %15 = "llvm.mlir.constant"() <{value = 2 : index}> : () -> i32
      %16 = "llvm.mlir.constant"() <{value = 768 : index}> : () -> i32
      %17 = "llvm.alloca"(%16) <{alignment = 128 : i64, elem_type = i8}> : (i32) -> !llvm.ptr<5>
      %18 = "llvm.alloca"(%16) <{alignment = 128 : i64, elem_type = i8}> : (i32) -> !llvm.ptr<5>
      %19 = "llvm.alloca"(%15) <{elem_type = !llvm.ptr}> : (i32) -> !llvm.ptr
      %20 = "llvm.addrspacecast"(%18) : (!llvm.ptr<5>) -> !llvm.ptr
      "llvm.call"(%20) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_private_dte_ctr, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 1, 0>}> : (!llvm.ptr) -> ()
      "llvm.store"(%20, %19) <{ordering = 0 : i64}> : (!llvm.ptr, !llvm.ptr) -> ()
      %21 = "llvm.addrspacecast"(%17) : (!llvm.ptr<5>) -> !llvm.ptr
      "llvm.call"(%21) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_private_dte_ctr, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 1, 0>}> : (!llvm.ptr) -> ()
      %22 = "llvm.getelementptr"(%19) <{elem_type = !llvm.ptr, rawConstantIndices = array<i32: 1>}> : (!llvm.ptr) -> !llvm.ptr
      "llvm.store"(%21, %22) <{ordering = 0 : i64}> : (!llvm.ptr, !llvm.ptr) -> ()
      %23 = "llvm.ptrtoint"(%arg3) : (!llvm.ptr) -> i64
      %24 = "llvm.inttoptr"(%23) : (i64) -> !llvm.ptr
      %25 = "llvm.call"() <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_get_local_memory, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 0, 0>}> : () -> !llvm.ptr
      %26 = "llvm.insertvalue"(%13, %25) <{position = array<i64: 0>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, !llvm.ptr) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %27 = "llvm.insertvalue"(%26, %25) <{position = array<i64: 1>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, !llvm.ptr) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %28 = "llvm.insertvalue"(%27, %7) <{position = array<i64: 2>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, i32) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %29 = "llvm.insertvalue"(%28, %6) <{position = array<i64: 3, 0>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, i32) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %30 = "llvm.insertvalue"(%29, %5) <{position = array<i64: 4, 0>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, i32) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %31 = "llvm.getelementptr"(%19) <{elem_type = !llvm.ptr, rawConstantIndices = array<i32: 1>}> : (!llvm.ptr) -> !llvm.ptr
      %32 = "llvm.load"(%31) <{ordering = 0 : i64}> : (!llvm.ptr) -> !llvm.ptr
      %33 = "llvm.trunc"(%6) <{overflowFlags = #llvm.overflow<none>}> : (i32) -> i32
      %34 = "llvm.trunc"(%6) <{overflowFlags = #llvm.overflow<none>}> : (i32) -> i32
      "llvm.call"(%32, %25, %33, %24, %34, %2, %4) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_slice_async_1_fp32, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 7, 0>}> : (!llvm.ptr, !llvm.ptr, i32, !llvm.ptr, i32, i32, f32) -> ()
      "llvm.call"() <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_syncthreads, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 0, 0>}> : () -> ()
      %35 = "llvm.call"() <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_clock_begin, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 0, 0>}> : () -> i64
      %36 = "llvm.call"(%35) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_trunci_ui64_to_ui32, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 1, 0>}> : (i64) -> i32
      %37 = "llvm.getelementptr"(%19) <{elem_type = !llvm.ptr, rawConstantIndices = array<i32: 1>}> : (!llvm.ptr) -> !llvm.ptr
      %38 = "llvm.load"(%37) <{ordering = 0 : i64}> : (!llvm.ptr) -> !llvm.ptr
      "llvm.call"(%38) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_wait_dte, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 1, 0>}> : (!llvm.ptr) -> ()
      %39 = "llvm.getelementptr"(%25) <{elem_type = i8, rawConstantIndices = array<i32: 512>}> : (!llvm.ptr) -> !llvm.ptr
      %40 = "llvm.insertvalue"(%13, %25) <{position = array<i64: 0>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, !llvm.ptr) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %41 = "llvm.insertvalue"(%40, %39) <{position = array<i64: 1>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, !llvm.ptr) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %42 = "llvm.insertvalue"(%41, %7) <{position = array<i64: 2>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, i32) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %43 = "llvm.insertvalue"(%42, %6) <{position = array<i64: 3, 0>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, i32) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %44 = "llvm.insertvalue"(%43, %5) <{position = array<i64: 4, 0>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, i32) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      "llvm.br"(%2, %30)[^bb1] : (i32, !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>) -> ()
    ^bb1(%45: i32, %46: !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>):  // 2 preds: ^bb0, ^bb2
      %47 = "llvm.icmp"(%45, %1) <{predicate = 2 : i64}> : (i32, i32) -> i1
      "llvm.cond_br"(%47)[^bb2, ^bb3] <{operandSegmentSizes = array<i32: 1, 0, 0>}> : (i1) -> ()
    ^bb2:  // pred: ^bb1
      %48 = "llvm.extractvalue"(%46) <{position = array<i64: 1>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>) -> !llvm.ptr
      %49 = "llvm.load"(%48) <{alignment = 512 : i64, ordering = 0 : i64}> : (!llvm.ptr) -> vector<128xf32>
      %50 = "llvm.call"(%49, %8, %9) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_mac_v4_fp32, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 3, 0>}> : (vector<128xf32>, vector<128xf32>, vector<128xf32>) -> vector<128xf32>
      "llvm.store"(%50, %39) <{alignment = 512 : i64, ordering = 0 : i64}> : (vector<128xf32>, !llvm.ptr) -> ()
      %51 = "llvm.add"(%45, %3) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      "llvm.br"(%51, %44)[^bb1] : (i32, !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>) -> ()
    ^bb3:  // pred: ^bb1
      "llvm.call"() <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_syncthreads, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 0, 0>}> : () -> ()
      %52 = "llvm.call"() <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_clock_begin, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 0, 0>}> : () -> i64
      %53 = "llvm.call"(%52) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_trunci_ui64_to_ui32, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 1, 0>}> : (i64) -> i32
      %54 = "llvm.getelementptr"(%25) <{elem_type = i8, rawConstantIndices = array<i32: 1024>}> : (!llvm.ptr) -> !llvm.ptr
      %55 = "llvm.insertvalue"(%13, %25) <{position = array<i64: 0>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, !llvm.ptr) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %56 = "llvm.insertvalue"(%55, %54) <{position = array<i64: 1>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, !llvm.ptr) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %57 = "llvm.insertvalue"(%56, %7) <{position = array<i64: 2>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, i32) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %58 = "llvm.insertvalue"(%57, %6) <{position = array<i64: 3, 0>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, i32) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %59 = "llvm.insertvalue"(%58, %5) <{position = array<i64: 4, 0>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, i32) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      "llvm.br"(%2, %46)[^bb4] : (i32, !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>) -> ()
    ^bb4(%60: i32, %61: !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>):  // 2 preds: ^bb3, ^bb5
      %62 = "llvm.icmp"(%60, %0) <{predicate = 2 : i64}> : (i32, i32) -> i1
      "llvm.cond_br"(%62)[^bb5, ^bb6] <{operandSegmentSizes = array<i32: 1, 0, 0>}> : (i1) -> ()
    ^bb5:  // pred: ^bb4
      %63 = "llvm.extractvalue"(%61) <{position = array<i64: 1>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>) -> !llvm.ptr
      %64 = "llvm.load"(%63) <{alignment = 512 : i64, ordering = 0 : i64}> : (!llvm.ptr) -> vector<128xf32>
      %65 = "llvm.call"(%64, %8, %9) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_mac_v4_fp32, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 3, 0>}> : (vector<128xf32>, vector<128xf32>, vector<128xf32>) -> vector<128xf32>
      "llvm.store"(%65, %54) <{alignment = 512 : i64, ordering = 0 : i64}> : (vector<128xf32>, !llvm.ptr) -> ()
      %66 = "llvm.add"(%60, %3) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      "llvm.br"(%66, %59)[^bb4] : (i32, !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>) -> ()
    ^bb6:  // pred: ^bb4
      "llvm.call"() <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_syncthreads, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 0, 0>}> : () -> ()
      %67 = "llvm.call"() <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_clock_end, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 0, 0>}> : () -> i64
      %68 = "llvm.call"(%67) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_trunci_ui64_to_ui32, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 1, 0>}> : (i64) -> i32
      %69 = "llvm.getelementptr"(%25) <{elem_type = i8, rawConstantIndices = array<i32: 1536>}> : (!llvm.ptr) -> !llvm.ptr
      %70 = "llvm.insertvalue"(%13, %25) <{position = array<i64: 0>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, !llvm.ptr) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %71 = "llvm.insertvalue"(%70, %69) <{position = array<i64: 1>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, !llvm.ptr) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %72 = "llvm.insertvalue"(%71, %7) <{position = array<i64: 2>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, i32) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %73 = "llvm.insertvalue"(%72, %6) <{position = array<i64: 3, 0>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, i32) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      %74 = "llvm.insertvalue"(%73, %5) <{position = array<i64: 4, 0>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>, i32) -> !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>
      "llvm.br"(%2, %61)[^bb7] : (i32, !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>) -> ()
    ^bb7(%75: i32, %76: !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>):  // 2 preds: ^bb6, ^bb8
      %77 = "llvm.icmp"(%75, %1) <{predicate = 2 : i64}> : (i32, i32) -> i1
      "llvm.cond_br"(%77)[^bb8, ^bb9] <{operandSegmentSizes = array<i32: 1, 0, 0>}> : (i1) -> ()
    ^bb8:  // pred: ^bb7
      %78 = "llvm.extractvalue"(%76) <{position = array<i64: 1>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>) -> !llvm.ptr
      %79 = "llvm.load"(%78) <{alignment = 512 : i64, ordering = 0 : i64}> : (!llvm.ptr) -> vector<128xf32>
      %80 = "llvm.call"(%79, %8, %9) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_mac_v4_fp32, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 3, 0>}> : (vector<128xf32>, vector<128xf32>, vector<128xf32>) -> vector<128xf32>
      "llvm.store"(%80, %69) <{alignment = 512 : i64, ordering = 0 : i64}> : (vector<128xf32>, !llvm.ptr) -> ()
      %81 = "llvm.add"(%75, %3) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      "llvm.br"(%81, %74)[^bb7] : (i32, !llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>) -> ()
    ^bb9:  // pred: ^bb7
      "llvm.call"() <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_syncthreads, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 0, 0>}> : () -> ()
      %82 = "llvm.call"() <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_clock_end, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 0, 0>}> : () -> i64
      %83 = "llvm.call"(%82) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_trunci_ui64_to_ui32, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 1, 0>}> : (i64) -> i32
      %84 = "llvm.ptrtoint"(%arg4) : (!llvm.ptr) -> i64
      %85 = "llvm.inttoptr"(%84) : (i64) -> !llvm.ptr
      %86 = "llvm.load"(%19) <{ordering = 0 : i64}> : (!llvm.ptr) -> !llvm.ptr
      %87 = "llvm.extractvalue"(%76) <{position = array<i64: 1>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>) -> !llvm.ptr
      %88 = "llvm.trunc"(%6) <{overflowFlags = #llvm.overflow<none>}> : (i32) -> i32
      %89 = "llvm.extractvalue"(%76) <{position = array<i64: 3, 0>}> : (!llvm.struct<(ptr, ptr, i32, array<1 x i32>, array<1 x i32>)>) -> i32
      %90 = "llvm.trunc"(%89) <{overflowFlags = #llvm.overflow<none>}> : (i32) -> i32
      "llvm.call"(%86, %85, %88, %87, %90, %2) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_deslice_async_1_fp32, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 6, 0>}> : (!llvm.ptr, !llvm.ptr, i32, !llvm.ptr, i32, i32) -> ()
      %91 = "llvm.load"(%19) <{ordering = 0 : i64}> : (!llvm.ptr) -> !llvm.ptr
      "llvm.call"(%91) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_wait_dte, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 1, 0>}> : (!llvm.ptr) -> ()
      "llvm.store"(%36, %25) <{ordering = 0 : i64}> : (i32, !llvm.ptr) -> ()
      %92 = "llvm.call"(%7) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_get_thread_id, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 1, 0>}> : (i32) -> i32
      %93 = "llvm.icmp"(%92, %7) <{predicate = 0 : i64}> : (i32, i32) -> i1
      "llvm.call"() <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_mfence, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 0, 0>}> : () -> ()
      "llvm.cond_br"(%93)[^bb10, ^bb11] <{operandSegmentSizes = array<i32: 1, 0, 0>}> : (i1) -> ()
    ^bb10:  // pred: ^bb9
      %94 = "llvm.load"(%19) <{ordering = 0 : i64}> : (!llvm.ptr) -> !llvm.ptr
      %95 = "llvm.mul"(%5, %7) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %96 = "llvm.add"(%95, %7) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %97 = "llvm.mul"(%5, %7) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %98 = "llvm.add"(%97, %7) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %99 = "llvm.getelementptr"(%arg5, %96) <{elem_type = i32, rawConstantIndices = array<i32: -2147483648>}> : (!llvm.ptr, i32) -> !llvm.ptr
      %100 = "llvm.getelementptr"(%25, %98) <{elem_type = i32, rawConstantIndices = array<i32: -2147483648>}> : (!llvm.ptr, i32) -> !llvm.ptr
      %101 = "llvm.trunc"(%5) <{overflowFlags = #llvm.overflow<none>}> : (i32) -> i32
      %102 = "llvm.mul"(%101, %14) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      "llvm.call"(%94, %99, %100, %102) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_memcpy_async, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 4, 0>}> : (!llvm.ptr, !llvm.ptr, !llvm.ptr, i32) -> ()
      %103 = "llvm.load"(%19) <{ordering = 0 : i64}> : (!llvm.ptr) -> !llvm.ptr
      "llvm.call"(%103) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_wait_dte, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 1, 0>}> : (!llvm.ptr) -> ()
      "llvm.br"()[^bb11] : () -> ()
    ^bb11:  // 2 preds: ^bb9, ^bb10
      %104 = "llvm.ptrtoint"(%arg5) : (!llvm.ptr) -> i64
      %105 = "llvm.add"(%104, %10) <{overflowFlags = #llvm.overflow<none>}> : (i64, i64) -> i64
      %106 = "llvm.inttoptr"(%105) : (i64) -> !llvm.ptr
      "llvm.store"(%83, %25) <{ordering = 0 : i64}> : (i32, !llvm.ptr) -> ()
      "llvm.call"() <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_mfence, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 0, 0>}> : () -> ()
      "llvm.cond_br"(%93)[^bb12, ^bb13] <{operandSegmentSizes = array<i32: 1, 0, 0>}> : (i1) -> ()
    ^bb12:  // pred: ^bb11
      %107 = "llvm.load"(%19) <{ordering = 0 : i64}> : (!llvm.ptr) -> !llvm.ptr
      %108 = "llvm.mul"(%5, %7) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %109 = "llvm.add"(%108, %7) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %110 = "llvm.mul"(%5, %7) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %111 = "llvm.add"(%110, %7) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %112 = "llvm.getelementptr"(%106, %109) <{elem_type = i32, rawConstantIndices = array<i32: -2147483648>}> : (!llvm.ptr, i32) -> !llvm.ptr
      %113 = "llvm.getelementptr"(%25, %111) <{elem_type = i32, rawConstantIndices = array<i32: -2147483648>}> : (!llvm.ptr, i32) -> !llvm.ptr
      %114 = "llvm.trunc"(%5) <{overflowFlags = #llvm.overflow<none>}> : (i32) -> i32
      %115 = "llvm.mul"(%114, %14) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      "llvm.call"(%107, %112, %113, %115) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_memcpy_async, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 4, 0>}> : (!llvm.ptr, !llvm.ptr, !llvm.ptr, i32) -> ()
      %116 = "llvm.load"(%19) <{ordering = 0 : i64}> : (!llvm.ptr) -> !llvm.ptr
      "llvm.call"(%116) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_wait_dte, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 1, 0>}> : (!llvm.ptr) -> ()
      "llvm.br"()[^bb13] : () -> ()
    ^bb13:  // 2 preds: ^bb11, ^bb12
      %117 = "llvm.add"(%104, %11) <{overflowFlags = #llvm.overflow<none>}> : (i64, i64) -> i64
      %118 = "llvm.inttoptr"(%117) : (i64) -> !llvm.ptr
      "llvm.store"(%53, %25) <{ordering = 0 : i64}> : (i32, !llvm.ptr) -> ()
      "llvm.call"() <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_mfence, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 0, 0>}> : () -> ()
      "llvm.cond_br"(%93)[^bb14, ^bb15] <{operandSegmentSizes = array<i32: 1, 0, 0>}> : (i1) -> ()
    ^bb14:  // pred: ^bb13
      %119 = "llvm.load"(%19) <{ordering = 0 : i64}> : (!llvm.ptr) -> !llvm.ptr
      %120 = "llvm.mul"(%5, %7) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %121 = "llvm.add"(%120, %7) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %122 = "llvm.mul"(%5, %7) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %123 = "llvm.add"(%122, %7) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %124 = "llvm.getelementptr"(%118, %121) <{elem_type = i32, rawConstantIndices = array<i32: -2147483648>}> : (!llvm.ptr, i32) -> !llvm.ptr
      %125 = "llvm.getelementptr"(%25, %123) <{elem_type = i32, rawConstantIndices = array<i32: -2147483648>}> : (!llvm.ptr, i32) -> !llvm.ptr
      %126 = "llvm.trunc"(%5) <{overflowFlags = #llvm.overflow<none>}> : (i32) -> i32
      %127 = "llvm.mul"(%126, %14) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      "llvm.call"(%119, %124, %125, %127) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_memcpy_async, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 4, 0>}> : (!llvm.ptr, !llvm.ptr, !llvm.ptr, i32) -> ()
      %128 = "llvm.load"(%19) <{ordering = 0 : i64}> : (!llvm.ptr) -> !llvm.ptr
      "llvm.call"(%128) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_wait_dte, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 1, 0>}> : (!llvm.ptr) -> ()
      "llvm.br"()[^bb15] : () -> ()
    ^bb15:  // 2 preds: ^bb13, ^bb14
      %129 = "llvm.add"(%104, %12) <{overflowFlags = #llvm.overflow<none>}> : (i64, i64) -> i64
      %130 = "llvm.inttoptr"(%129) : (i64) -> !llvm.ptr
      "llvm.store"(%68, %25) <{ordering = 0 : i64}> : (i32, !llvm.ptr) -> ()
      "llvm.call"() <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_mfence, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 0, 0>}> : () -> ()
      "llvm.cond_br"(%93)[^bb16, ^bb17] <{operandSegmentSizes = array<i32: 1, 0, 0>}> : (i1) -> ()
    ^bb16:  // pred: ^bb15
      %131 = "llvm.load"(%19) <{ordering = 0 : i64}> : (!llvm.ptr) -> !llvm.ptr
      %132 = "llvm.mul"(%5, %7) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %133 = "llvm.add"(%132, %7) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %134 = "llvm.mul"(%5, %7) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %135 = "llvm.add"(%134, %7) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      %136 = "llvm.getelementptr"(%130, %133) <{elem_type = i32, rawConstantIndices = array<i32: -2147483648>}> : (!llvm.ptr, i32) -> !llvm.ptr
      %137 = "llvm.getelementptr"(%25, %135) <{elem_type = i32, rawConstantIndices = array<i32: -2147483648>}> : (!llvm.ptr, i32) -> !llvm.ptr
      %138 = "llvm.trunc"(%5) <{overflowFlags = #llvm.overflow<none>}> : (i32) -> i32
      %139 = "llvm.mul"(%138, %14) <{overflowFlags = #llvm.overflow<none>}> : (i32, i32) -> i32
      "llvm.call"(%131, %136, %137, %139) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_memcpy_async, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 4, 0>}> : (!llvm.ptr, !llvm.ptr, !llvm.ptr, i32) -> ()
      %140 = "llvm.load"(%19) <{ordering = 0 : i64}> : (!llvm.ptr) -> !llvm.ptr
      "llvm.call"(%140) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @tops_wait_dte, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 1, 0>}> : (!llvm.ptr) -> ()
      "llvm.br"()[^bb17] : () -> ()
    ^bb17:  // 2 preds: ^bb15, ^bb16
      "llvm.return"() : () -> ()
    }) : () -> ()
    "llvm.func"() <{CConv = #llvm.cconv<ccc>, function_type = !llvm.func<void (ptr, ptr, ptr)>, linkage = #llvm.linkage<external>, sym_name = "probe", visibility_ = 0 : i64}> ({
    ^bb0(%arg0: !llvm.ptr, %arg1: !llvm.ptr, %arg2: !llvm.ptr):
      "llvm.call"(%arg0, %arg1, %arg2) <{CConv = #llvm.cconv<ccc>, TailCallKind = #llvm.tailcallkind<none>, callee = @probe_triton_internal__, fastmathFlags = #llvm.fastmath<none>, op_bundle_sizes = array<i32>, operandSegmentSizes = array<i32: 3, 0>}> : (!llvm.ptr, !llvm.ptr, !llvm.ptr) -> ()
      "llvm.return"() : () -> ()
    }) {dtu_kernel, gcu.local_memory_size = 2048 : i64, gcu.shared_memory_size = 0 : i64, gpu.kernel} : () -> ()
  }) : () -> ()
}) {"ttg.cluster-dims-x" = 1 : i32, "ttg.cluster-dims-y" = 1 : i32, "ttg.cluster-dims-z" = 1 : i32, "ttg.num-ctas" = 1 : i32, "ttg.num-warps" = 1 : i32, ttg.target = "gcu:gcu300", "ttg.threads-per-warp" = 1 : i32} : () -> ()
