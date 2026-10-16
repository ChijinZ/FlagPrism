#!/usr/bin/env python3
"""Apply the SDK source repair only after a matching unmodified public replay."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import time

from accept_public_baseline import validate as validate_producer_baseline
from validate_delivery import validate as validate_delivery

SOURCE = "bishengir/lib/Dialect/HIVM/Transforms/TileAndBindSubBlock.cpp"
SOURCE_SHA256 = "c33d6effd6a128a16126a4ee1f1c511754d1b045157133a664baa63607ad4d11"
PUBLIC_INPUT_SHA256 = "6b910a15aa5e87da20bbfc7ae29515093d362a609eae1a8c39126514f6a76b3f"
PUBLIC_BINARY_SHA256 = "05b54efee3ed790bc6c76b40110e92b2f7684d2761605bea6f1dfa31c1fe6b6e"


def sha(path):
    with Path(path).open("rb") as data:
        return hashlib.file_digest(data, "sha256").hexdigest()


def objects(build):
    return {str(path.relative_to(build)): sha(path)
            for path in sorted(build.rglob("*.o"))}


def dependencies(log, build):
    result = {}
    for line in log.read_text().splitlines():
        if not line.startswith("    "):
            continue
        path = Path(line.strip())
        path = path if path.is_absolute() else build / path
        if path.is_file():
            result[str(path.resolve())] = sha(path)
    if not result:
        raise RuntimeError("Actual translation-unit dependency list was empty")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("prefix", type=Path)
    parser.add_argument("--baseline-replay", type=Path, required=True)
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument("--baseline-equivalence", type=Path)
    parser.add_argument("--execution-seal", type=Path)
    parser.add_argument("--jobs", type=int, default=12)
    args = parser.parse_args()
    if not 1 <= args.jobs <= 12:
        parser.error("jobs must be between 1 and 12")
    prefix = args.prefix.resolve()
    path = prefix / "fixed-build-receipt.json"
    if path.exists():
        raise RuntimeError("Existing fixed-build receipt requires inspection, not a blind restart")
    baseline = json.loads(args.baseline_replay.read_text())
    build_receipt_path = (prefix / "build-compat-receipt.json")
    if not build_receipt_path.exists():
        build_receipt_path = prefix / "build-receipt.json"
    build_receipt = json.loads(build_receipt_path.read_text())
    template_receipt = json.loads((prefix / "templates-receipt.json").read_text())
    if template_receipt.get("state") != "templates-ready":
        raise RuntimeError("The complete public template resource installation is required")
    old_compiler = prefix / "install-unmodified/bin/bishengir-compile"
    # Re-read actual files, not just the previous receipt's booleans.
    if (baseline["input_sha256"] != PUBLIC_INPUT_SHA256 or
            sha(baseline["input"]) != PUBLIC_INPUT_SHA256 or
            sha(baseline["reference"]) != PUBLIC_BINARY_SHA256 or
            baseline["reference_sha256"] != PUBLIC_BINARY_SHA256 or
            sha(baseline["binary"]) != baseline["binary_sha256"] or
            baseline["compiler_sha256"] != sha(old_compiler) or
            Path(baseline["compiler"]).resolve() != old_compiler.resolve()):
        raise RuntimeError("Frozen public input/reference/output/tool identity changed")
    equivalent = None
    if args.baseline_equivalence:
        derived = json.loads(args.baseline_equivalence.read_text())
        equivalent = validate_producer_baseline(args.baseline_replay)
        canonical = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"))
        if any(canonical(derived.get(key)) != canonical(value) for key, value in equivalent.items()):
            raise RuntimeError("Producer-only receipt differs from a fresh strict ELF/IR audit")
    elif (baseline.get("state") != "matched" or not baseline.get("byteequal") or
          baseline["binary_sha256"] != PUBLIC_BINARY_SHA256):
        raise RuntimeError("A byteequal replay or separately audited producer-only equivalence is required")
    if build_receipt["state"] not in ("unmodified-tool-ready", "legality-unmodified-tool-ready"):
        raise RuntimeError("Actual source build is not a legality-unmodified baseline")
    delivery = validate_delivery(prefix, baseline)
    execution_seal = None
    if equivalent:
        if not args.execution_seal:
            raise RuntimeError("Producer-only baseline requires an explicitly reviewed execution seal")
        execution_seal = json.loads(args.execution_seal.read_text())
        observed_seal = {"actual_baseline_sha256": sha(baseline["binary"]),
                         "input_sha256": sha(baseline["input"]),
                         "reference_sha256": sha(baseline["reference"]),
                         "compiler_sha256": sha(old_compiler),
                         "derived_receipt_sha256": sha(args.baseline_equivalence),
                         "build_receipt_sha256": delivery["build_receipt_sha256"],
                         "templates_receipt_sha256": delivery["templates_receipt_sha256"],
                         "source_sha256": SOURCE_SHA256}
        if canonical(execution_seal) != canonical(observed_seal):
            raise RuntimeError("Actual build differs from the explicitly reviewed execution seal")
    source = prefix / "source/AscendNPU-IR"
    if sha(source / SOURCE) != SOURCE_SHA256:
        raise RuntimeError("SDK translation unit is not the frozen unmodified exact revision")
    build = prefix / "build-unmodified"
    target_objects = list(build.rglob("TileAndBindSubBlock.cpp.o"))
    if len(target_objects) != 1:
        raise RuntimeError("Cannot identify the actually compiled partition translation unit")
    target_object = target_objects[0]
    receipt = {"pid": os.getpid(), "started": time.time(), "state": "preparing",
               "recipe_sha256": sha(__file__), "patch": str(args.patch),
               "patch_sha256": sha(args.patch), "source_before_sha256": SOURCE_SHA256,
               "unmodified_compiler_sha256": sha(old_compiler),
               "baseline_replay": str(args.baseline_replay),
               "baseline_replay_sha256": sha(args.baseline_replay),
               "baseline_equivalence": equivalent,
               "delivery": delivery,
               "execution_seal": execution_seal,
               "execution_seal_sha256": sha(args.execution_seal) if args.execution_seal else None,
               "baseline_equivalence_receipt_sha256": (sha(args.baseline_equivalence)
                   if args.baseline_equivalence else None),
               "cmake_cache_sha256": sha(build / "CMakeCache.txt"),
               "target_object": str(target_object), "commands": []}

    def save(**fields):
        receipt.update(fields)
        path.write_text(json.dumps(receipt, indent=2) + "\n")

    def run(label, command, cwd=prefix, timeout=3600):
        log = prefix / ("fixed-" + label + ".log")
        record = {"label": label, "argv": list(map(str, command)),
                  "cwd": str(cwd), "started": time.time(), "log": str(log),
                  "timeout_seconds": timeout}
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
        before = objects(build)
        (prefix / "objects-unmodified.json").write_text(json.dumps(before, indent=2) + "\n")
        run("commands-before", ["ninja", "-C", build, "-t", "commands",
                                 target_object.relative_to(build)], timeout=60)
        run("dependencies-before", ["ninja", "-C", build, "-t", "deps",
                                     target_object.relative_to(build)], timeout=60)
        deps_before = dependencies(prefix / "fixed-dependencies-before.log", build)
        (prefix / "dependencies-unmodified.json").write_text(json.dumps(deps_before, indent=2) + "\n")
        run("patch-check", ["git", "apply", "--check", args.patch.resolve()], cwd=source, timeout=60)
        run("patch-apply", ["git", "apply", args.patch.resolve()], cwd=source, timeout=60)
        save(source_fixed_sha256=sha(source / SOURCE))
        run("compile", ["cmake", "--build", build, "--target", "bishengir-compile",
                        "bishengir-opt", "-j", args.jobs])
        after = objects(build)
        (prefix / "objects-fixed.json").write_text(json.dumps(after, indent=2) + "\n")
        changed = {name: {"before": before.get(name), "after": value}
                   for name, value in after.items() if before.get(name) != value}
        if str(target_object.relative_to(build)) not in changed:
            raise RuntimeError("Changed partition source did not produce a changed object")
        save(changed_objects=changed, reused_object_count=sum(
            name in before and before[name] == value for name, value in after.items()))
        run("dependencies-after", ["ninja", "-C", build, "-t", "deps",
                                    target_object.relative_to(build)], timeout=60)
        run("commands-after", ["ninja", "-C", build, "-t", "commands",
                                target_object.relative_to(build)], timeout=60)
        deps_after = dependencies(prefix / "fixed-dependencies-after.log", build)
        (prefix / "dependencies-fixed.json").write_text(json.dumps(deps_after, indent=2) + "\n")
        save(changed_dependencies={name: {"before": deps_before.get(name), "after": value}
                                   for name, value in deps_after.items()
                                   if deps_before.get(name) != value},
             reused_dependency_count=sum(name in deps_before and deps_before[name] == value
                                         for name, value in deps_after.items()),
             compilation_commands_before_sha256=sha(prefix / "fixed-commands-before.log"),
             compilation_commands_after_sha256=sha(prefix / "fixed-commands-after.log"))
        install = prefix / "install-fixed"
        run("install", ["cmake", "--install", build, "--prefix", install,
                        "--component", "bishengir-publish-products"], timeout=300)
        (install / "lib").mkdir(exist_ok=True)
        fixed_resources = {}
        for name, resource in template_receipt["public_template_resources"].items():
            generated = build / "lib" / name
            if sha(generated) != resource["sha256"]:
                raise RuntimeError("Public template resource changed since baseline")
            destination = install / "lib" / name
            if destination.exists():
                raise RuntimeError("Refusing to replace an existing fixed template resource")
            shutil.copyfile(generated, destination)
            fixed_resources[name] = {"path": str(destination), "sha256": sha(destination)}
        compiler = install / "bin/bishengir-compile"
        run("version", [compiler, "--version"], timeout=30)
        if sha(old_compiler) != receipt["unmodified_compiler_sha256"]:
            raise RuntimeError("Unmodified installed compiler was overwritten")
        if sha(compiler) == sha(old_compiler):
            raise RuntimeError("Fixed and unmodified linked tools are identical")
        save(state="fixed-tool-ready", compiler=str(compiler),
             compiler_sha256=sha(compiler), public_template_resources=fixed_resources,
             baseline_kind=build_receipt.get("baseline_kind", "exact428 unmodified"),
             ended=time.time())
    except BaseException as error:
        save(state="failed", error=repr(error), ended=time.time())
        raise


if __name__ == "__main__":
    main()
