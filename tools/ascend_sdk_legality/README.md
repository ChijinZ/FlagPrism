# Isolated SDK tiling-legality build

This recipe builds public AscendNPU-IR
`428ab8fdab46a879c7349caba4cde705bc8c9bb6`, its LLVM19 submodule
`cd708029e0b2869e80abe31ddb175f7c35361f90`, and all 65 LLVM patches
shipped by that SDK revision. The FlagTree LLVM22 dialect build does not build
this standalone SDK compiler. Tools communicate through the existing CANN
`hivmc` executable; do not load LLVM19 libraries into the LLVM22 Python process.

Run installation, builds and tests inside the approved Ascend Docker. The
reference environment has CANN9.0.0, GCC11.4, CMake3.31.10, Ninja1.13 and
Python3.11. Use at most 12 build jobs and provide sufficient disk space for LLVM
objects. Keep the system CANN installation, driver, daemon and SDK bitcode
unchanged. Public source archives may be downloaded elsewhere and transferred;
all execution below belongs in the Docker container.

From a clean checkout, choose absolute paths. `LIBDEVICE` must name the
`libdevice.10.bc` shipped by the matching installed FlagTree Ascend backend;
it is an external runtime dependency, not a file included in this repository.
Set the existing CANN compiler tools in PATH using your normal SDK setup.
The recipe never changes SDK binaries or installs to their directories.

```sh
RECIPE=/absolute/checkout/tools/ascend_sdk_legality
PATCHES=/absolute/checkout/integration/patches/ascend
PREFIX=/tmp/my-isolated-sdk-build
CANN_ROOT=/usr/local/Ascend/cann-9.0.0
BISHENG_BIN="$CANN_ROOT/tools/bisheng_compiler/bin"
LIBDEVICE=/absolute/installed/triton/backends/ascend/lib/libdevice.10.bc
export PATH="$BISHENG_BIN:$CANN_ROOT/tools/bishengir/bin:$PATH"
python3 "$RECIPE/bootstrap_sources.py" "$PREFIX"
```

Bootstrap requires a nonexistent or empty prefix, creates it, downloads both
pinned official archives, and records commands, PIDs, deadlines and SHA256.
Retries are bounded. Existing nonempty prefixes are rejected to preserve old
receipts. Inspect failures before any transport handoff; preserve partial
archives and use new filenames for transferred complete archives. For the
archives used in the recorded build, the full build command is:

```sh
python3 "$RECIPE/build_unmodified.py" "$PREFIX" \
  --sdk-archive "$PREFIX/downloads/AscendNPU-IR.tar.gz" \
  --sdk-sha256 ad8e88cadb6330c54b64cf7af3b223128ae453c2671a1fcea51c01575228cdc2 \
  --llvm-archive "$PREFIX/downloads/llvm-project.tar.gz" \
  --llvm-sha256 baa49713c849c63ca7fd51c4200e439eca01988e87ea904d7abaaf1ef78a95b8 \
  --jobs 12 \
  --build-compat-patch "$PATCHES/sdk-build-explicit-collapse-instantiation.patch"
```

Check each downloaded archive against its `*-source.json` receipt. An official
archive encoding with a different hash requires review and recording its actual
hash, not replacing a failed archive silently. The build extracts source and
uses official GNU `patch -p1 --merge` semantics. One LLVM patch lacks a final
newline: GNU patch accepts it with a warning, while `git apply` rejects it.
Preserve patch bytes and warnings. Only a recorded failed patch check can be
resumed using `--resume-llvm-patch INDEX`; earlier applied patches are not
repeated or skipped.

The explicit `--build-compat-patch` applies the separately pinned compatibility
patch before the first compilation, avoiding an expected full-build failure on
a fresh installation. It checks original Utils source, patch and result SHA256
and records compatibility in the build receipt. It does not apply the legality
patch. The historical pristine build was retained and, with GCC11, reached both
tool links and failed:
the five-argument `collapseAndReplace<CollapseShapeOp>` template is declared
and called across translation units but lacks an explicit instantiation. The
separate compatibility patch instantiates that existing function without
changing its algorithm. This is distinct from the legality correction. Only
when resuming that exact historical failure, use the first command below; a
fresh build with `--build-compat-patch` skips it. Both routes then run template
completion:

```sh
# Historical failed-build resume only; skip for a fresh compatibility-enabled build.
python3 "$RECIPE/resume_template_compat.py" "$PREFIX" \
  --patch "$PATCHES/sdk-build-explicit-collapse-instantiation.patch" --jobs 12
python3 "$RECIPE/complete_templates.py" "$PREFIX" \
  --bisheng-bin "$BISHENG_BIN" --jobs 12
```

The compatibility recipe freezes original source, caller/header, symbols, link
failure, object hashes and dependency hashes; only the actual Utils translation
unit and linked tools change. Call this baseline **exact428 plus explicit
template build compatibility, legality unmodified**, rather than pristine
upstream. It installs under `PREFIX/install-unmodified`. Template completion
uses the exact public CMake `BISHENGIR_BUILD_TEMPLATE=ON` contract, compiles
51 public CPP sources using existing CANN `ccec`/`llvm-link`, and installs the
five generated public template BC files beside the isolated tools. It neither
copies SDK template BC into this repository nor changes system resources.
All failures and object reuse receipts remain available.

The repository includes our public probe, frozen actual compiler MLIR input
SHA `6b910a15aa5e87da20bbfc7ae29515093d362a609eae1a8c39126514f6a76b3f`,
and its original ordinary NPUBIN SHA
`05b54efee3ed790bc6c76b40110e92b2f7684d2761605bea6f1dfa31c1fe6b6e`
in `tests/data/manifest.json`. These are our generated user-kernel artifacts,
not SDK libraries. Replay compiles on the CPU and never launches the kernel:

```sh
python3 "$RECIPE/replay_public.py" \
  --compiler "$PREFIX/install-unmodified/bin/bishengir-compile" \
  --libdevice "$LIBDEVICE" --output "$PREFIX/public-replay-baseline"
```

The same codegen flags and target as the original ordinary compile are fixed
in the script. Only MLIR printing options are added; their original SDK replay
was separately byteequal. The receipt records input/reference/tool identities,
actual output presence, bytes, first difference, Bind IR, sampled descendant
`hivmc`/`bisheng` identities and resource hashes. A driver exit0 without a final
NPUBIN fails. SDK executable/library/BC content is not copied into evidence.
Descendant observation is sampled and its coverage is stated explicitly.

The first resource-complete isolated baseline generated a 4576-byte NPUBIN
whose `.text`, symbols, argument metadata, stack record and Bind IR match the
original. It is **not bitidentical**: its nonallocated `.comment` includes the
local template compiler's dated producer string. The comparator verifies all
ELF headers, program headers, section contents/layout and every differing byte
without modifying either binary:

```sh
python3 "$RECIPE/compare_public_elf.py" \
  --actual "$PREFIX/public-replay-baseline/kernel.o" \
  --output "$PREFIX/public-replay-baseline/elf-comparison.json"
```

A mismatch remains a failed byteequal replay. A strictly reviewed producer-only
comparison can support a separate, explicitly recorded baseline equivalence
classification; it must not be relabeled bitidentical or used to relax device
correctness criteria. After reviewing the strict classification, derive a separate
receipt without changing the original failed replay:

```sh
python3 "$RECIPE/accept_public_baseline.py" \
  --replay "$PREFIX/public-replay-baseline/receipt.json" \
  --output "$PREFIX/public-replay-baseline/equivalence.json"
```

This gate re-reads input/reference/output/tool bytes and both pinned Bind IR files.
`rebuild_fixed.py` repeats the strict audit and also checks actual source archives,
compatibility source, generated/installed template manifests and their public
CPP sources, and observed external tool/resource identities. Rejection uses
explicit exceptions, including under Python `-O`. Do not strip producer strings, change codegen flags to
force a match, or accept differences in loadable content, ABI, relocations or
other section data.

For the producer-only route, explicitly seal the material you inspected. A
seal from another build is rejected: tool, baseline and receipt hashes are
specific to this installation. After reviewing the comparison and manifests,
create the separate seal with this CPU-only command:

```sh
python3 - "$PREFIX" <<'PYSEAL'
import hashlib, json, pathlib, sys
p = pathlib.Path(sys.argv[1])
h = lambda f: hashlib.sha256(pathlib.Path(f).read_bytes()).hexdigest()
r = json.loads((p / "public-replay-baseline/receipt.json").read_text())
b = p / "build-compat-receipt.json"
if not b.exists():
    b = p / "build-receipt.json"
seal = {"actual_baseline_sha256": h(r["binary"]),
        "input_sha256": h(r["input"]), "reference_sha256": h(r["reference"]),
        "compiler_sha256": h(r["compiler"]),
        "derived_receipt_sha256": h(p / "public-replay-baseline/equivalence.json"),
        "build_receipt_sha256": h(b),
        "templates_receipt_sha256": h(p / "templates-receipt.json"),
        "source_sha256": h(p / "source/AscendNPU-IR/bishengir/lib/Dialect/HIVM/Transforms/TileAndBindSubBlock.cpp")}
with (p / "reviewed-execution-seal.json").open("x") as output:
    json.dump(seal, output, indent=2)
PYSEAL
```

After the matching baseline (or the separately reviewed exact producer-only
equivalence) gate, run actual pass checks, apply the legality patch, rebuild
its translation unit and both tools, and check the corrected pass:

```sh
python3 "$RECIPE/check_pass.py" \
  --opt "$PREFIX/install-unmodified/bin/bishengir-opt" \
  --expect unmodified --output "$PREFIX/pass-unmodified"
python3 "$RECIPE/rebuild_fixed.py" "$PREFIX" \
  --baseline-replay "$PREFIX/public-replay-baseline/receipt.json" \
  --baseline-equivalence "$PREFIX/public-replay-baseline/equivalence.json" \
  --execution-seal "$PREFIX/reviewed-execution-seal.json" \
  --patch "$PATCHES/sdk-scalar-tiling-legality.patch" --jobs 12
python3 "$RECIPE/check_pass.py" \
  --opt "$PREFIX/install-fixed/bin/bishengir-opt" \
  --expect fixed --output "$PREFIX/pass-fixed"
```

For a bitidentical replay, omit `--baseline-equivalence` and `--execution-seal`; the byteequal gate
still re-reads actual input, reference, output and tool identities.

The SDK repair makes any failed StoreOp partition reject the whole AIV tiling
attempt, using its existing store-election fallback. A successful fallback
continues to later functions; failure still signals pass failure and returns.
The regressions retain tileable parallel execution, test mixed scalar stores
and an existing odd-size tensor fallback, preserve the scalar read/modify SSA chain and
conditional control, and check processing of multiple functions. This does
not establish safety for arbitrary unknown effects or distributed SSA
broadcasts: the verified public AIV scope has closed scalar consumption and
StoreOp external writes, while synchronization remains outside store guards.

Exercise the clean preparation and gate regressions without a device:

```sh
python3 "$RECIPE/tests/test_prepare_compat.py"
python3 -O "$RECIPE/tests/test_prepare_compat.py"
python3 "$RECIPE/tests/test_baseline_gate.py" \
  --replay "$PREFIX/public-replay-baseline/receipt.json"
python3 "$RECIPE/replay_public.py" --expect fixed \
  --compiler "$PREFIX/install-fixed/bin/bishengir-compile" \
  --libdevice "$LIBDEVICE" --output "$PREFIX/public-replay-fixed"
```

The fixed driver replay must produce its final NPUBIN and actual fallback IR,
with unchanged pre-pass IR, both complete store guards, the closed scalar SSA
chain, and synchronization before election. It records all five templates at
the **fixed install** path and actual downstream compiler/resource identities.
The changed output is not compared as byteequal to the old buggy binary.

Fixed installation uses `PREFIX/install-fixed`; the original binary is
preserved. Receipts record changed/reused objects, actual dependency hashes,
compile commands, patch and both tool SHA256 values. Describe it as an
incremental SDK rebuild. Do not use the old buggy binary as the normal
execution baseline for profiling cost comparisons.

Install the FlagTree parent patch providing the
[compiler identity contract](../../integration/patches/ascend/compiler_identity.md)
into the active wheel before selecting the new executable:

```sh
export TRITON_ASCEND_COMPILER="$PREFIX/install-fixed/bin/bishengir-compile"
```

The selector validates the absolute executable path and uses resolved path
and binary SHA256 for ordinary and profiled compilation, including JIT memory
and disk caches. Source presence alone does not prove wheel installation. Use
an atomic rename for same-path tool upgrades and preserve old caches for
upgrade verification. Both ordinary and profile use the same selected tool;
never substitute it only for profiling.

No NPU run is part of this build recipe. Separately authorized device
validation of the installed fixed compiler has since passed the
[original failing combinations](../../integration/evidence/usability-r15-independent-finite2/),
the [full original independent cohort](../../integration/evidence/usability-r15-ascend-main24/)
and [two new independent mathematical kernels](../../integration/evidence/usability-r15-ascend-new8/).
The historical ec75 plus stock SDK result remains 42/44 with two State failures;
its [original report](../../integration/evidence/usability-v3-ec75a9f/qualification-final/REPORT.md)
is preserved rather than relabelled as a first-pass success.
