#!/usr/bin/env python3
"""Build the pinned public compiler in an isolated container prefix.

Only the LLVM patchset shipped by the pinned SDK source is applied. The SDK
legality patch is deliberately a separate, later stage after baseline replay.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tarfile
import time

from prepare_build_compat import apply as apply_build_compat

PINS = {
    "AscendNPU-IR": "428ab8fdab46a879c7349caba4cde705bc8c9bb6",
    "llvm-project": "cd708029e0b2869e80abe31ddb175f7c35361f90",
}


def sha(path):
    with Path(path).open("rb") as data:
        return hashlib.file_digest(data, "sha256").hexdigest()


class Build:
    def __init__(self, args):
        self.args = args
        self.prefix = args.prefix.resolve()
        self.path = self.prefix / "build-receipt.json"
        if self.path.exists():
            self.receipt = json.loads(self.path.read_text())
            if args.resume_llvm_patch is None or self.receipt["state"] != "failed":
                raise RuntimeError("Existing receipt requires an explicit failed-patch resume")
            expected = f"llvm-patch-{args.resume_llvm_patch:03d}"
            last = self.receipt["commands"][-1]
            if last["label"] != expected or not last.get("returncode"):
                raise RuntimeError("Resume must identify the last failed patch check")
            self.receipt.setdefault("resumes", []).append({
                "pid": os.getpid(), "time": time.time(),
                "recipe_sha256": sha(__file__), "from_patch": args.resume_llvm_patch,
                "previous_error": self.receipt.get("error"),
                "reason": "Use GNU patch -p1 --merge as pinned official apply_patches.sh; preserve original patch bytes"})
            self.receipt.pop("error", None)
        else:
            if args.resume_llvm_patch is not None:
                raise RuntimeError("Cannot resume without an existing receipt")
            self.receipt = {"pid": os.getpid(), "pins": PINS,
                            "recipe_sha256": sha(__file__), "commands": [],
                            "started": time.time(), "state": "preparing"}
        self.save(pid=os.getpid())

    def save(self, **fields):
        self.receipt.update(fields)
        self.path.write_text(json.dumps(self.receipt, indent=2) + "\n")

    def run(self, label, argv, cwd=None, timeout=14400):
        record = {"label": label, "argv": list(map(str, argv)),
                  "cwd": str(cwd or self.prefix), "started": time.time(),
                  "timeout_seconds": timeout}
        self.receipt["commands"].append(record)
        log = self.prefix / f"build-{len(self.receipt['commands']):03d}-{label}.log"
        record["log"] = str(log)
        with log.open("wb") as output:
            process = subprocess.Popen(record["argv"], cwd=record["cwd"],
                                       stdout=output, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            record["pid"] = process.pid
            self.save(state=label)
            print(json.dumps(record), flush=True)
            try:
                record["returncode"] = process.wait(timeout=timeout)
            except BaseException:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=20)
                record.update(returncode=process.returncode, ended=time.time())
                self.save(state="failed")
                raise
        record["ended"] = time.time()
        self.save()
        if record["returncode"]:
            raise RuntimeError(f"{label} failed; retained log {log}")

    def extract(self, name, archive, expected):
        actual = sha(archive)
        if actual != expected:
            raise RuntimeError(f"{name}: transfer SHA mismatch {actual} != {expected}")
        destination = self.prefix / "source" / name
        destination.mkdir()
        with tarfile.open(archive) as bundle:
            members = bundle.getmembers()
            roots = {member.name.split("/", 1)[0] for member in members}
            if len(roots) != 1:
                raise RuntimeError("Unexpected archive root")
            for member in members:
                parts = Path(member.name).parts
                if ".." in parts or Path(member.name).is_absolute():
                    raise RuntimeError("Invalid source archive path")
                if len(parts) == 1:
                    continue
                member.name = str(Path(*parts[1:]))
                bundle.extract(member, destination, filter="data")
        self.receipt.setdefault("sources", {})[name] = {
            "revision": PINS[name], "archive": str(archive),
            "archive_sha256": actual, "archive_root": roots.pop(),
            "source": str(destination)}
        self.save(state="source-extracted")
        return destination

    def build(self):
        if self.args.resume_llvm_patch is None:
            source = self.extract("AscendNPU-IR", self.args.sdk_archive,
                                  self.args.sdk_sha256)
            llvm = self.extract("llvm-project", self.args.llvm_archive,
                                self.args.llvm_sha256)
        else:
            source = self.prefix / "source/AscendNPU-IR"
            llvm = self.prefix / "source/llvm-project"
            for name, archive, expected in (
                ("AscendNPU-IR", self.args.sdk_archive, self.args.sdk_sha256),
                ("llvm-project", self.args.llvm_archive, self.args.llvm_sha256)):
                if sha(archive) != expected or self.receipt["sources"][name]["archive_sha256"] != expected:
                    raise RuntimeError("Resume source archive mismatch")
        patches = sorted((source / "build-tools/patches/llvm-project").glob("*.patch"))
        if not patches:
            raise RuntimeError("Pinned SDK LLVM patchset missing")
        patch_manifest = [{"file": str(p.relative_to(source)),
                           "sha256": sha(p)} for p in patches]
        if self.args.resume_llvm_patch is not None and self.receipt["llvm_patches"] != patch_manifest:
            raise RuntimeError("Resume LLVM patchset changed")
        self.receipt["llvm_patches"] = patch_manifest
        self.save()
        for number, patch in enumerate(patches):
            if number < (self.args.resume_llvm_patch or 0):
                continue
            # The pinned official script uses GNU patch, including for patches
            # missing a terminal LF that git apply rejects as corrupt.
            self.run(f"llvm-patch-{number:03d}",
                     ["patch", "--dry-run", "--batch", "-p1", "--merge", "--input", patch],
                     cwd=llvm, timeout=60)
            self.run(f"llvm-apply-{number:03d}",
                     ["patch", "--batch", "-p1", "--merge", "--input", patch],
                     cwd=llvm, timeout=60)
        if self.args.build_compat_patch:
            self.save(**apply_build_compat(source, self.args.build_compat_patch, self.run))
        build = self.prefix / "build-unmodified"
        install = self.prefix / "install-unmodified"
        self.run("configure-unmodified", [
            "cmake", "-S", llvm / "llvm", "-B", build, "-G", "Ninja",
            "-DCMAKE_C_COMPILER=/usr/bin/gcc", "-DCMAKE_CXX_COMPILER=/usr/bin/g++",
            "-DCMAKE_BUILD_TYPE=Release", f"-DCMAKE_INSTALL_PREFIX={install}",
            "-DLLVM_ENABLE_PROJECTS=mlir", "-DLLVM_EXTERNAL_PROJECTS=bishengir",
            f"-DLLVM_EXTERNAL_BISHENGIR_SOURCE_DIR={source}",
            "-DLLVM_TARGETS_TO_BUILD=AArch64", "-DLLVM_ENABLE_ASSERTIONS=OFF",
            "-DMLIR_ENABLE_BINDINGS_PYTHON=OFF", "-DBISHENGIR_PUBLISH=ON",
            "-DLLVM_BSPUB_DAVINCI_BISHENGIR=ON", "-DBSPUB_DAVINCI_BISHENGIR=ON",
            "-DBISHENGIR_BUILD_TEMPLATE=OFF", "-DBISHENGIR_BUILD_STANDALONE_IR_ONLY=OFF",
        ], timeout=600)
        self.run("compile-unmodified", ["cmake", "--build", build, "--target",
                 "bishengir-compile", "bishengir-opt", "-j", str(self.args.jobs)])
        self.run("install-unmodified", ["cmake", "--install", build,
                 "--component", "bishengir-publish-products"], timeout=300)
        compiler = install / "bin/bishengir-compile"
        self.run("version-unmodified", [compiler, "--version"], timeout=30)
        self.save(state=("legality-unmodified-tool-ready" if self.args.build_compat_patch
                         else "unmodified-tool-ready"), compiler=str(compiler),
                  compiler_sha256=sha(compiler), ended=time.time())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("prefix", type=Path)
    parser.add_argument("--sdk-archive", type=Path, required=True)
    parser.add_argument("--sdk-sha256", required=True)
    parser.add_argument("--llvm-archive", type=Path, required=True)
    parser.add_argument("--llvm-sha256", required=True)
    parser.add_argument("--jobs", type=int, default=12)
    parser.add_argument("--resume-llvm-patch", type=int)
    parser.add_argument("--build-compat-patch", type=Path)
    args = parser.parse_args()
    if not 1 <= args.jobs <= 12:
        parser.error("jobs must be between 1 and 12")
    build = Build(args)
    try:
        build.build()
    except BaseException as error:
        build.save(state="failed", error=repr(error), ended=time.time())
        raise


if __name__ == "__main__":
    main()
