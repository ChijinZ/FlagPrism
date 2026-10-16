#!/usr/bin/env python3
"""Resume the exact-source link failure with an explicit-template-only patch.

The result is legality-unmodified, not byte-unmodified upstream SDK source.
The original failed full-build receipt remains immutable.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

from rebuild_fixed import dependencies, objects, sha

UTILS = "bishengir/lib/Dialect/Tensor/Transforms/PropagateReshape/Utils.cpp"
UTILS_SHA = "a6185b7a3184c76e5e315837f112887dfa99bee814717a23efaf483623341c85"
PARTITION = "bishengir/lib/Dialect/HIVM/Transforms/TileAndBindSubBlock.cpp"
PARTITION_SHA = "c33d6effd6a128a16126a4ee1f1c511754d1b045157133a664baa63607ad4d11"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("prefix", type=Path)
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=12)
    args = parser.parse_args()
    if not 1 <= args.jobs <= 12:
        parser.error("jobs must be between 1 and 12")
    prefix = args.prefix.resolve()
    source = prefix / "source/AscendNPU-IR"
    build = prefix / "build-unmodified"
    path = prefix / "build-compat-receipt.json"
    if path.exists():
        raise RuntimeError("Existing compatibility receipt must be inspected, not overwritten")
    original_path = prefix / "build-receipt.json"
    original = json.loads(original_path.read_text())
    if (original["state"] != "failed" or
            original["commands"][-1]["label"] != "compile-unmodified" or
            not original["commands"][-1].get("returncode")):
        raise RuntimeError("Expected the recorded exact-source full-build link failure")
    original_failure = Path(original["commands"][-1]["log"]).read_text()
    if ("undefined reference" not in original_failure or
            "collapseAndReplace<mlir::tensor::CollapseShapeOp>" not in original_failure):
        raise RuntimeError("Recorded build failure is not the known missing template instantiation")
    if sha(source / UTILS) != UTILS_SHA or sha(source / PARTITION) != PARTITION_SHA:
        raise RuntimeError("SDK source is not the frozen original, legality-unmodified state")
    target = list(build.rglob("PropagateReshape/Utils.cpp.o"))
    if len(target) != 1:
        raise RuntimeError("Cannot identify the actually compiled Utils.cpp translation unit")
    target = target[0]
    freeze_paths = [UTILS, PARTITION,
                   "bishengir/include/bishengir/Dialect/Tensor/Transforms/PropagateReshape/Utils.h",
                   "bishengir/lib/Dialect/Tensor/Transforms/PropagateReshape/PropagateCollapseDown.cpp"]
    receipt = {"pid": os.getpid(), "started": time.time(), "state": "freezing",
               "baseline_kind": "exact428 + explicit-template buildcompat, legality-unmodified",
               "pins": original["pins"], "recipe_sha256": sha(__file__),
               "original_failed_receipt_sha256": sha(original_path),
               "original_failed_receipt": str(original_path),
               "patch": str(args.patch), "patch_sha256": sha(args.patch),
               "sources_before": {name: sha(source / name) for name in freeze_paths},
               "cmake_cache_before_sha256": sha(build / "CMakeCache.txt"),
               "commands": []}

    def save(**fields):
        receipt.update(fields)
        path.write_text(json.dumps(receipt, indent=2) + "\n")

    def run(label, argv, cwd=prefix, timeout=3600):
        log = prefix / ("compat-" + label + ".log")
        record = {"label": label, "argv": list(map(str, argv)), "cwd": str(cwd),
                  "started": time.time(), "timeout_seconds": timeout, "log": str(log)}
        receipt["commands"].append(record)
        with log.open("wb") as output:
            process = subprocess.Popen(record["argv"], cwd=cwd, stdout=output,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            record["pid"] = process.pid
            save(state=label)
            try:
                record["returncode"] = process.wait(timeout=timeout)
            except BaseException:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=20)
                record.update(returncode=process.returncode, ended=time.time())
                save(state="failed")
                raise
        record["ended"] = time.time()
        save()
        if record["returncode"]:
            raise RuntimeError(f"{label} failed; retained {log}")

    try:
        save()
        for name in freeze_paths:
            frozen = prefix / "compat-source-before" / name
            frozen.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, frozen)
        failure_log = Path(original["commands"][-1]["log"])
        excerpt = [line for line in failure_log.read_text().splitlines()
                   if any(text in line for text in ("undefined reference", "FAILED:", "collect2:"))]
        (prefix / "compat-original-link-failure.txt").write_text("\n".join(excerpt) + "\n")
        before = objects(build)
        (prefix / "compat-objects-before.json").write_text(json.dumps(before, indent=2) + "\n")
        # Freeze the real unresolved/defined symbols, header, definition and
        # cross-translation-unit caller before applying any source change.
        run("symbols-before", ["nm", "-C", build / "lib/libBiShengIRTensorTransforms.a"], timeout=60)
        symbol_excerpt = [line for line in (prefix / "compat-symbols-before.log").read_text().splitlines()
                          if "collapseAndReplace" in line]
        (prefix / "compat-template-symbols-before.txt").write_text("\n".join(symbol_excerpt) + "\n")
        run("dependencies-before", ["ninja", "-C", build, "-t", "deps", target.relative_to(build)], timeout=60)
        deps_before = dependencies(prefix / "compat-dependencies-before.log", build)
        (prefix / "compat-deps-before.json").write_text(json.dumps(deps_before, indent=2) + "\n")
        run("patch-check", ["git", "apply", "--check", args.patch.resolve()], cwd=source, timeout=60)
        run("patch-apply", ["git", "apply", args.patch.resolve()], cwd=source, timeout=60)
        save(utils_compat_sha256=sha(source / UTILS))
        run("compile", ["cmake", "--build", build, "--target", "bishengir-compile",
                        "bishengir-opt", "-j", args.jobs])
        after = objects(build)
        (prefix / "compat-objects-after.json").write_text(json.dumps(after, indent=2) + "\n")
        changed = {name: {"before": before.get(name), "after": value}
                   for name, value in after.items() if before.get(name) != value}
        if set(changed) != {str(target.relative_to(build))}:
            raise RuntimeError(f"Compatibility rebuild changed unexpected objects: {list(changed)}")
        run("symbols-after", ["nm", "-C", build / "lib/libBiShengIRTensorTransforms.a"], timeout=60)
        run("dependencies-after", ["ninja", "-C", build, "-t", "deps", target.relative_to(build)], timeout=60)
        deps_after = dependencies(prefix / "compat-dependencies-after.log", build)
        (prefix / "compat-deps-after.json").write_text(json.dumps(deps_after, indent=2) + "\n")
        save(changed_objects=changed, reused_object_count=len(after) - len(changed),
             changed_dependencies={name: {"before": deps_before.get(name), "after": value}
                                   for name, value in deps_after.items() if deps_before.get(name) != value},
             cmake_cache_after_sha256=sha(build / "CMakeCache.txt"))
        run("install", ["cmake", "--install", build, "--component", "bishengir-publish-products"], timeout=300)
        compiler = prefix / "install-unmodified/bin/bishengir-compile"
        run("version", [compiler, "--version"], timeout=30)
        if sha(source / PARTITION) != PARTITION_SHA or sha(original_path) != receipt["original_failed_receipt_sha256"]:
            raise RuntimeError("Legality source or original failed receipt changed")
        save(state="legality-unmodified-tool-ready", compiler=str(compiler),
             compiler_sha256=sha(compiler), ended=time.time())
    except BaseException as error:
        save(state="failed", error=repr(error), ended=time.time())
        raise


if __name__ == "__main__":
    main()
