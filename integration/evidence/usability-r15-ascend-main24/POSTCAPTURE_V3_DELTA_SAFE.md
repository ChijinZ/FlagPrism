# Independent CPU closeout v3: truthful mixed/standalone ownership

This is a postcapture evidence adapter only. The d992 execution manifest, f645 capture controller, original f6c27 CPU closeout, 141 old gates, mathematical sources, inputs, tolerances, automatic plan, captures, receipts and historical failures remain unchanged. Existing finite2 v2 full verdict and its 18 per-bank obligations remain immutable.

The v2 derivation had a mixed-specific assumption: selected terminal operation had to be tt.store and the writer had to have an explicit SUB0 election. An actual standalone profile selected the exact State RMW addi source operation instead; it has a single AIV module and no SUB instruction. The v3 adapter does not relabel that absence as an explicit guard.

Allowed proof variants:
- mixed_explicit_SUB0_guard: original scalar State pointer/ABI, load/add-one/UB/GM descriptor, explicit SUB==0 branch dominance, nonrepeating writer CFG, source-terminal marker CFG and every per-actor raw count==1 remain required. This variant keeps actual_compiled_single_writer_guard=true.
- standalone_aiv_one_instance: actual SDK AIV function must lack part_of_mix and declare mix_mode=aiv; actual metadata must be AIV task type 10/zero mix ratio; actual captured host grids and requested call count must match the source receipt. The actual cached native loader must bind the installed npu_utils.cpp source cache key and its machine registration must use AIVEC magic 0x41415246. Actual cached launcher disassembly proves exactly one rtKernelLaunch call, with gridX*gridY*gridZ passed as blockDim and no repeated native call. This is a machine-code/dataflow derivation tied to the actual host record, not a dynamic SDK blockDim packet: the query receipt list is empty and stays explicitly reported as empty. The original standalone AIVEC launch convention gives one vector instance per block; the exact 1D grid plus the already proved source-program coordinate mapping is bijective. Within that instance, the actual scalar State call must postdominate entry and not be cyclic. This variant explicitly sets actual_compiled_single_writer_guard=false and carries a separate complete single-instance execution proof.

Terminal markers are limited to actual selected State tt.store or scalar i32 arith.addi at the exact State-store AST location. An addi marker must immediately precede the exact LLVM SSA add-one from the loaded State value; a store marker must precede the exact UB store of that SSA value in the same block. Source and actual SSA/CFG checks prevent substituting an arbitrary counted site.

Standalone raw obligations specify every independent program × terminal-site pair and sum both admissible banks [1,2] to exactly one. Both cells must be present, including a zero-valued cell. No bank is selected by looking for nonzero data, and no zero cell is reclassified as unexecuted. The original full physical geometry gate is retained. New CPU closeout independently checks complete obligation geometry and re-proves the actual native/grid evidence before accepting the standalone kind.

Actual Docker CPU validation is in POSTCAPTURE_V3_NORMAL_OPTIMIZED_CPU_SAFE.json. Normal and -O both passed actual standalone and existing mixed profile positives. Each rejected six explicit negatives: both bank counts zero, duplicate visits across banks, missing a bank cell, missing a whole program/site, mixed task metadata falsely labelled standalone, and changed native blockDim multiplication. No product modules, compiler, or device work occurred. This is not a new profile run or whole-matrix verdict.

Review sources are all in postcapture-v3-safe-source/ and contain no private mathematical formulas, operator-case mapping or IR. Exact current SHA:
- derive_ownership_v3.py: bb89d0451dcfa9e5c5546760200f41988fc8612b59c6e09163b6f3a632b466ae
- standalone_execution_r15.py: 82ce616a0fc3b8f73546f171fd346585e26e0edccd756d9cb1a9b94c40ac8b86
- finalize_scope_cpu_v3.py: 969bdd9234d34f99b74dd32025aa42838f024949cd3b18eca661f185d65dfb30

The qualifier will use this CPU closeout version for complete main24/new8 evidence only after root's narrow source review. Capture continues under the unchanged original authorized controller. Prior CPU helper errors and drafts are retained separately; they are not device/product failures and do not trigger device replay.
