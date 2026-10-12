# Review resolution

Three reviewers independently inspected source, raw samples, saved IR and figures.
The original reviews remain unchanged; this records revisions after their feedback.

- Evidence: 1296 artifact hashes and nested medians independently matched. CUDA
  early outliers had been hidden by median-only plotting. The revised figure
  retains min–max relative to the reference median on a logarithmic ratio axis.
- Story: fused mapping and nested recurrence are independent evidence chains.
  Study now explicitly separates them; neither is presented as a measured fused
  busy/wait timeline. Requirements remain distinct from unimplemented methods.
- Visual: endpoint figure now spans two columns; fonts enlarged; zero-work
  values labeled; breadth markers, exact shapes and requested settings defined.
- Native detail: black marks defined as medians; SDK percentage scopes stated.
  Per-SIP data is preserved in the JSON, while panels show invocation aggregates.
  No causal bottleneck claim or profiler-guided ~60× improvement is inferred.
- Binary controls: GCU and V100 GEMM stage1/2 binaries are identical across all
  three shapes. This is now explicit; a parameter label is not a compiled change.

Verdict retained: credible motivating Study of backend contracts (mapping,
measurement protocols, native detail). This is not yet an evaluation of a novel
instrumentation method, its accuracy, unperturbed busy/wait ground truth, or
operational deployment. SDK TimelineDetail failed on the available mixed kernel;
failed late-HIVM roundtrips never launched on hardware. Both remain documented.

Visual follow-up: shortened long vertical axis labels to avoid title overlap; captions now define log/symlog axes, medians, min–max bars and the fused+bias label. Native SDK metric definitions are exported alongside evidence.
