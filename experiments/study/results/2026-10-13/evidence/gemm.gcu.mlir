#map = affine_map<() -> (0)>
#map1 = affine_map<() -> (4)>
#map2 = affine_map<() -> (16)>
"builtin.module"() ({
  "gpu.module"() <{sym_name = "triton"}> ({
    "func.func"() <{function_type = (!gcu.ptr<f16>, !gcu.ptr<f16>, !gcu.ptr<f32>, !gcu.ptr<f32>) -> (), sym_name = "matmul_triton_internal__"}> ({
    ^bb0(%arg4: !gcu.ptr<f16>, %arg5: !gcu.ptr<f16>, %arg6: !gcu.ptr<f32>, %arg7: !gcu.ptr<f32>):
      %0 = "arith.constant"() <{value = dense<0.000000e+00> : vector<128xf32>}> : () -> vector<128xf32>
      %1 = "arith.constant"() <{value = 8 : index}> : () -> index
      %2 = "arith.constant"() <{value = 4 : i32}> : () -> i32
      %3 = "arith.constant"() <{value = 2 : index}> : () -> index
      %4 = "arith.constant"() <{value = 2047 : index}> : () -> index
      %5 = "arith.constant"() <{value = 4 : index}> : () -> index
      %6 = "arith.constant"() <{value = 0 : index}> : () -> index
      %7 = "arith.constant"() <{value = 64 : index}> : () -> index
      %8 = "arith.constant"() <{value = 16 : i32}> : () -> i32
      %9 = "arith.constant"() <{value = 8 : i32}> : () -> i32
      %10 = "arith.constant"() <{value = 1 : i32}> : () -> i32
      %11 = "arith.constant"() <{value = 0 : i32}> : () -> i32
      %12 = "arith.constant"() <{value = 16 : index}> : () -> index
      %13 = "arith.constant"() <{value = 128 : index}> : () -> index
      %14 = "arith.constant"() <{value = 0.000000e+00 : f16}> : () -> f16
      %15 = "arith.constant"() <{value = 1 : index}> : () -> index
      %16 = "arith.constant"() <{value = 2 : i64}> : () -> i64
      %17 = "arith.constant"() <{value = 4 : i64}> : () -> i64
      %18 = "memref.alloc"() <{operandSegmentSizes = array<i32: 0, 0>}> {gcu_private_tag} : () -> memref<3xi32>
      "gcu.border"() {enter = "triton_gcu.elementwise_fusion_region"} : () -> ()
      %19 = "memref.alloc"() <{operandSegmentSizes = array<i32: 0, 0>}> : () -> memref<8x8xf32>
      %20 = "memref.reinterpret_cast"(%19) <{operandSegmentSizes = array<i32: 1, 0, 0, 0>, static_offsets = array<i64: 0>, static_sizes = array<i64: 64>, static_strides = array<i64: 1>}> : (memref<8x8xf32>) -> memref<64xf32>
      "vector.store"(%0, %20, %6) <{nontemporal = false}> : (vector<128xf32>, memref<64xf32>, index) -> ()
      "gcu.border"() {leave = "triton_gcu.elementwise_fusion_region"} : () -> ()
      "gcu.border"() {enter = "tt.get_program_id"} : () -> ()
      %21 = "gpu.block_id"() <{dimension = #gpu<dim x>}> : () -> index
      %22 = "arith.index_cast"(%21) : (index) -> i32
      %23 = "arith.muli"(%22, %8) <{overflowFlags = #arith.overflow<none>}> : (i32, i32) -> i32
      "gcu.border"() {enter = "tt.get_program_id"} : () -> ()
      %24 = "gpu.block_id"() <{dimension = #gpu<dim y>}> : () -> index
      %25 = "arith.index_cast"(%24) : (index) -> i32
      %26 = "arith.muli"(%25, %8) <{overflowFlags = #arith.overflow<none>}> : (i32, i32) -> i32
      %27 = "arith.index_cast"(%23) : (i32) -> index
      %28 = "arith.addi"(%27, %12) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
      %29 = "arith.minsi"(%28, %13) : (index, index) -> index
      %30 = "arith.subi"(%29, %27) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
      %31 = "arith.minsi"(%30, %12) : (index, index) -> index
      %32 = "arith.muli"(%27, %13) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
      "gcu.border"() {enter = "tt.ptr_to_int"} : () -> ()
      %33 = "gcu.ptr2int"(%arg4) : (!gcu.ptr<f16>) -> i64
      "gcu.border"() {leave = "tt.ptr_to_int"} : () -> ()
      %34 = "arith.index_cast"(%32) : (index) -> i64
      %35 = "arith.muli"(%34, %16) <{overflowFlags = #arith.overflow<none>}> : (i64, i64) -> i64
      %36 = "arith.addi"(%33, %35) <{overflowFlags = #arith.overflow<none>}> : (i64, i64) -> i64
      %37 = "arith.index_cast"(%26) : (i32) -> index
      %38 = "arith.addi"(%37, %12) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
      %39 = "arith.minsi"(%38, %13) : (index, index) -> index
      %40 = "arith.subi"(%39, %37) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
      %41 = "arith.minsi"(%40, %12) : (index, index) -> index
      "gcu.border"() {enter = "tt.ptr_to_int"} : () -> ()
      %42 = "gcu.ptr2int"(%arg5) : (!gcu.ptr<f16>) -> i64
      "gcu.border"() {leave = "tt.ptr_to_int"} : () -> ()
      %43 = "arith.index_cast"(%37) : (index) -> i64
      %44 = "arith.muli"(%43, %16) <{overflowFlags = #arith.overflow<none>}> : (i64, i64) -> i64
      "gcu.border"() {enter = "scf.for"} : () -> ()
      %45 = "memref.alloc"() <{operandSegmentSizes = array<i32: 0, 0>}> : () -> memref<8x8xf32>
      %46 = "scf.for"(%11, %9, %10, %19) ({
      ^bb0(%arg8: i32, %arg9: memref<8x8xf32>):
        %83 = "arith.muli"(%arg8, %8) <{overflowFlags = #arith.overflow<none>}> : (i32, i32) -> i32
        %84 = "arith.index_cast"(%83) : (i32) -> index
        %85 = "arith.addi"(%84, %12) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
        %86 = "arith.minsi"(%85, %13) : (index, index) -> index
        %87 = "arith.subi"(%86, %84) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
        %88 = "arith.minsi"(%87, %12) : (index, index) -> index
        %89 = "arith.index_cast"(%84) : (index) -> i64
        %90 = "arith.muli"(%89, %16) <{overflowFlags = #arith.overflow<none>}> : (i64, i64) -> i64
        %91 = "arith.addi"(%36, %90) <{overflowFlags = #arith.overflow<none>}> : (i64, i64) -> i64
        "gcu.border"() {enter = "triton_gcu.int2ptr"} : () -> ()
        %92 = "gcu.int2ptr"(%91) : (i64) -> !gcu.ptr<f16>
        "gcu.border"() {leave = "triton_gcu.int2ptr"} : () -> ()
        "gcu.border"() {enter = "triton_gcu.load"} : () -> ()
        %93 = "memref.alloc"() <{operandSegmentSizes = array<i32: 0, 0>}> : () -> memref<16x4xf16>
        %94 = "arith.cmpi"(%31, %6) <{predicate = 4 : i64}> : (index, index) -> i1
        %95 = "arith.cmpi"(%88, %6) <{predicate = 4 : i64}> : (index, index) -> i1
        %96 = "arith.andi"(%94, %95) : (i1, i1) -> i1
        %97 = "scf.if"(%96) ({
          %145 = "gcu.ptr2memref"(%92) : (!gcu.ptr<f16>) -> memref<?xf16>
          %146 = "gpu.thread_id"() <{dimension = #gpu<dim x>}> : () -> index
          %147 = "arith.remsi"(%146, %5) : (index, index) -> index
          %148 = "arith.muli"(%147, %5) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
          %149 = "arith.index_cast"(%148) : (index) -> i32
          %150 = "arith.maxsi"(%31, %6) : (index, index) -> index
          %151 = "arith.minsi"(%150, %12) : (index, index) -> index
          %152 = "arith.index_cast"(%151) : (index) -> i32
          %153 = "arith.subi"(%88, %148) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
          %154 = "arith.maxsi"(%153, %6) : (index, index) -> index
          %155 = "arith.minsi"(%154, %5) : (index, index) -> index
          %156 = "arith.index_cast"(%155) : (index) -> i32
          %157 = "arith.muli"(%151, %155) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
          %158 = "arith.subi"(%12, %151) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
          %159 = "arith.subi"(%5, %155) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
          %160 = "arith.addi"(%158, %159) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
          %161 = "arith.cmpi"(%160, %6) <{predicate = 4 : i64}> : (index, index) -> i1
          %162 = "memref.reinterpret_cast"(%145, %6, %31, %13, %13, %15) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>, static_offsets = array<i64: -9223372036854775808>, static_sizes = array<i64: -9223372036854775808, -9223372036854775808>, static_strides = array<i64: -9223372036854775808, -9223372036854775808>}> : (memref<?xf16>, index, index, index, index, index) -> memref<?x?xf16>
          %163 = "arith.cmpi"(%157, %6) <{predicate = 1 : i64}> : (index, index) -> i1
          %164 = "arith.andi"(%161, %163) : (i1, i1) -> i1
          "scf.if"(%164) ({
            %165 = "arith.cmpi"(%158, %4) <{predicate = 3 : i64}> : (index, index) -> i1
            %166 = "arith.cmpi"(%159, %4) <{predicate = 3 : i64}> : (index, index) -> i1
            %167 = "arith.andi"(%165, %166) : (i1, i1) -> i1
            "scf.if"(%167) ({
              "memref_ext.slice_pad_start"(%93, %162, %11, %149, %152, %156, %14, %18, %15) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 1, 1, 1>}> : (memref<16x4xf16>, memref<?x?xf16>, i32, i32, i32, i32, f16, memref<3xi32>, index) -> ()
              "scf.yield"() : () -> ()
            }, {
              "affine.for"() <{lowerBoundMap = #map, operandSegmentSizes = array<i32: 0, 0, 0>, step = 1 : index, upperBoundMap = #map2}> ({
              ^bb0(%arg16: index):
                "affine.for"() <{lowerBoundMap = #map, operandSegmentSizes = array<i32: 0, 0, 0>, step = 1 : index, upperBoundMap = #map1}> ({
                ^bb0(%arg17: index):
                  "memref.store"(%14, %93, %arg16, %arg17) <{nontemporal = false}> : (f16, memref<16x4xf16>, index, index) -> ()
                  "affine.yield"() : () -> ()
                }) : () -> ()
                "affine.yield"() : () -> ()
              }) : () -> ()
              "gcu.mfence"() <{mfence_type = #gcu.mfence_type<memory>}> : () -> ()
              "memref_ext.slice_deslice_start"(%93, %162, %11, %149, %152, %156, %11, %11, %18, %15) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2, 1, 1>}> : (memref<16x4xf16>, memref<?x?xf16>, i32, i32, i32, i32, i32, i32, memref<3xi32>, index) -> ()
              "scf.yield"() : () -> ()
            }) : (i1) -> ()
            "scf.yield"() : () -> ()
          }, {
            "scf.if"(%163) ({
              "memref_ext.slice_start"(%93, %162, %11, %149, %14, %18, %15) <{operandSegmentSizes = array<i32: 1, 1, 2, 1, 1, 1>}> : (memref<16x4xf16>, memref<?x?xf16>, i32, i32, f16, memref<3xi32>, index) -> ()
              "scf.yield"() : () -> ()
            }, {
              "memref_ext.memset_start"(%93, %14, %18, %15) : (memref<16x4xf16>, f16, memref<3xi32>, index) -> ()
              "scf.yield"() : () -> ()
            }) : (i1) -> ()
            "scf.yield"() : () -> ()
          }) : (i1) -> ()
          "scf.yield"(%157) : (index) -> ()
        }, {
          "affine.for"() <{lowerBoundMap = #map, operandSegmentSizes = array<i32: 0, 0, 0>, step = 1 : index, upperBoundMap = #map2}> ({
          ^bb0(%arg14: index):
            "affine.for"() <{lowerBoundMap = #map, operandSegmentSizes = array<i32: 0, 0, 0>, step = 1 : index, upperBoundMap = #map1}> ({
            ^bb0(%arg15: index):
              "memref.store"(%14, %93, %arg14, %arg15) <{nontemporal = false}> : (f16, memref<16x4xf16>, index, index) -> ()
              "affine.yield"() : () -> ()
            }) : () -> ()
            "affine.yield"() : () -> ()
          }) : () -> ()
          "gcu.mfence"() <{mfence_type = #gcu.mfence_type<memory>}> : () -> ()
          "scf.yield"(%6) : (index) -> ()
        }) : (i1) -> index
        "gcu.border"() {leave = "triton_gcu.load"} : () -> ()
        %98 = "arith.muli"(%84, %13) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
        %99 = "arith.index_cast"(%98) : (index) -> i64
        %100 = "arith.muli"(%99, %16) <{overflowFlags = #arith.overflow<none>}> : (i64, i64) -> i64
        %101 = "arith.addi"(%42, %100) <{overflowFlags = #arith.overflow<none>}> : (i64, i64) -> i64
        %102 = "arith.addi"(%101, %44) <{overflowFlags = #arith.overflow<none>}> : (i64, i64) -> i64
        "gcu.border"() {enter = "triton_gcu.int2ptr"} : () -> ()
        %103 = "gcu.int2ptr"(%102) : (i64) -> !gcu.ptr<f16>
        "gcu.border"() {leave = "triton_gcu.int2ptr"} : () -> ()
        "gcu.border"() {enter = "triton_gcu.load"} : () -> ()
        %104 = "memref.alloc"() <{operandSegmentSizes = array<i32: 0, 0>}> : () -> memref<16x4xf16>
        %105 = "arith.cmpi"(%41, %6) <{predicate = 4 : i64}> : (index, index) -> i1
        %106 = "arith.andi"(%95, %105) : (i1, i1) -> i1
        %107 = "scf.if"(%106) ({
          %122 = "gcu.ptr2memref"(%103) : (!gcu.ptr<f16>) -> memref<?xf16>
          %123 = "gpu.thread_id"() <{dimension = #gpu<dim x>}> : () -> index
          %124 = "arith.remsi"(%123, %5) : (index, index) -> index
          %125 = "arith.muli"(%124, %5) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
          %126 = "arith.index_cast"(%125) : (index) -> i32
          %127 = "arith.maxsi"(%88, %6) : (index, index) -> index
          %128 = "arith.minsi"(%127, %12) : (index, index) -> index
          %129 = "arith.index_cast"(%128) : (index) -> i32
          %130 = "arith.subi"(%41, %125) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
          %131 = "arith.maxsi"(%130, %6) : (index, index) -> index
          %132 = "arith.minsi"(%131, %5) : (index, index) -> index
          %133 = "arith.index_cast"(%132) : (index) -> i32
          %134 = "arith.muli"(%128, %132) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
          %135 = "arith.subi"(%12, %128) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
          %136 = "arith.subi"(%5, %132) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
          %137 = "arith.addi"(%135, %136) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
          %138 = "arith.cmpi"(%137, %6) <{predicate = 4 : i64}> : (index, index) -> i1
          %139 = "memref.reinterpret_cast"(%122, %6, %88, %13, %13, %15) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>, static_offsets = array<i64: -9223372036854775808>, static_sizes = array<i64: -9223372036854775808, -9223372036854775808>, static_strides = array<i64: -9223372036854775808, -9223372036854775808>}> : (memref<?xf16>, index, index, index, index, index) -> memref<?x?xf16>
          %140 = "arith.cmpi"(%134, %6) <{predicate = 1 : i64}> : (index, index) -> i1
          %141 = "arith.andi"(%138, %140) : (i1, i1) -> i1
          "scf.if"(%141) ({
            %142 = "arith.cmpi"(%135, %4) <{predicate = 3 : i64}> : (index, index) -> i1
            %143 = "arith.cmpi"(%136, %4) <{predicate = 3 : i64}> : (index, index) -> i1
            %144 = "arith.andi"(%142, %143) : (i1, i1) -> i1
            "scf.if"(%144) ({
              "memref_ext.slice_pad_start"(%104, %139, %11, %126, %129, %133, %14, %18, %3) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 1, 1, 1>}> : (memref<16x4xf16>, memref<?x?xf16>, i32, i32, i32, i32, f16, memref<3xi32>, index) -> ()
              "scf.yield"() : () -> ()
            }, {
              "affine.for"() <{lowerBoundMap = #map, operandSegmentSizes = array<i32: 0, 0, 0>, step = 1 : index, upperBoundMap = #map2}> ({
              ^bb0(%arg12: index):
                "affine.for"() <{lowerBoundMap = #map, operandSegmentSizes = array<i32: 0, 0, 0>, step = 1 : index, upperBoundMap = #map1}> ({
                ^bb0(%arg13: index):
                  "memref.store"(%14, %104, %arg12, %arg13) <{nontemporal = false}> : (f16, memref<16x4xf16>, index, index) -> ()
                  "affine.yield"() : () -> ()
                }) : () -> ()
                "affine.yield"() : () -> ()
              }) : () -> ()
              "gcu.mfence"() <{mfence_type = #gcu.mfence_type<memory>}> : () -> ()
              "memref_ext.slice_deslice_start"(%104, %139, %11, %126, %129, %133, %11, %11, %18, %3) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2, 1, 1>}> : (memref<16x4xf16>, memref<?x?xf16>, i32, i32, i32, i32, i32, i32, memref<3xi32>, index) -> ()
              "scf.yield"() : () -> ()
            }) : (i1) -> ()
            "scf.yield"() : () -> ()
          }, {
            "scf.if"(%140) ({
              "memref_ext.slice_start"(%104, %139, %11, %126, %14, %18, %3) <{operandSegmentSizes = array<i32: 1, 1, 2, 1, 1, 1>}> : (memref<16x4xf16>, memref<?x?xf16>, i32, i32, f16, memref<3xi32>, index) -> ()
              "scf.yield"() : () -> ()
            }, {
              "memref_ext.memset_start"(%104, %14, %18, %3) : (memref<16x4xf16>, f16, memref<3xi32>, index) -> ()
              "scf.yield"() : () -> ()
            }) : (i1) -> ()
            "scf.yield"() : () -> ()
          }) : (i1) -> ()
          "scf.yield"(%134) : (index) -> ()
        }, {
          "affine.for"() <{lowerBoundMap = #map, operandSegmentSizes = array<i32: 0, 0, 0>, step = 1 : index, upperBoundMap = #map2}> ({
          ^bb0(%arg10: index):
            "affine.for"() <{lowerBoundMap = #map, operandSegmentSizes = array<i32: 0, 0, 0>, step = 1 : index, upperBoundMap = #map1}> ({
            ^bb0(%arg11: index):
              "memref.store"(%14, %104, %arg10, %arg11) <{nontemporal = false}> : (f16, memref<16x4xf16>, index, index) -> ()
              "affine.yield"() : () -> ()
            }) : () -> ()
            "affine.yield"() : () -> ()
          }) : () -> ()
          "gcu.mfence"() <{mfence_type = #gcu.mfence_type<memory>}> : () -> ()
          "scf.yield"(%6) : (index) -> ()
        }) : (i1) -> index
        "gcu.border"() {leave = "triton_gcu.load"} : () -> ()
        "scf.if"(%96) ({
          "memref.dma_wait"(%18, %15, %97) : (memref<3xi32>, index, index) -> ()
          "scf.yield"() : () -> ()
        }, {
        }) : (i1) -> ()
        "gcu.border"() {enter = "ttg.convert_layout"} : () -> ()
        %108 = "memref.alloc"() <{operandSegmentSizes = array<i32: 0, 0>}> : () -> memref<16x16xf16, 2>
        %109 = "gpu.thread_id"() <{dimension = #gpu<dim x>}> : () -> index
        %110 = "arith.remsi"(%109, %5) : (index, index) -> index
        %111 = "arith.index_cast"(%110) : (index) -> i32
        %112 = "arith.muli"(%111, %2) <{overflowFlags = #arith.overflow<none>}> : (i32, i32) -> i32
        "memref_ext.deslice_start"(%108, %93, %11, %112, %18, %15) <{operandSegmentSizes = array<i32: 1, 1, 2, 1, 1>}> : (memref<16x16xf16, 2>, memref<16x4xf16>, i32, i32, memref<3xi32>, index) -> ()
        "memref.dma_wait"(%18, %15, %7) : (memref<3xi32>, index, index) -> ()
        "gpu.barrier"() : () -> ()
        %113 = "arith.divsi"(%110, %3) : (index, index) -> index
        %114 = "arith.index_cast"(%113) : (index) -> i32
        %115 = "arith.muli"(%114, %9) <{overflowFlags = #arith.overflow<none>}> : (i32, i32) -> i32
        %116 = "memref.alloc"() <{operandSegmentSizes = array<i32: 0, 0>}> : () -> memref<8x16xf16>
        "memref_ext.slice_start"(%116, %108, %115, %11, %14, %18, %15) <{operandSegmentSizes = array<i32: 1, 1, 2, 1, 1, 1>}> : (memref<8x16xf16>, memref<16x16xf16, 2>, i32, i32, f16, memref<3xi32>, index) -> ()
        "gcu.border"() {leave = "ttg.convert_layout"} : () -> ()
        "memref.dealloc"(%93) : (memref<16x4xf16>) -> ()
        "scf.if"(%106) ({
          "memref.dma_wait"(%18, %3, %107) : (memref<3xi32>, index, index) -> ()
          "scf.yield"() : () -> ()
        }, {
        }) : (i1) -> ()
        "gcu.border"() {enter = "ttg.convert_layout"} : () -> ()
        %117 = "memref.alloc"() <{operandSegmentSizes = array<i32: 0, 0>}> : () -> memref<16x16xf16, 2>
        "memref_ext.deslice_start"(%117, %104, %11, %112, %18, %6) <{operandSegmentSizes = array<i32: 1, 1, 2, 1, 1>}> : (memref<16x16xf16, 2>, memref<16x4xf16>, i32, i32, memref<3xi32>, index) -> ()
        "memref.dma_wait"(%18, %6, %7) : (memref<3xi32>, index, index) -> ()
        "gpu.barrier"() : () -> ()
        %118 = "arith.remsi"(%110, %3) : (index, index) -> index
        %119 = "arith.index_cast"(%118) : (index) -> i32
        %120 = "arith.muli"(%119, %9) <{overflowFlags = #arith.overflow<none>}> : (i32, i32) -> i32
        %121 = "memref.alloc"() <{operandSegmentSizes = array<i32: 0, 0>}> : () -> memref<16x8xf16>
        "memref_ext.slice_start"(%121, %117, %11, %120, %14, %18, %6) <{operandSegmentSizes = array<i32: 1, 1, 2, 1, 1, 1>}> : (memref<16x8xf16>, memref<16x16xf16, 2>, i32, i32, f16, memref<3xi32>, index) -> ()
        "memref.dma_wait"(%18, %6, %13) : (memref<3xi32>, index, index) -> ()
        "gcu.border"() {leave = "ttg.convert_layout"} : () -> ()
        "memref.dealloc"(%104) : (memref<16x4xf16>) -> ()
        "memref.dma_wait"(%18, %15, %13) : (memref<3xi32>, index, index) -> ()
        "gcu.border"() {enter = "tt.dot"} : () -> ()
        "gcu.matmul"(%45, %116, %121, %arg9) <{inputPrecision = 2 : i32, operandSegmentSizes = array<i32: 1, 1, 1, 1, 0>}> : (memref<8x8xf32>, memref<8x16xf16>, memref<16x8xf16>, memref<8x8xf32>) -> ()
        "gcu.border"() {leave = "tt.dot"} : () -> ()
        "memref.dealloc"(%121) : (memref<16x8xf16>) -> ()
        "memref.dealloc"(%117) : (memref<16x16xf16, 2>) -> ()
        "memref.dealloc"(%116) : (memref<8x16xf16>) -> ()
        "memref.dealloc"(%108) : (memref<16x16xf16, 2>) -> ()
        "gcu.border"() {enter = "scf.yield"} : () -> ()
        "scf.yield"(%45) : (memref<8x8xf32>) -> ()
      }) : (i32, i32, i32, memref<8x8xf32>) -> memref<8x8xf32>
      "gcu.border"() {enter = "tt.ptr_to_int"} : () -> ()
      %47 = "gcu.ptr2int"(%arg7) : (!gcu.ptr<f32>) -> i64
      "gcu.border"() {leave = "tt.ptr_to_int"} : () -> ()
      %48 = "arith.muli"(%34, %17) <{overflowFlags = #arith.overflow<none>}> : (i64, i64) -> i64
      %49 = "arith.addi"(%47, %48) <{overflowFlags = #arith.overflow<none>}> : (i64, i64) -> i64
      %50 = "arith.muli"(%43, %17) <{overflowFlags = #arith.overflow<none>}> : (i64, i64) -> i64
      %51 = "arith.addi"(%49, %50) <{overflowFlags = #arith.overflow<none>}> : (i64, i64) -> i64
      "gcu.border"() {enter = "triton_gcu.int2ptr"} : () -> ()
      %52 = "gcu.int2ptr"(%51) : (i64) -> !gcu.ptr<f32>
      "gcu.border"() {leave = "triton_gcu.int2ptr"} : () -> ()
      "gcu.border"() {enter = "triton_gcu.store"} : () -> ()
      %53 = "arith.cmpi"(%31, %6) <{predicate = 4 : i64}> : (index, index) -> i1
      %54 = "arith.cmpi"(%41, %6) <{predicate = 4 : i64}> : (index, index) -> i1
      %55 = "arith.andi"(%53, %54) : (i1, i1) -> i1
      %56 = "scf.if"(%55) ({
        %58 = "gcu.ptr2memref"(%52) : (!gcu.ptr<f32>) -> memref<?xf32>
        %59 = "gpu.thread_id"() <{dimension = #gpu<dim x>}> : () -> index
        %60 = "arith.remsi"(%59, %5) : (index, index) -> index
        %61 = "arith.divsi"(%60, %3) : (index, index) -> index
        %62 = "arith.remsi"(%59, %3) : (index, index) -> index
        %63 = "arith.muli"(%61, %1) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
        %64 = "arith.muli"(%62, %1) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
        %65 = "arith.index_cast"(%63) : (index) -> i32
        %66 = "arith.index_cast"(%64) : (index) -> i32
        %67 = "arith.subi"(%31, %63) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
        %68 = "arith.maxsi"(%67, %6) : (index, index) -> index
        %69 = "arith.minsi"(%68, %1) : (index, index) -> index
        %70 = "arith.index_cast"(%69) : (index) -> i32
        %71 = "arith.subi"(%41, %64) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
        %72 = "arith.maxsi"(%71, %6) : (index, index) -> index
        %73 = "arith.minsi"(%72, %1) : (index, index) -> index
        %74 = "arith.index_cast"(%73) : (index) -> i32
        %75 = "arith.muli"(%69, %73) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
        %76 = "arith.subi"(%1, %69) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
        %77 = "arith.subi"(%1, %73) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
        %78 = "arith.addi"(%76, %77) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
        %79 = "memref.reinterpret_cast"(%58, %6, %31, %13, %13, %15) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>, static_offsets = array<i64: -9223372036854775808>, static_sizes = array<i64: -9223372036854775808, -9223372036854775808>, static_strides = array<i64: -9223372036854775808, -9223372036854775808>}> : (memref<?xf32>, index, index, index, index, index) -> memref<?x?xf32>
        %80 = "arith.cmpi"(%78, %6) <{predicate = 4 : i64}> : (index, index) -> i1
        %81 = "arith.cmpi"(%75, %6) <{predicate = 1 : i64}> : (index, index) -> i1
        %82 = "arith.andi"(%80, %81) : (i1, i1) -> i1
        "scf.if"(%82) ({
          "memref_ext.slice_deslice_start"(%79, %46, %11, %11, %70, %74, %65, %66, %18, %6) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2, 1, 1>}> : (memref<?x?xf32>, memref<8x8xf32>, i32, i32, i32, i32, i32, i32, memref<3xi32>, index) -> ()
          "scf.yield"() : () -> ()
        }, {
          "scf.if"(%81) ({
            "memref_ext.deslice_start"(%79, %46, %65, %66, %18, %6) <{operandSegmentSizes = array<i32: 1, 1, 2, 1, 1>}> : (memref<?x?xf32>, memref<8x8xf32>, i32, i32, memref<3xi32>, index) -> ()
            "scf.yield"() : () -> ()
          }, {
          }) : (i1) -> ()
          "scf.yield"() : () -> ()
        }) : (i1) -> ()
        "scf.yield"(%75) : (index) -> ()
      }, {
        "scf.yield"(%6) : (index) -> ()
      }) : (i1) -> index
      %57 = "arith.cmpi"(%56, %6) <{predicate = 1 : i64}> : (index, index) -> i1
      "scf.if"(%57) ({
        "memref.dma_wait"(%18, %6, %56) : (memref<3xi32>, index, index) -> ()
        "scf.yield"() : () -> ()
      }, {
      }) : (i1) -> ()
      "gcu.border"() {leave = "triton_gcu.store"} : () -> ()
      "memref.dealloc"(%45) : (memref<8x8xf32>) -> ()
      "memref.dealloc"(%19) : (memref<8x8xf32>) -> ()
      "gcu.border"() {enter = "tt.return"} : () -> ()
      "func.return"() : () -> ()
    }) {llvm.linkage = #llvm.linkage<internal>} : () -> ()
    "gpu.func"() <{function_type = (!gcu.ptr<f16>, !gcu.ptr<f16>, !gcu.ptr<f32>, !gcu.ptr<f32>) -> ()}> ({
    ^bb0(%arg0: !gcu.ptr<f16>, %arg1: !gcu.ptr<f16>, %arg2: !gcu.ptr<f32>, %arg3: !gcu.ptr<f32>):
      "func.call"(%arg0, %arg1, %arg2, %arg3) <{callee = @matmul_triton_internal__}> : (!gcu.ptr<f16>, !gcu.ptr<f16>, !gcu.ptr<f32>, !gcu.ptr<f32>) -> ()
      "gpu.return"() : () -> ()
    }) {gpu.kernel, sym_name = "matmul", workgroup_attributions = 0 : i64} : () -> ()
  }) : () -> ()
}) {"ttg.cluster-dims-x" = 1 : i32, "ttg.cluster-dims-y" = 1 : i32, "ttg.cluster-dims-z" = 1 : i32, "ttg.num-ctas" = 1 : i32, "ttg.num-warps" = 4 : i32, ttg.target = "gcu:gcu300", "ttg.threads-per-warp" = 1 : i32} : () -> ()
