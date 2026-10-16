#!/usr/bin/env python3
"""Replay a frozen public SDK input on the CPU; never launch a device kernel."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import time


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_identity(path):
    path = Path(path).resolve(strict=True)
    with path.open("rb") as data:
        checksum = hashlib.file_digest(data, "sha256").hexdigest()
    return {"path": str(path), "sha256": checksum, "bytes": path.stat().st_size}


def observe_compiler_children(root_pid, finished, records):
    """Observe only this compiler subtree; never read process environments."""
    while not finished.is_set():
        pending = [root_pid]
        seen = set()
        while pending:
            pid = pending.pop()
            if pid in seen:
                continue
            seen.add(pid)
            proc = Path("/proc") / str(pid)
            try:
                pending.extend(int(value) for value in (
                    proc / "task" / str(pid) / "children").read_text().split())
                executable = os.readlink(proc / "exe")
                argv = [part.decode("utf-8", "replace") for part in
                        (proc / "cmdline").read_bytes().split(b"\0") if part]
            except (OSError, ValueError):
                continue
            records.setdefault((pid, executable, tuple(argv)),
                               {"pid": pid, "executable": executable, "argv": argv})
        finished.wait(0.005)


def attach_external_identity(receipt, processes, compiler, libdevice):
    tools = {}
    resources = {str(libdevice.resolve()): file_identity(libdevice)}
    for process in processes.values():
        executable = Path(process["executable"])
        if executable.is_file():
            tools[str(executable.resolve())] = file_identity(executable)
        for argument in process["argv"]:
            candidate = Path(argument.split("=", 1)[-1])
            if (candidate.is_absolute() and candidate.suffix in (".bc", ".a", ".so")
                    and candidate.is_file()):
                resources[str(candidate.resolve())] = file_identity(candidate)
    template_names = ("meta_op.aic.bc", "meta_op.aiv.bc", "meta_op.mix.aic.bc",
                      "meta_op.mix.aiv.bc", "host.bc")
    templates = {}
    for name in template_names:
        path = compiler.parent.parent / "lib" / name
        templates[name] = file_identity(path) if path.is_file() else {"path": str(path), "present": False}
    names = {Path(name).name for name in tools}
    receipt.update(observed_processes=list(processes.values()),
                   external_executables=list(tools.values()),
                   observed_argument_resources=list(resources.values()),
                   compiler_prefix_templates=templates,
                   external_observation={"hivmc": "hivmc" in names,
                                         "bisheng": "bisheng" in names,
                                         "scope": "sampled compiler descendants; no environment contents"},
                   sdk_environment_paths={key: os.environ[key] for key in (
                       "ASCEND_HOME_PATH", "ASCEND_OPP_PATH", "BISHENG_INSTALL_PATH")
                       if key in os.environ})


def main():
    data = Path(__file__).with_name("tests") / "data"
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--expect", choices=("original", "fixed"), default="original")
    parser.add_argument("--input", type=Path, default=data / "public_bm16_scalar.mlir")
    parser.add_argument("--input-sha256", default="6b910a15aa5e87da20bbfc7ae29515093d362a609eae1a8c39126514f6a76b3f")
    parser.add_argument("--reference", type=Path, default=data / "ordinary_reference.npubin")
    parser.add_argument("--libdevice", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    compiler = args.compiler.resolve(strict=True)
    if digest(args.input.read_bytes()) != args.input_sha256:
        raise RuntimeError("Public input SHA mismatch")
    args.output.mkdir()
    output = args.output / "kernel"
    command = [str(compiler), str(args.input.resolve()),
               "--target=Ascend910B4-1", "--enable-auto-multi-buffer=True",
               "--enable-auto-bind-sub-block=True",
               "--link-aicore-bitcode=" + str(args.libdevice.resolve()),
               "--enable-hfusion-compile=true", "--enable-hivm-compile=true",
               "--enable-triton-kernel-compile=true", "-o", str(output),
               "--mlir-disable-threading", "--mlir-print-ir-module-scope",
               "--mlir-print-ir-before=hivm-bind-sub-block",
               "--mlir-print-ir-after=hivm-bind-sub-block",
               "--mlir-print-ir-tree-dir=" + str(args.output / "ir")]
    receipt = {"argv": command, "compiler": str(compiler),
               "compiler_sha256": digest(compiler.read_bytes()),
               "input": str(args.input), "input_sha256": args.input_sha256,
               "reference": str(args.reference), "started": time.time(),
               "timeout_seconds": 180, "state": "running", "expect": args.expect}
    receipt_path = args.output / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    # This is a separate executable with a textual interface. Keep the installed
    # SDK hivmc/bisheng in PATH; never load this LLVM19 tool into LLVM22 Python.
    environment = dict(os.environ)
    with (args.output / "stdout.log").open("wb") as stdout, \
            (args.output / "stderr.log").open("wb") as stderr:
        process = subprocess.Popen(command, env=environment, stdout=stdout,
                                   stderr=stderr, start_new_session=True)
        receipt["pid"] = process.pid
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
        finished = threading.Event()
        processes = {}
        observer = threading.Thread(target=observe_compiler_children,
                                    args=(process.pid, finished, processes), daemon=True)
        observer.start()
        try:
            receipt["returncode"] = process.wait(timeout=180)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=20)
            receipt.update(state="timed_out", returncode=process.returncode,
                           ended=time.time())
            receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
            raise
        finally:
            finished.set()
            observer.join(timeout=5)
    attach_external_identity(receipt, processes, compiler, args.libdevice)
    receipt.update(ended=time.time(), state="compiler_finished")
    binary = args.output / "kernel.o"
    if not receipt["returncode"] and binary.is_file():
        actual, reference = binary.read_bytes(), args.reference.read_bytes()
        receipt.update(binary=str(binary), binary_bytes=len(actual),
                       binary_sha256=digest(actual), reference_bytes=len(reference),
                       reference_sha256=digest(reference), byteequal=actual == reference)
        if actual != reference:
            first = next((i for i, pair in enumerate(zip(actual, reference))
                          if pair[0] != pair[1]), min(len(actual), len(reference)))
            receipt["first_difference"] = {
                "offset": first, "actual_hex": actual[first:first + 16].hex(),
                "reference_hex": reference[first:first + 16].hex()}
        receipt["state"] = "matched" if actual == reference else "binary_mismatch"
    else:
        receipt["state"] = "failed"
    if args.expect == "fixed" and receipt["state"] in ("matched", "binary_mismatch"):
        from check_pass import verify_scalar_chain
        paths = list((args.output / "ir").rglob("0_hivm-bind-sub-block.mlir"))
        after_paths = list((args.output / "ir").rglob("1_hivm-bind-sub-block.mlir"))
        if len(paths) != 1 or len(after_paths) != 1:
            raise RuntimeError("Fixed public compile lacks actual Bind before/after IR")
        before_sha = digest(paths[0].read_bytes())
        if before_sha != "0b1f6b3241e15b95dfbcfa74b7d4dcc0166eca74c02a94928b89ea1b6dc66c2f":
            raise RuntimeError("Fixed public compile changed IR before the repaired pass")
        after = after_paths[0].read_text()
        aiv = after.split("func.func @state_probe_mix_aiv", 1)[1]
        if ("map_for_to_forall" in aiv or aiv.count("limit_sub_block_id0") != 2 or
                aiv.count("hivm.hir.store") != 2 or
                aiv.count("hivm.hir.sync_block_wait") != 1 or
                aiv.index("hivm.hir.sync_block_wait") > aiv.index("scf.if")):
            raise RuntimeError("Fixed public AIV must retain synchronization and elect both complete stores")
        verify_scalar_chain(aiv)
        receipt.update(state="fixed-compiled", before_bind_sha256=before_sha,
                       after_bind_sha256=digest(after_paths[0].read_bytes()),
                       verified_public_aiv={"untiled_whole_output": True,
                           "store_election_guards": 2, "closed_scalar_ssa": True,
                           "sync_wait_before_election": True},
                       validation_scope="CPU compiler evidence; device execution still required")
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    if receipt["state"] not in ("matched", "fixed-compiled"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
