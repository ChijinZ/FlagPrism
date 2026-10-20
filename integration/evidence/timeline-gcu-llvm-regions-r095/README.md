# GCU finite LLVM selected-region rules (R095)

Source freeze: `4ae3561735a186a5ad2352ac901a168a93517709`.
All execution used existing `flagprism-enflame-dev` Docker; recorder a2937f0d was reused after checking unchanged native inputs. This delta does not qualify native scheduling, exclusive source cost, or the whole timeline goal.

The previous freeze fails the new undef/poison, reset-backedge and continuation-reentry regressions. The fixed rules pass 20 standalone native-index tests and 39 affected binding tests in both normal and optimized Python. A normal wheel installation checks all 503 installed members. Two immutable old captures and two new public math captures produce 11/13 and 10/13 checked local regions; unknown source remains unverified. The recurrence has one checked runtime loop.

The public runner initially failed its final extra check because it treated a relative capture reference as an absolute filesystem path. The math and captures had already succeeded. The CPU-only public-post job used the existing load_capture API to inspect those exact outputs without application replay; its terminal and result are retained here. Other failed launcher attempts and complete original receipts remain in the workspace record; no SDK/private IR is included.

Legacy current96 coverage, Ascend finite source/loop rules and final whole-goal reviews remain open.
