# GCU two actual streams

The reusable hardware test passes six interleaved calls on two non-default torch.gcu.Stream objects, with two source specializations and distinct inputs. It validates exact CPU FP32 math, unchanged inputs/output guards, actual launch IDs, native provider/process/context/correlation tuples, source scopes/binaries and stream separation, plus six distinct dynamic captures (80 observations).

The SDK grid/task field remains unknown for raw gridId=0. It is not the identity oracle. Two initial test failures (wrong stream field spelling and an unsupported non-null task-ID assumption) are preserved in the external raw archive; no production module was changed to make them pass.

ROOT independently checks the complete archive SHA, 48 capture-file hashes, 34 bundle entries and the source/native/dynamic identity correspondence. Three absolute pytest current-directory symlinks are skipped when extracting the archive; all data files are checked. There is no concurrent-overlap or shared-clock claim.
