# GCU public diagnostic replay and retained intervention

The reusable hardware entry is
`Profiler/test/test_enflame_softmax_diagnostic_hardware.py` (requires the actual
GCU runtime and `FLAGPRISM_TEST_ENFLAME=1`). Run inside the existing server
Docker with the validated source/native import setup. `summary.json` records
the exact request, all source-version boundaries and original raw references.
Two tiny captures passed; this was not a new performance experiment.

`root-independent-audit.json` records independent offline verification of
110 bundle-manifest entries, the two current raw record buffers, all270
historical native samples, byte hashes and mathematical-function AST identity.
It does not rerun the numerical oracle or establish local timing accuracy.
The original raw package remains in workspace
`artifacts/method-run/enflame/round2/diagnostic-raw-evidence.tar.gz`, SHA256
`0249bf9e672e442ae8dbafe278dd869bcd8ad8677ad6d6e7caa6bfd671309744`.

To replay the offline audit, safely extract regular files beneath
`EVIDENCE_DIR/root-extracted` (skip the two pytest absolute `current` symlinks),
place the original package and `retained-controls-audit.json` in `EVIDENCE_DIR`,
and run:

```bash
python root-independent-audit.py --evidence-dir EVIDENCE_DIR --source-root FLAGPRISM_SOURCE
```

Current public output supplies a structural clue, not a microsecond breakdown:
four vector work-items use two shared scratch buffers and two barriers; one
removes the exchange. The historical source-observer-disabled/native-collector-on
three30-call batches give1.615–1.621× improvement. The two-item control retains
both barriers and approaches one-item performance, excluding barrier presence
as a complete explanation. This is a retrospective reproduction of a diagnosis,
not a claim of first discovery or final-source performance reruns.
