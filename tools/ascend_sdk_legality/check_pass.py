#!/usr/bin/env python3
"""Run actual CPU compiler passes and check partition/fallback structure."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time


def digest(path):
    with Path(path).open("rb") as data:
        return hashlib.file_digest(data, "sha256").hexdigest()


def verify_scalar_chain(output):
    old = re.search('(%[\\w]+) = memref.load ', output)
    if not old:
        raise RuntimeError('scalar load disappeared')
    add = re.search('(%[\\w]+) = arith.addi ' + re.escape(old[1]) + ',', output)
    if not add:
        raise RuntimeError('load-to-add SSA chain changed')
    insert = re.search('(%[\\w]+) = tensor.insert ' + re.escape(add[1]) + ' into', output)
    if not insert:
        raise RuntimeError('scalar-to-tensor SSA chain changed')
    if not re.search('hivm.hir.store ins\\(' + re.escape(insert[1]) + ' :', output):
        raise RuntimeError('terminal scalar store no longer uses the original read/modify result')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--opt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expect", choices=("unmodified", "fixed"), required=True)
    args = parser.parse_args()
    args.output.mkdir()
    root = Path(__file__).with_name("tests")
    receipts = []
    cases = ["tileable_store", "store_legality", "unaligned_store", "multi_function"]
    if args.expect == "fixed":
        cases.append("conditional_store")
    for name in cases:
        source = root / (name + ".mlir")
        command = [str(args.opt.resolve()), str(source), "--hivm-bind-sub-block",
                   "--verify-each"]
        started = time.time()
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        (args.output / (name + ".stdout.mlir")).write_text(result.stdout)
        (args.output / (name + ".stderr.txt")).write_text(result.stderr)
        receipt = {"case": name, "argv": command, "started": started,
                   "ended": time.time(), "returncode": result.returncode,
                   "input_sha256": digest(source), "tool_sha256": digest(args.opt),
                   "stdout_sha256": hashlib.sha256(result.stdout.encode()).hexdigest()}
        receipts.append(receipt)
        (args.output / "receipt.json").write_text(json.dumps(receipts, indent=2) + "\n")
        assert result.returncode == 0, f"{name}: real compiler pass failed; inspect stderr"
        output = result.stdout
        tiled = "map_for_to_forall" in output
        guards = output.count("limit_sub_block_id0")
        if name == "multi_function":
            assert output.count("func.func @") == 2, "module functions lost or duplicated"
            assert guards == 1, "first function must take its original unique-writer fallback"
            expected_loops = 0 if args.expect == "unmodified" else 1
            assert output.count("map_for_to_forall") == expected_loops, \
                "fallback must not stop processing subsequent AIV functions"
        elif name == "tileable_store":
            assert tiled, "ordinary tileable tensor store lost two-subblock execution"
            assert guards == 0, "positive control was globally forced to subblock zero"
        else:
            if name in ("store_legality", "conditional_store"):
                verify_scalar_chain(output)
            assert output.count("hivm.hir.store") == 2, "source stores lost or duplicated"
            if args.expect == "unmodified" and name != "unaligned_store":
                assert tiled and guards == 0, "baseline fixture did not expose mixed-store bug"
            else:
                assert not tiled, "unpartitioned external store survived accepted subblock tiling"
                assert guards == 2, "fallback must elect both output and scalar stores"
                assert output.count("hivm.hir.get_sub_block_idx") == 2
                assert output.count("arith.cmpi eq,") >= 2
                if name == "conditional_store":
                    assert "scf.if %arg3" in output, "source mask/control condition was lost"
        receipt["verified"] = True
        (args.output / "receipt.json").write_text(json.dumps(receipts, indent=2) + "\n")
    print(json.dumps({"verified": len(receipts), "expect": args.expect,
                      "receipt": str(args.output / "receipt.json")}))


if __name__ == "__main__":
    main()
