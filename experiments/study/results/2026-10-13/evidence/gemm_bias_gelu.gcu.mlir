#map = affine_map<() -> (0)>
#map1 = affine_map<() -> (4)>
#map2 = affine_map<() -> (16)>
"builtin.module"() ({
  "gpu.module"() <{sym_name = "triton"}> ({
    "func.func"() <{function_type = (!gcu.ptr<f16>, !gcu.ptr<f16>, !gcu.ptr<f32>, !gcu.ptr<f32>) -> (), sym_name = "matmul_triton_internal__"}> ({
    ^bb0(%arg4: !gcu.ptr<f16>, %arg5: !gcu.ptr<f16>, %arg6: !gcu.ptr<f32>, %arg7: !gcu.ptr<f32>):
      %0 = "arith.constant"() <{value = dense<4.471500e-02> : vector<128xf32>}> : () -> vector<128xf32>
      %1 = "arith.constant"() <{value = dense<0.797884583> : vector<128xf32>}> : () -> vector<128xf32>
      %2 = "arith.constant"() <{value = dense<-2.000000e+00> : vector<128xf32>}> : () -> vector<128xf32>
      %3 = "arith.constant"() <{value = dense<1.000000e+00> : vector<128xf32>}> : () -> vector<128xf32>
      %4 = "arith.constant"() <{value = dense<2.000000e+00> : vector<128xf32>}> : () -> vector<128xf32>
      %5 = "arith.constant"() <{value = dense<5.000000e-01> : vector<128xf32>}> : () -> vector<128xf32>
      %6 = "arith.constant"() <{value = dense<0.000000e+00> : vector<128xf32>}> : () -> vector<128xf32>
      %7 = "arith.constant"() <{value = 8 : index}> : () -> index
      %8 = "arith.constant"() <{value = 4 : i32}> : () -> i32
      %9 = "arith.constant"() <{value = 2 : index}> : () -> index
      %10 = "arith.constant"() <{value = 2047 : index}> : () -> index
      %11 = "arith.constant"() <{value = 4 : index}> : () -> index
      %12 = "arith.constant"() <{value = 0 : index}> : () -> index
      %13 = "arith.constant"() <{value = 64 : index}> : () -> index
      %14 = "arith.constant"() <{value = 0 : i32}> : () -> i32
      %15 = "arith.constant"() <{value = 1 : i32}> : () -> i32
      %16 = "arith.constant"() <{value = 8 : i32}> : () -> i32
      %17 = "arith.constant"() <{value = 16 : i32}> : () -> i32
      %18 = "arith.constant"() <{value = 16 : index}> : () -> index
      %19 = "arith.constant"() <{value = 128 : index}> : () -> index
      %20 = "arith.constant"() <{value = 0.000000e+00 : f16}> : () -> f16
      %21 = "arith.constant"() <{value = 1 : index}> : () -> index
      %22 = "arith.constant"() <{value = 2 : i64}> : () -> i64
      %23 = "arith.constant"() <{value = 0.000000e+00 : f32}> : () -> f32
      %24 = "arith.constant"() <{value = 4 : i64}> : () -> i64
      %25 = "memref.alloc"() <{operandSegmentSizes = array<i32: 0, 0>}> {gcu_private_tag} : () -> memref<3xi32>
      "gcu.border"() {enter = "triton_gcu.elementwise_fusion_region"} : () -> ()
      %26 = "memref.alloc"() <{operandSegmentSizes = array<i32: 0, 0>}> : () -> memref<8x8xf32>
      %27 = "memref.reinterpret_cast"(%26) <{operandSegmentSizes = array<i32: 1, 0, 0, 0>, static_offsets = array<i64: 0>, static_sizes = array<i64: 64>, static_strides = array<i64: 1>}> : (memref<8x8xf32>) -> memref<64xf32>
      "vector.store"(%6, %27, %12) <{nontemporal = false}> : (vector<128xf32>, memref<64xf32>, index) -> ()
      "gcu.border"() {leave = "triton_gcu.elementwise_fusion_region"} : () -> ()
      "gcu.border"() {enter = "tt.get_program_id"} : () -> ()
      %28 = "gpu.block_id"() <{dimension = #gpu<dim x>}> : () -> index
      %29 = "arith.index_cast"(%28) : (index) -> i32
      %30 = "arith.muli"(%29, %17) <{overflowFlags = #arith.overflow<none>}> : (i32, i32) -> i32
      "gcu.border"() {enter = "tt.get_program_id"} : () -> ()
      %31 = "gpu.block_id"() <{dimension = #gpu<dim y>}> : () -> index
      %32 = "arith.index_cast"(%31) : (index) -> i32
      %33 = "arith.muli"(%32, %17) <{overflowFlags = #arith.overflow<none>}> : (i32, i32) -> i32
      %34 = "arith.index_cast"(%30) : (i32) -> index
      %35 = "arith.addi"(%34, %18) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
      %36 = "arith.minsi"(%35, %19) : (index, index) -> index
      %37 = "arith.subi"(%36, %34) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
      %38 = "arith.minsi"(%37, %18) : (index, index) -> index
      %39 = "arith.muli"(%34, %19) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
      "gcu.border"() {enter = "tt.ptr_to_int"} : () -> ()
      %40 = "gcu.ptr2int"(%arg4) : (!gcu.ptr<f16>) -> i64
      "gcu.border"() {leave = "tt.ptr_to_int"} : () -> ()
      %41 = "arith.index_cast"(%39) : (index) -> i64
      %42 = "arith.muli"(%41, %22) <{overflowFlags = #arith.overflow<none>}> : (i64, i64) -> i64
      %43 = "arith.addi"(%40, %42) <{overflowFlags = #arith.overflow<none>}> : (i64, i64) -> i64
      %44 = "arith.index_cast"(%33) : (i32) -> index
      %45 = "arith.addi"(%44, %18) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
      %46 = "arith.minsi"(%45, %19) : (index, index) -> index
      %47 = "arith.subi"(%46, %44) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
      %48 = "arith.minsi"(%47, %18) : (index, index) -> index
      "gcu.border"() {enter = "tt.ptr_to_int"} : () -> ()
      %49 = "gcu.ptr2int"(%arg5) : (!gcu.ptr<f16>) -> i64
      "gcu.border"() {leave = "tt.ptr_to_int"} : () -> ()
      %50 = "arith.index_cast"(%44) : (index) -> i64
      %51 = "arith.muli"(%50, %22) <{overflowFlags = #arith.overflow<none>}> : (i64, i64) -> i64
      "gcu.border"() {enter = "scf.for"} : () -> ()
      %52 = "memref.alloc"() <{operandSegmentSizes = array<i32: 0, 0>}> : () -> memref<8x8xf32>
      %53 = "scf.for"(%14, %16, %15, %26) ({
      ^bb0(%arg10: i32, %arg11: memref<8x8xf32>):
        %137 = "arith.muli"(%arg10, %17) <{overflowFlags = #arith.overflow<none>}> : (i32, i32) -> i32
        %138 = "arith.index_cast"(%137) : (i32) -> index
        %139 = "arith.addi"(%138, %18) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
        %140 = "arith.minsi"(%139, %19) : (index, index) -> index
        %141 = "arith.subi"(%140, %138) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
        %142 = "arith.minsi"(%141, %18) : (index, index) -> index
        %143 = "arith.index_cast"(%138) : (index) -> i64
        %144 = "arith.muli"(%143, %22) <{overflowFlags = #arith.overflow<none>}> : (i64, i64) -> i64
        %145 = "arith.addi"(%43, %144) <{overflowFlags = #arith.overflow<none>}> : (i64, i64) -> i64
        "gcu.border"() {enter = "triton_gcu.int2ptr"} : () -> ()
        %146 = "gcu.int2ptr"(%145) : (i64) -> !gcu.ptr<f16>
        "gcu.border"() {leave = "triton_gcu.int2ptr"} : () -> ()
        "gcu.border"() {enter = "triton_gcu.load"} : () -> ()
        %147 = "memref.alloc"() <{operandSegmentSizes = array<i32: 0, 0>}> : () -> memref<16x4xf16>
        %148 = "arith.cmpi"(%38, %12) <{predicate = 4 : i64}> : (index, index) -> i1
        %149 = "arith.cmpi"(%142, %12) <{predicate = 4 : i64}> : (index, index) -> i1
        %150 = "arith.andi"(%148, %149) : (i1, i1) -> i1
        %151 = "scf.if"(%150) ({
          %199 = "gcu.ptr2memref"(%146) : (!gcu.ptr<f16>) -> memref<?xf16>
          %200 = "gpu.thread_id"() <{dimension = #gpu<dim x>}> : () -> index
          %201 = "arith.remsi"(%200, %11) : (index, index) -> index
          %202 = "arith.muli"(%201, %11) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
          %203 = "arith.index_cast"(%202) : (index) -> i32
          %204 = "arith.maxsi"(%38, %12) : (index, index) -> index
          %205 = "arith.minsi"(%204, %18) : (index, index) -> index
          %206 = "arith.index_cast"(%205) : (index) -> i32
          %207 = "arith.subi"(%142, %202) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
          %208 = "arith.maxsi"(%207, %12) : (index, index) -> index
          %209 = "arith.minsi"(%208, %11) : (index, index) -> index
          %210 = "arith.index_cast"(%209) : (index) -> i32
          %211 = "arith.muli"(%205, %209) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
          %212 = "arith.subi"(%18, %205) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
          %213 = "arith.subi"(%11, %209) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
          %214 = "arith.addi"(%212, %213) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
          %215 = "arith.cmpi"(%214, %12) <{predicate = 4 : i64}> : (index, index) -> i1
          %216 = "memref.reinterpret_cast"(%199, %12, %38, %19, %19, %21) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>, static_offsets = array<i64: -9223372036854775808>, static_sizes = array<i64: -9223372036854775808, -9223372036854775808>, static_strides = array<i64: -9223372036854775808, -9223372036854775808>}> : (memref<?xf16>, index, index, index, index, index) -> memref<?x?xf16>
          %217 = "arith.cmpi"(%211, %12) <{predicate = 1 : i64}> : (index, index) -> i1
          %218 = "arith.andi"(%215, %217) : (i1, i1) -> i1
          "scf.if"(%218) ({
            %219 = "arith.cmpi"(%212, %10) <{predicate = 3 : i64}> : (index, index) -> i1
            %220 = "arith.cmpi"(%213, %10) <{predicate = 3 : i64}> : (index, index) -> i1
            %221 = "arith.andi"(%219, %220) : (i1, i1) -> i1
            "scf.if"(%221) ({
              "memref_ext.slice_pad_start"(%147, %216, %14, %203, %206, %210, %20, %25, %21) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 1, 1, 1>}> : (memref<16x4xf16>, memref<?x?xf16>, i32, i32, i32, i32, f16, memref<3xi32>, index) -> ()
              "scf.yield"() : () -> ()
            }, {
              "affine.for"() <{lowerBoundMap = #map, operandSegmentSizes = array<i32: 0, 0, 0>, step = 1 : index, upperBoundMap = #map2}> ({
              ^bb0(%arg18: index):
                "affine.for"() <{lowerBoundMap = #map, operandSegmentSizes = array<i32: 0, 0, 0>, step = 1 : index, upperBoundMap = #map1}> ({
                ^bb0(%arg19: index):
                  "memref.store"(%20, %147, %arg18, %arg19) <{nontemporal = false}> : (f16, memref<16x4xf16>, index, index) -> ()
                  "affine.yield"() : () -> ()
                }) : () -> ()
                "affine.yield"() : () -> ()
              }) : () -> ()
              "gcu.mfence"() <{mfence_type = #gcu.mfence_type<memory>}> : () -> ()
              "memref_ext.slice_deslice_start"(%147, %216, %14, %203, %206, %210, %14, %14, %25, %21) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2, 1, 1>}> : (memref<16x4xf16>, memref<?x?xf16>, i32, i32, i32, i32, i32, i32, memref<3xi32>, index) -> ()
              "scf.yield"() : () -> ()
            }) : (i1) -> ()
            "scf.yield"() : () -> ()
          }, {
            "scf.if"(%217) ({
              "memref_ext.slice_start"(%147, %216, %14, %203, %20, %25, %21) <{operandSegmentSizes = array<i32: 1, 1, 2, 1, 1, 1>}> : (memref<16x4xf16>, memref<?x?xf16>, i32, i32, f16, memref<3xi32>, index) -> ()
              "scf.yield"() : () -> ()
            }, {
              "memref_ext.memset_start"(%147, %20, %25, %21) : (memref<16x4xf16>, f16, memref<3xi32>, index) -> ()
              "scf.yield"() : () -> ()
            }) : (i1) -> ()
            "scf.yield"() : () -> ()
          }) : (i1) -> ()
          "scf.yield"(%211) : (index) -> ()
        }, {
          "affine.for"() <{lowerBoundMap = #map, operandSegmentSizes = array<i32: 0, 0, 0>, step = 1 : index, upperBoundMap = #map2}> ({
          ^bb0(%arg16: index):
            "affine.for"() <{lowerBoundMap = #map, operandSegmentSizes = array<i32: 0, 0, 0>, step = 1 : index, upperBoundMap = #map1}> ({
            ^bb0(%arg17: index):
              "memref.store"(%20, %147, %arg16, %arg17) <{nontemporal = false}> : (f16, memref<16x4xf16>, index, index) -> ()
              "affine.yield"() : () -> ()
            }) : () -> ()
            "affine.yield"() : () -> ()
          }) : () -> ()
          "gcu.mfence"() <{mfence_type = #gcu.mfence_type<memory>}> : () -> ()
          "scf.yield"(%12) : (index) -> ()
        }) : (i1) -> index
        "gcu.border"() {leave = "triton_gcu.load"} : () -> ()
        %152 = "arith.muli"(%138, %19) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
        %153 = "arith.index_cast"(%152) : (index) -> i64
        %154 = "arith.muli"(%153, %22) <{overflowFlags = #arith.overflow<none>}> : (i64, i64) -> i64
        %155 = "arith.addi"(%49, %154) <{overflowFlags = #arith.overflow<none>}> : (i64, i64) -> i64
        %156 = "arith.addi"(%155, %51) <{overflowFlags = #arith.overflow<none>}> : (i64, i64) -> i64
        "gcu.border"() {enter = "triton_gcu.int2ptr"} : () -> ()
        %157 = "gcu.int2ptr"(%156) : (i64) -> !gcu.ptr<f16>
        "gcu.border"() {leave = "triton_gcu.int2ptr"} : () -> ()
        "gcu.border"() {enter = "triton_gcu.load"} : () -> ()
        %158 = "memref.alloc"() <{operandSegmentSizes = array<i32: 0, 0>}> : () -> memref<16x4xf16>
        %159 = "arith.cmpi"(%48, %12) <{predicate = 4 : i64}> : (index, index) -> i1
        %160 = "arith.andi"(%149, %159) : (i1, i1) -> i1
        %161 = "scf.if"(%160) ({
          %176 = "gcu.ptr2memref"(%157) : (!gcu.ptr<f16>) -> memref<?xf16>
          %177 = "gpu.thread_id"() <{dimension = #gpu<dim x>}> : () -> index
          %178 = "arith.remsi"(%177, %11) : (index, index) -> index
          %179 = "arith.muli"(%178, %11) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
          %180 = "arith.index_cast"(%179) : (index) -> i32
          %181 = "arith.maxsi"(%142, %12) : (index, index) -> index
          %182 = "arith.minsi"(%181, %18) : (index, index) -> index
          %183 = "arith.index_cast"(%182) : (index) -> i32
          %184 = "arith.subi"(%48, %179) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
          %185 = "arith.maxsi"(%184, %12) : (index, index) -> index
          %186 = "arith.minsi"(%185, %11) : (index, index) -> index
          %187 = "arith.index_cast"(%186) : (index) -> i32
          %188 = "arith.muli"(%182, %186) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
          %189 = "arith.subi"(%18, %182) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
          %190 = "arith.subi"(%11, %186) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
          %191 = "arith.addi"(%189, %190) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
          %192 = "arith.cmpi"(%191, %12) <{predicate = 4 : i64}> : (index, index) -> i1
          %193 = "memref.reinterpret_cast"(%176, %12, %142, %19, %19, %21) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>, static_offsets = array<i64: -9223372036854775808>, static_sizes = array<i64: -9223372036854775808, -9223372036854775808>, static_strides = array<i64: -9223372036854775808, -9223372036854775808>}> : (memref<?xf16>, index, index, index, index, index) -> memref<?x?xf16>
          %194 = "arith.cmpi"(%188, %12) <{predicate = 1 : i64}> : (index, index) -> i1
          %195 = "arith.andi"(%192, %194) : (i1, i1) -> i1
          "scf.if"(%195) ({
            %196 = "arith.cmpi"(%189, %10) <{predicate = 3 : i64}> : (index, index) -> i1
            %197 = "arith.cmpi"(%190, %10) <{predicate = 3 : i64}> : (index, index) -> i1
            %198 = "arith.andi"(%196, %197) : (i1, i1) -> i1
            "scf.if"(%198) ({
              "memref_ext.slice_pad_start"(%158, %193, %14, %180, %183, %187, %20, %25, %9) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 1, 1, 1>}> : (memref<16x4xf16>, memref<?x?xf16>, i32, i32, i32, i32, f16, memref<3xi32>, index) -> ()
              "scf.yield"() : () -> ()
            }, {
              "affine.for"() <{lowerBoundMap = #map, operandSegmentSizes = array<i32: 0, 0, 0>, step = 1 : index, upperBoundMap = #map2}> ({
              ^bb0(%arg14: index):
                "affine.for"() <{lowerBoundMap = #map, operandSegmentSizes = array<i32: 0, 0, 0>, step = 1 : index, upperBoundMap = #map1}> ({
                ^bb0(%arg15: index):
                  "memref.store"(%20, %158, %arg14, %arg15) <{nontemporal = false}> : (f16, memref<16x4xf16>, index, index) -> ()
                  "affine.yield"() : () -> ()
                }) : () -> ()
                "affine.yield"() : () -> ()
              }) : () -> ()
              "gcu.mfence"() <{mfence_type = #gcu.mfence_type<memory>}> : () -> ()
              "memref_ext.slice_deslice_start"(%158, %193, %14, %180, %183, %187, %14, %14, %25, %9) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2, 1, 1>}> : (memref<16x4xf16>, memref<?x?xf16>, i32, i32, i32, i32, i32, i32, memref<3xi32>, index) -> ()
              "scf.yield"() : () -> ()
            }) : (i1) -> ()
            "scf.yield"() : () -> ()
          }, {
            "scf.if"(%194) ({
              "memref_ext.slice_start"(%158, %193, %14, %180, %20, %25, %9) <{operandSegmentSizes = array<i32: 1, 1, 2, 1, 1, 1>}> : (memref<16x4xf16>, memref<?x?xf16>, i32, i32, f16, memref<3xi32>, index) -> ()
              "scf.yield"() : () -> ()
            }, {
              "memref_ext.memset_start"(%158, %20, %25, %9) : (memref<16x4xf16>, f16, memref<3xi32>, index) -> ()
              "scf.yield"() : () -> ()
            }) : (i1) -> ()
            "scf.yield"() : () -> ()
          }) : (i1) -> ()
          "scf.yield"(%188) : (index) -> ()
        }, {
          "affine.for"() <{lowerBoundMap = #map, operandSegmentSizes = array<i32: 0, 0, 0>, step = 1 : index, upperBoundMap = #map2}> ({
          ^bb0(%arg12: index):
            "affine.for"() <{lowerBoundMap = #map, operandSegmentSizes = array<i32: 0, 0, 0>, step = 1 : index, upperBoundMap = #map1}> ({
            ^bb0(%arg13: index):
              "memref.store"(%20, %158, %arg12, %arg13) <{nontemporal = false}> : (f16, memref<16x4xf16>, index, index) -> ()
              "affine.yield"() : () -> ()
            }) : () -> ()
            "affine.yield"() : () -> ()
          }) : () -> ()
          "gcu.mfence"() <{mfence_type = #gcu.mfence_type<memory>}> : () -> ()
          "scf.yield"(%12) : (index) -> ()
        }) : (i1) -> index
        "gcu.border"() {leave = "triton_gcu.load"} : () -> ()
        "scf.if"(%150) ({
          "memref.dma_wait"(%25, %21, %151) : (memref<3xi32>, index, index) -> ()
          "scf.yield"() : () -> ()
        }, {
        }) : (i1) -> ()
        "gcu.border"() {enter = "ttg.convert_layout"} : () -> ()
        %162 = "memref.alloc"() <{operandSegmentSizes = array<i32: 0, 0>}> : () -> memref<16x16xf16, 2>
        %163 = "gpu.thread_id"() <{dimension = #gpu<dim x>}> : () -> index
        %164 = "arith.remsi"(%163, %11) : (index, index) -> index
        %165 = "arith.index_cast"(%164) : (index) -> i32
        %166 = "arith.muli"(%165, %8) <{overflowFlags = #arith.overflow<none>}> : (i32, i32) -> i32
        "memref_ext.deslice_start"(%162, %147, %14, %166, %25, %21) <{operandSegmentSizes = array<i32: 1, 1, 2, 1, 1>}> : (memref<16x16xf16, 2>, memref<16x4xf16>, i32, i32, memref<3xi32>, index) -> ()
        "memref.dma_wait"(%25, %21, %13) : (memref<3xi32>, index, index) -> ()
        "gpu.barrier"() : () -> ()
        %167 = "arith.divsi"(%164, %9) : (index, index) -> index
        %168 = "arith.index_cast"(%167) : (index) -> i32
        %169 = "arith.muli"(%168, %16) <{overflowFlags = #arith.overflow<none>}> : (i32, i32) -> i32
        %170 = "memref.alloc"() <{operandSegmentSizes = array<i32: 0, 0>}> : () -> memref<8x16xf16>
        "memref_ext.slice_start"(%170, %162, %169, %14, %20, %25, %21) <{operandSegmentSizes = array<i32: 1, 1, 2, 1, 1, 1>}> : (memref<8x16xf16>, memref<16x16xf16, 2>, i32, i32, f16, memref<3xi32>, index) -> ()
        "gcu.border"() {leave = "ttg.convert_layout"} : () -> ()
        "memref.dealloc"(%147) : (memref<16x4xf16>) -> ()
        "scf.if"(%160) ({
          "memref.dma_wait"(%25, %9, %161) : (memref<3xi32>, index, index) -> ()
          "scf.yield"() : () -> ()
        }, {
        }) : (i1) -> ()
        "gcu.border"() {enter = "ttg.convert_layout"} : () -> ()
        %171 = "memref.alloc"() <{operandSegmentSizes = array<i32: 0, 0>}> : () -> memref<16x16xf16, 2>
        "memref_ext.deslice_start"(%171, %158, %14, %166, %25, %12) <{operandSegmentSizes = array<i32: 1, 1, 2, 1, 1>}> : (memref<16x16xf16, 2>, memref<16x4xf16>, i32, i32, memref<3xi32>, index) -> ()
        "memref.dma_wait"(%25, %12, %13) : (memref<3xi32>, index, index) -> ()
        "gpu.barrier"() : () -> ()
        %172 = "arith.remsi"(%164, %9) : (index, index) -> index
        %173 = "arith.index_cast"(%172) : (index) -> i32
        %174 = "arith.muli"(%173, %16) <{overflowFlags = #arith.overflow<none>}> : (i32, i32) -> i32
        %175 = "memref.alloc"() <{operandSegmentSizes = array<i32: 0, 0>}> : () -> memref<16x8xf16>
        "memref_ext.slice_start"(%175, %171, %14, %174, %20, %25, %12) <{operandSegmentSizes = array<i32: 1, 1, 2, 1, 1, 1>}> : (memref<16x8xf16>, memref<16x16xf16, 2>, i32, i32, f16, memref<3xi32>, index) -> ()
        "memref.dma_wait"(%25, %12, %19) : (memref<3xi32>, index, index) -> ()
        "gcu.border"() {leave = "ttg.convert_layout"} : () -> ()
        "memref.dealloc"(%158) : (memref<16x4xf16>) -> ()
        "memref.dma_wait"(%25, %21, %19) : (memref<3xi32>, index, index) -> ()
        "gcu.border"() {enter = "tt.dot"} : () -> ()
        "gcu.matmul"(%52, %170, %175, %arg11) <{inputPrecision = 2 : i32, operandSegmentSizes = array<i32: 1, 1, 1, 1, 0>}> : (memref<8x8xf32>, memref<8x16xf16>, memref<16x8xf16>, memref<8x8xf32>) -> ()
        "gcu.border"() {leave = "tt.dot"} : () -> ()
        "memref.dealloc"(%175) : (memref<16x8xf16>) -> ()
        "memref.dealloc"(%171) : (memref<16x16xf16, 2>) -> ()
        "memref.dealloc"(%170) : (memref<8x16xf16>) -> ()
        "memref.dealloc"(%162) : (memref<16x16xf16, 2>) -> ()
        "gcu.border"() {enter = "scf.yield"} : () -> ()
        "scf.yield"(%52) : (memref<8x8xf32>) -> ()
      }) : (i32, i32, i32, memref<8x8xf32>) -> memref<8x8xf32>
      "gcu.border"() {enter = "tt.ptr_to_int"} : () -> ()
      %54 = "gcu.ptr2int"(%arg6) : (!gcu.ptr<f32>) -> i64
      "gcu.border"() {leave = "tt.ptr_to_int"} : () -> ()
      %55 = "arith.muli"(%50, %24) <{overflowFlags = #arith.overflow<none>}> : (i64, i64) -> i64
      %56 = "arith.addi"(%54, %55) <{overflowFlags = #arith.overflow<none>}> : (i64, i64) -> i64
      "gcu.border"() {enter = "triton_gcu.int2ptr"} : () -> ()
      %57 = "gcu.int2ptr"(%56) : (i64) -> !gcu.ptr<f32>
      "gcu.border"() {leave = "triton_gcu.int2ptr"} : () -> ()
      "gcu.border"() {enter = "triton_gcu.load"} : () -> ()
      %58 = "memref.alloc"() <{operandSegmentSizes = array<i32: 0, 0>}> : () -> memref<4xf32>
      %59 = "arith.cmpi"(%47, %12) <{predicate = 4 : i64}> : (index, index) -> i1
      "scf.if"(%59) ({
        %122 = "gcu.ptr2memref"(%57) : (!gcu.ptr<f32>) -> memref<?xf32>
        %123 = "gpu.thread_id"() <{dimension = #gpu<dim x>}> : () -> index
        %124 = "arith.remsi"(%123, %11) : (index, index) -> index
        %125 = "arith.muli"(%124, %11) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
        %126 = "arith.index_cast"(%125) : (index) -> i32
        %127 = "arith.subi"(%47, %125) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
        %128 = "arith.maxsi"(%127, %12) : (index, index) -> index
        %129 = "arith.minsi"(%128, %11) : (index, index) -> index
        %130 = "arith.index_cast"(%129) : (index) -> i32
        %131 = "arith.subi"(%11, %129) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
        %132 = "arith.cmpi"(%131, %12) <{predicate = 4 : i64}> : (index, index) -> i1
        %133 = "memref.reinterpret_cast"(%122, %12, %47, %21) <{operandSegmentSizes = array<i32: 1, 1, 1, 1>, static_offsets = array<i64: -9223372036854775808>, static_sizes = array<i64: -9223372036854775808>, static_strides = array<i64: -9223372036854775808>}> : (memref<?xf32>, index, index, index) -> memref<?xf32>
        %134 = "arith.cmpi"(%129, %12) <{predicate = 1 : i64}> : (index, index) -> i1
        %135 = "arith.andi"(%132, %134) : (i1, i1) -> i1
        "scf.if"(%135) ({
          %136 = "arith.cmpi"(%131, %10) <{predicate = 3 : i64}> : (index, index) -> i1
          "scf.if"(%136) ({
            "memref_ext.slice_pad_start"(%58, %133, %126, %130, %23, %25, %12) <{operandSegmentSizes = array<i32: 1, 1, 1, 1, 1, 1, 1>}> : (memref<4xf32>, memref<?xf32>, i32, i32, f32, memref<3xi32>, index) -> ()
            "scf.yield"() : () -> ()
          }, {
            "affine.for"() <{lowerBoundMap = #map, operandSegmentSizes = array<i32: 0, 0, 0>, step = 1 : index, upperBoundMap = #map1}> ({
            ^bb0(%arg9: index):
              "memref.store"(%23, %58, %arg9) <{nontemporal = false}> : (f32, memref<4xf32>, index) -> ()
              "affine.yield"() : () -> ()
            }) : () -> ()
            "gcu.mfence"() <{mfence_type = #gcu.mfence_type<memory>}> : () -> ()
            "memref_ext.slice_deslice_start"(%58, %133, %126, %130, %14, %25, %12) <{operandSegmentSizes = array<i32: 1, 1, 1, 1, 1, 1, 1>}> : (memref<4xf32>, memref<?xf32>, i32, i32, i32, memref<3xi32>, index) -> ()
            "scf.yield"() : () -> ()
          }) : (i1) -> ()
          "scf.yield"() : () -> ()
        }, {
          "scf.if"(%134) ({
            "memref_ext.slice_start"(%58, %133, %126, %23, %25, %12) <{operandSegmentSizes = array<i32: 1, 1, 1, 1, 1, 1>}> : (memref<4xf32>, memref<?xf32>, i32, f32, memref<3xi32>, index) -> ()
            "scf.yield"() : () -> ()
          }, {
            "memref_ext.memset_start"(%58, %23, %25, %12) : (memref<4xf32>, f32, memref<3xi32>, index) -> ()
            "scf.yield"() : () -> ()
          }) : (i1) -> ()
          "scf.yield"() : () -> ()
        }) : (i1) -> ()
        "memref.dma_wait"(%25, %12, %129) : (memref<3xi32>, index, index) -> ()
        "scf.yield"() : () -> ()
      }, {
        "affine.for"() <{lowerBoundMap = #map, operandSegmentSizes = array<i32: 0, 0, 0>, step = 1 : index, upperBoundMap = #map1}> ({
        ^bb0(%arg8: index):
          "memref.store"(%23, %58, %arg8) <{nontemporal = false}> : (f32, memref<4xf32>, index) -> ()
          "affine.yield"() : () -> ()
        }) : () -> ()
        "gcu.mfence"() <{mfence_type = #gcu.mfence_type<memory>}> : () -> ()
        "scf.yield"() : () -> ()
      }) : (i1) -> ()
      "gcu.border"() {leave = "triton_gcu.load"} : () -> ()
      "gcu.border"() {enter = "ttg.convert_layout"} : () -> ()
      %60 = "memref.alloc"() <{operandSegmentSizes = array<i32: 0, 0>}> : () -> memref<16xf32, 2>
      %61 = "gpu.thread_id"() <{dimension = #gpu<dim x>}> : () -> index
      %62 = "arith.remsi"(%61, %11) : (index, index) -> index
      %63 = "arith.index_cast"(%62) : (index) -> i32
      %64 = "arith.muli"(%63, %8) <{overflowFlags = #arith.overflow<none>}> : (i32, i32) -> i32
      "memref_ext.deslice_start"(%60, %58, %64, %25, %21) <{operandSegmentSizes = array<i32: 1, 1, 1, 1, 1>}> : (memref<16xf32, 2>, memref<4xf32>, i32, memref<3xi32>, index) -> ()
      "memref.dma_wait"(%25, %21, %11) : (memref<3xi32>, index, index) -> ()
      "gpu.barrier"() : () -> ()
      %65 = "arith.remsi"(%61, %9) : (index, index) -> index
      %66 = "arith.index_cast"(%65) : (index) -> i32
      %67 = "arith.muli"(%66, %16) <{overflowFlags = #arith.overflow<none>}> : (i32, i32) -> i32
      %68 = "memref.alloc"() <{operandSegmentSizes = array<i32: 0, 0>}> : () -> memref<8xf32>
      "memref_ext.slice_start"(%68, %60, %67, %23, %25, %21) <{operandSegmentSizes = array<i32: 1, 1, 1, 1, 1, 1>}> : (memref<8xf32>, memref<16xf32, 2>, i32, f32, memref<3xi32>, index) -> ()
      "gcu.border"() {leave = "ttg.convert_layout"} : () -> ()
      "memref.dealloc"(%58) : (memref<4xf32>) -> ()
      "gcu.border"() {enter = "tt.expand_dims"} : () -> ()
      %69 = "memref.reinterpret_cast"(%68) <{operandSegmentSizes = array<i32: 1, 0, 0, 0>, static_offsets = array<i64: 0>, static_sizes = array<i64: 1, 8>, static_strides = array<i64: 8, 1>}> : (memref<8xf32>) -> memref<1x8xf32>
      "gcu.border"() {leave = "tt.expand_dims"} : () -> ()
      "memref.dma_wait"(%25, %21, %7) : (memref<3xi32>, index, index) -> ()
      "gcu.border"() {enter = "tt.broadcast"} : () -> ()
      %70 = "memref.alloc"() <{operandSegmentSizes = array<i32: 0, 0>}> : () -> memref<8x8xf32>
      "memref_ext.broadcast_start"(%70, %69, %25, %12) : (memref<8x8xf32>, memref<1x8xf32>, memref<3xi32>, index) -> ()
      "memref.dma_wait"(%25, %12, %7) : (memref<3xi32>, index, index) -> ()
      "gcu.border"() {leave = "tt.broadcast"} : () -> ()
      "memref.dealloc"(%68) : (memref<8xf32>) -> ()
      "memref.dealloc"(%60) : (memref<16xf32, 2>) -> ()
      "gcu.border"() {enter = "triton_gcu.elementwise_fusion_region"} : () -> ()
      %71 = "memref.alloc"() <{operandSegmentSizes = array<i32: 0, 0>}> : () -> memref<8x8xf32>
      %72 = "memref.reinterpret_cast"(%71) <{operandSegmentSizes = array<i32: 1, 0, 0, 0>, static_offsets = array<i64: 0>, static_sizes = array<i64: 64>, static_strides = array<i64: 1>}> : (memref<8x8xf32>) -> memref<64xf32>
      %73 = "memref.reinterpret_cast"(%53) <{operandSegmentSizes = array<i32: 1, 0, 0, 0>, static_offsets = array<i64: 0>, static_sizes = array<i64: 64>, static_strides = array<i64: 1>}> : (memref<8x8xf32>) -> memref<64xf32>
      %74 = "memref.reinterpret_cast"(%70) <{operandSegmentSizes = array<i32: 1, 0, 0, 0>, static_offsets = array<i64: 0>, static_sizes = array<i64: 64>, static_strides = array<i64: 1>}> : (memref<8x8xf32>) -> memref<64xf32>
      %75 = "vector.load"(%73, %12) <{nontemporal = false}> : (memref<64xf32>, index) -> vector<128xf32>
      %76 = "vector.load"(%74, %12) <{nontemporal = false}> : (memref<64xf32>, index) -> vector<128xf32>
      %77 = "arith.addf"(%75, %76) <{fastmath = #arith.fastmath<none>}> : (vector<128xf32>, vector<128xf32>) -> vector<128xf32>
      %78 = "arith.mulf"(%77, %0) <{fastmath = #arith.fastmath<none>}> : (vector<128xf32>, vector<128xf32>) -> vector<128xf32>
      %79 = "arith.mulf"(%78, %77) <{fastmath = #arith.fastmath<none>}> : (vector<128xf32>, vector<128xf32>) -> vector<128xf32>
      %80 = "gcu.extern_elementwise_op"(%79, %77, %77) <{symbol = "__gcu_mac_fp32"}> : (vector<128xf32>, vector<128xf32>, vector<128xf32>) -> vector<128xf32>
      %81 = "arith.mulf"(%80, %1) <{fastmath = #arith.fastmath<none>}> : (vector<128xf32>, vector<128xf32>) -> vector<128xf32>
      %82 = "arith.mulf"(%81, %2) <{fastmath = #arith.fastmath<none>}> : (vector<128xf32>, vector<128xf32>) -> vector<128xf32>
      %83 = "math.exp"(%82) <{fastmath = #arith.fastmath<none>}> : (vector<128xf32>) -> vector<128xf32>
      %84 = "arith.addf"(%83, %3) <{fastmath = #arith.fastmath<none>}> : (vector<128xf32>, vector<128xf32>) -> vector<128xf32>
      %85 = "arith.divf"(%4, %84) <{fastmath = #arith.fastmath<none>}> : (vector<128xf32>, vector<128xf32>) -> vector<128xf32>
      %86 = "arith.subf"(%85, %3) <{fastmath = #arith.fastmath<none>}> : (vector<128xf32>, vector<128xf32>) -> vector<128xf32>
      %87 = "arith.mulf"(%77, %5) <{fastmath = #arith.fastmath<none>}> : (vector<128xf32>, vector<128xf32>) -> vector<128xf32>
      %88 = "arith.addf"(%86, %3) <{fastmath = #arith.fastmath<none>}> : (vector<128xf32>, vector<128xf32>) -> vector<128xf32>
      %89 = "arith.mulf"(%87, %88) <{fastmath = #arith.fastmath<none>}> : (vector<128xf32>, vector<128xf32>) -> vector<128xf32>
      "vector.store"(%89, %72, %12) <{nontemporal = false}> : (vector<128xf32>, memref<64xf32>, index) -> ()
      "gcu.border"() {leave = "triton_gcu.elementwise_fusion_region"} : () -> ()
      "memref.dealloc"(%70) : (memref<8x8xf32>) -> ()
      "memref.dealloc"(%52) : (memref<8x8xf32>) -> ()
      "memref.dealloc"(%26) : (memref<8x8xf32>) -> ()
      "gcu.border"() {enter = "tt.ptr_to_int"} : () -> ()
      %90 = "gcu.ptr2int"(%arg7) : (!gcu.ptr<f32>) -> i64
      "gcu.border"() {leave = "tt.ptr_to_int"} : () -> ()
      %91 = "arith.muli"(%41, %24) <{overflowFlags = #arith.overflow<none>}> : (i64, i64) -> i64
      %92 = "arith.addi"(%90, %91) <{overflowFlags = #arith.overflow<none>}> : (i64, i64) -> i64
      %93 = "arith.addi"(%92, %55) <{overflowFlags = #arith.overflow<none>}> : (i64, i64) -> i64
      "gcu.border"() {enter = "triton_gcu.int2ptr"} : () -> ()
      %94 = "gcu.int2ptr"(%93) : (i64) -> !gcu.ptr<f32>
      "gcu.border"() {leave = "triton_gcu.int2ptr"} : () -> ()
      "gcu.border"() {enter = "triton_gcu.store"} : () -> ()
      %95 = "arith.cmpi"(%38, %12) <{predicate = 4 : i64}> : (index, index) -> i1
      %96 = "arith.cmpi"(%48, %12) <{predicate = 4 : i64}> : (index, index) -> i1
      %97 = "arith.andi"(%95, %96) : (i1, i1) -> i1
      %98 = "scf.if"(%97) ({
        %100 = "gcu.ptr2memref"(%94) : (!gcu.ptr<f32>) -> memref<?xf32>
        %101 = "arith.divsi"(%62, %9) : (index, index) -> index
        %102 = "arith.muli"(%101, %7) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
        %103 = "arith.muli"(%65, %7) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
        %104 = "arith.index_cast"(%102) : (index) -> i32
        %105 = "arith.index_cast"(%103) : (index) -> i32
        %106 = "arith.subi"(%38, %102) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
        %107 = "arith.maxsi"(%106, %12) : (index, index) -> index
        %108 = "arith.minsi"(%107, %7) : (index, index) -> index
        %109 = "arith.index_cast"(%108) : (index) -> i32
        %110 = "arith.subi"(%48, %103) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
        %111 = "arith.maxsi"(%110, %12) : (index, index) -> index
        %112 = "arith.minsi"(%111, %7) : (index, index) -> index
        %113 = "arith.index_cast"(%112) : (index) -> i32
        %114 = "arith.muli"(%108, %112) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
        %115 = "arith.subi"(%7, %108) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
        %116 = "arith.subi"(%7, %112) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
        %117 = "arith.addi"(%115, %116) <{overflowFlags = #arith.overflow<none>}> : (index, index) -> index
        %118 = "memref.reinterpret_cast"(%100, %12, %38, %19, %19, %21) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>, static_offsets = array<i64: -9223372036854775808>, static_sizes = array<i64: -9223372036854775808, -9223372036854775808>, static_strides = array<i64: -9223372036854775808, -9223372036854775808>}> : (memref<?xf32>, index, index, index, index, index) -> memref<?x?xf32>
        %119 = "arith.cmpi"(%117, %12) <{predicate = 4 : i64}> : (index, index) -> i1
        %120 = "arith.cmpi"(%114, %12) <{predicate = 1 : i64}> : (index, index) -> i1
        %121 = "arith.andi"(%119, %120) : (i1, i1) -> i1
        "scf.if"(%121) ({
          "memref_ext.slice_deslice_start"(%118, %71, %14, %14, %109, %113, %104, %105, %25, %12) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2, 1, 1>}> : (memref<?x?xf32>, memref<8x8xf32>, i32, i32, i32, i32, i32, i32, memref<3xi32>, index) -> ()
          "scf.yield"() : () -> ()
        }, {
          "scf.if"(%120) ({
            "memref_ext.deslice_start"(%118, %71, %104, %105, %25, %12) <{operandSegmentSizes = array<i32: 1, 1, 2, 1, 1>}> : (memref<?x?xf32>, memref<8x8xf32>, i32, i32, memref<3xi32>, index) -> ()
            "scf.yield"() : () -> ()
          }, {
          }) : (i1) -> ()
          "scf.yield"() : () -> ()
        }) : (i1) -> ()
        "scf.yield"(%114) : (index) -> ()
      }, {
        "scf.yield"(%12) : (index) -> ()
      }) : (i1) -> index
      %99 = "arith.cmpi"(%98, %12) <{predicate = 1 : i64}> : (index, index) -> i1
      "scf.if"(%99) ({
        "memref.dma_wait"(%25, %12, %98) : (memref<3xi32>, index, index) -> ()
        "scf.yield"() : () -> ()
      }, {
      }) : (i1) -> ()
      "gcu.border"() {leave = "triton_gcu.store"} : () -> ()
      "memref.dealloc"(%71) : (memref<8x8xf32>) -> ()
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
