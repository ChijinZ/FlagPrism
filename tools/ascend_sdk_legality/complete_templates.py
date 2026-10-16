#!/usr/bin/env python3
"""Build and install the pinned public template resources through SDK CMake."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

from rebuild_fixed import objects, sha

NAMES = ("meta_op.aic.bc", "meta_op.aiv.bc", "meta_op.mix.aic.bc",
         "meta_op.mix.aiv.bc", "host.bc")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("prefix", type=Path)
    parser.add_argument("--bisheng-bin", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=12)
    args = parser.parse_args()
    if not 1 <= args.jobs <= 12:
        parser.error("jobs must be between 1 and 12")
    prefix = args.prefix.resolve()
    source = prefix / "source/AscendNPU-IR"
    build = prefix / "build-unmodified"
    install = prefix / "install-unmodified"
    receipt_path = prefix / "templates-receipt.json"
    if receipt_path.exists():
        raise RuntimeError("Existing template receipt requires inspection, not a blind restart")
    for name in NAMES:
        if (install / "lib" / name).exists():
            raise RuntimeError("Refusing to replace an existing installed template")
    tools = {name: args.bisheng_bin / name for name in ("ccec", "llvm-link")}
    if not all(path.is_file() and os.access(path, os.X_OK) for path in tools.values()):
        raise RuntimeError("Official template build requires executable ccec and llvm-link")
    receipt = {"pid": os.getpid(), "started": time.time(), "state": "preparing",
               "recipe_sha256": sha(__file__), "commands": [],
               "sdk_tools": {name: {"path": str(path.resolve()), "sha256": sha(path)}
                             for name, path in tools.items()},
               "compiler_before_sha256": sha(install / "bin/bishengir-compile"),
               "cmake_cache_before_sha256": sha(build / "CMakeCache.txt"),
               "template_sources": {str(path.relative_to(source)): sha(path)
                   for path in sorted((source / "bishengir/lib/Template").rglob("*"))
                   if path.is_file()},
               "install_contract": "exact build-tools/build.sh publishing copies build/lib/*.bc to package/lib"}

    def save(**fields):
        receipt.update(fields)
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")

    def run(label, command, timeout=1800):
        log = prefix / ("templates-" + label + ".log")
        record = {"label": label, "argv": list(map(str, command)),
                  "started": time.time(), "timeout_seconds": timeout, "log": str(log)}
        receipt["commands"].append(record)
        with log.open("wb") as output:
            process = subprocess.Popen(record["argv"], cwd=prefix, stdout=output,
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
        shutil.copyfile(build / "CMakeCache.txt", prefix / "templates-CMakeCache-before.txt")
        before = objects(build)
        (prefix / "templates-objects-before.json").write_text(json.dumps(before, indent=2) + "\n")
        # These are the upstream template build options, not user-kernel
        # codegen compensation flags. Configure itself generates the bitcode.
        run("configure", ["cmake", "-S", prefix / "source/llvm-project/llvm",
                           "-B", build, "-DBISHENGIR_BUILD_TEMPLATE=ON",
                           "-DBISHENG_COMPILER_PATH=" + str(args.bisheng_bin.resolve())])
        run("tools", ["cmake", "--build", build, "--target", "bishengir-compile",
                      "bishengir-opt", "-j", args.jobs])
        run("install-tools", ["cmake", "--install", build,
                              "--component", "bishengir-publish-products"], timeout=300)
        (install / "lib").mkdir(exist_ok=True)
        resources = {}
        for name in NAMES:
            generated = build / "lib" / name
            if not generated.is_file() or not generated.stat().st_size:
                raise RuntimeError(f"Official template build did not generate {name}")
            shutil.copyfile(generated, install / "lib" / name)
            resources[name] = {"generated": str(generated),
                               "installed": str(install / "lib" / name),
                               "sha256": sha(generated), "bytes": generated.stat().st_size}
        after = objects(build)
        (prefix / "templates-objects-after.json").write_text(json.dumps(after, indent=2) + "\n")
        save(state="templates-ready", public_template_resources=resources,
             compiler_after_sha256=sha(install / "bin/bishengir-compile"),
             changed_objects={name: {"before": before.get(name), "after": value}
                              for name, value in after.items() if before.get(name) != value},
             reused_object_count=sum(before.get(name) == value for name, value in after.items()),
             cmake_cache_after_sha256=sha(build / "CMakeCache.txt"), ended=time.time())
    except BaseException as error:
        save(state="failed", error=repr(error), ended=time.time())
        raise


if __name__ == "__main__":
    main()
