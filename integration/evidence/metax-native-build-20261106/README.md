# Isolated MetaX native build (2026-11-06)

Source code: merged detailed-profiler base through2a288d66 (officialMetaXPR18 ae3fc33 plus existing detailed features and compatibility interfaces). Staged at/root/chijin-metax-detailed-20261106/base/source inside chijin-flagprism-metax. Existing installed package, environment file and FlagTree source/build were not mutated.

The reproducible build-native.py replays25 native compile commands and2links from the existing FlagTree native targets with all source/object/output paths remapped. It uses4compiler jobs and the installed matching LLVM19/SDK/generated headers. Compiler bindings continue to come from the existing installed libtriton; no incompatible NVIDIA native object was copied.

First compile exposed missing official-parent APIs: optional vendor event properties, collector plan configuration, and a nonkernel-event overlay variable. These were integrated in2a288d66 with no-op defaults for other collectors. Attempt1 logs remain on server in output-attempt1. The complete second build passed, hashes and exact commands are attached.

Output PYTHONPATH=/root/chijin-metax-detailed-20261106/base/output/python. This contains current detailedPythonAPI and freshly compiled profiler/debugger native modules. CPU import probe confirms matchinglibtriton.proton, debugger availability and public detail/observation/capacity parameters. No device experiments were run by this build task. Timeline-agent purePython overlays can be applied after this base; initial hashes describe the two unchanged native libraries.
