# Independent visual-readability review

Reviewer: closure_visual_review. Reviewed 2026-10-13. This review did not read other reviewers' reports and did not access remote machines. Inspection covered the rendered `paper/main.pdf` (9 pages, Ghostscript png16m render), all nine current result/mapping PNGs, the Study source, `plot_operator_closure.py`, the protocol comparison CSV, Ascend summary and selected actual actor records. It is a presentation audit, not a complete numerical-accuracy audit.

## Verdict

The figures now depict actual operator results and compiler mappings, including the requested static pipeline and dynamically measured internal brackets. The visual sequence can support the restricted story: backend execution/mapping differences require backend-aware observation identity, scope and clock protocol. **The current paper PDF needs a layout correction before delivery**, and the Ascend figure needs the common output request visually marked. The figures do not establish unperturbed engine busy time, a synchronized AIC/AIV timeline, exact internal timing accuracy, or an attribution-error rate; the text generally states these limits correctly.

## Critical changes

1. **Keep Study figures with Study, before Design and references.** The current PDF puts Study prose on pages 2–4 but Figure 3 (fused mapping) on page 5, Figure 4 on page 6, Figure 5 on page 7, Figure 6 on page 8 and controls on page 9. Design, evaluation and references intervene. This breaks the desired evidence chain even though figure numbering is correct. Use deliberate grouped placement and a float boundary after Study; then render the PDF again. A clean build alone cannot verify this requirement.

2. **Show the fixed body/output request in the Ascend dynamic figure.** The pipeline currently has a grey body and colored wait/transfer/compute/store segments but no visible output-region outline or start marker. The reader cannot see that the common output interval begins before the fused AIV wait but begins at final normalization in softmax. Add an output-bracket outline or labeled endpoint ticks using the existing `output` records; retain the separate actor origins. This connects the dynamic case directly to the common request and the scope consequence.

3. **Preserve the distinction between measured bracket and full pipeline.** The Ascend AIC row records only its body, displayed grey; there is no measured breakdown of AIC input/compute/workspace/signal in that figure. Make this visible in the row label or caption (for example, “AIC: body only”). It is appropriate to show that row, but do not describe it as a full measured producer pipeline. The static mapping diagram supplies its dependency structure. Separate actor origins are correctly stated in title, axis and caption and must remain.

## Other actionable improvements

- The supplementary CUDA timeline subtracts the earliest start among the selected eight records, but its axis says “origin = first shown body start.” Program (0,0) does not start at zero in either rendered panel. Change the label to “earliest shown body start,” or change the calculation. This is a factual label discrepancy, although that figure is not currently included in the main Study.
- The protocol plot is easy to read and clearly shows GCU body collapse plus the adapter's 1.239 softmax perturbation. It only shows point ratios of pooled medians. Add descriptive per-launch dispersion if space permits, or explicitly keep it a point-summary plot; do not label absent uncertainty as a confidence interval. A logarithmic point plot would avoid the ambiguous nonzero visual base of log bars, but the printed ratios already make the conclusion legible.
- In the completion figure the original workspace observation is zero and its grey bar disappears. Add an explicit “0 / unresolved” label or marker. Both distributions have 15 launch summaries; optional min–max or individual dots would make variability visible. The existing caption correctly says fences change execution, so the figure must not be interpreted as error correction against a ground truth.
- The breadth plot is readable at full two-column width and has honestly identified min–max ranges. It is dominated by absolute latency differences between stack implementations, particularly untuned GCU GEMM. Keep its modest “scope/performance motivates inspection” claim. It cannot alone show profiling failure or compiler-independent hardware efficiency. Small/large/tail shapes are recoverable from its caption.
- The softmax mapping figure mixes compiled structure with recording protocol in its boxes. Ascend “PIPE_ALL” belongs to the selected observation endpoints rather than every original source-level lowering. Qualify the caption/label accordingly, so the successful generic single-AIV mapping is not conflated with the late completion-fenced probe.
- Across figures, backend colors are not completely consistent: breadth uses Ascend blue, GCU red, V100 green, whereas the protocol plot uses blue for a GCU adapter mechanism. This is acceptable when the legend is explicit, but avoid implying blue always means Ascend.

## Positive checks and what each figure establishes

- Breadth: six operators, three shapes, two configs, actual sample ranges; supports the range of behaviors only.
- Fused mapping: concrete memory/compute/synchronization paths, selected emitted dependencies, explicit no-time/no-overlap statement; this is a useful pipeline diagram rather than a decorative architecture picture.
- Softmax mapping: single-AIV positive contrast to fused actor decomposition; actual PTX/GCU lowering labels are checked by the plotting script.
- Protocol result: two real cases under body/output request, original GCU counter versus stateless adapter, matched per-provider references; the printed ratios agree with plot inputs and do not hide adapter perturbation.
- Ascend dynamic brackets: actual sample index 7 for both real operators; endpoints and sample actor data agree with the generated figure. There is no cross-actor subtraction. One softmax instance has a much larger store suffix than its peers and is correctly retained instead of silently removed.
- Readiness control: actual 15 per-launch actor medians with fixed auxiliary-work count; producer pre-signal bracket and consumer wait move together. Separate panels avoid pretending to have a synchronized global execution trace.
- Completion control: issue/gate versus completion-fenced observations, correct raw-tick units and median aggregation; supports endpoint semantics rather than internal accuracy.
- Native scale check (supplementary): conversion/scale relation to independent collection endpoints; not an internal precision certificate. Its labels appropriately do not rule out a common physical oscillator.

The remaining independent-reference precision requirement needs a separate evidence assessment. No change of visual framing can turn whole-kernel containment, pooled medians or matched-counter replay into internal-region ground truth.

## Recheck after corrections

Re-rendered the updated 12-page `paper/main.pdf` with Ghostscript png16m and inspected updated Study pages 3–10 and the full-size Ascend PNG. The three critical corrections above are **resolved**:

- All seven Study figures now occur before Design and references. Breadth is page 4, the two static mappings page 5, protocol and dynamic brackets page 7, controls page 9, and requirements precede Design on page 10. The evidence chain remains in subsection order.
- Violet `Requested output bracket` endpoint lines are visibly drawn from the actual output records. Fused output includes the readiness wait, transfer, compute and store suffix; softmax output covers normalize/store. This now directly visualizes the fixed request.
- Both the AIC row and caption explicitly say body only. Separate actor origins remain declared, so the figure does not present a synchronized cross-actor execution timeline.

The supplementary CUDA timeline axis now correctly says earliest shown body start. This source-label discrepancy is also resolved.

**Revised verdict:** the main result figures are readable and suitable for review of the restricted Study claims; no remaining critical visual blocker was identified. There are presentation refinements for a submission layout: FloatBarrier plus flush-bottom creates very large vertical gaps between paragraphs/items on pages 6, 8 and 10; use ragged-bottom or refine placement. The Study now spans pages 2–10 because each subsection's text and double-column floats are separated; it will need compact placement after content selection. Point-summary/zero-marker and softmax-endpoint-label suggestions above remain useful but do not reverse the main conclusions. Exact internal timing precision remains an evidence requirement and is not certified by this visual review.
