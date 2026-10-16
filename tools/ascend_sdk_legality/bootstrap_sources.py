#!/usr/bin/env python3
"""Fetch pinned public SDK compiler sources into a fresh isolated prefix.

Run in the approved build container. This does not build or change CANN.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

SOURCES = {
    "AscendNPU-IR": ("Ascend/AscendNPU-IR", "428ab8fdab46a879c7349caba4cde705bc8c9bb6"),
    "llvm-project": ("llvm/llvm-project", "cd708029e0b2869e80abe31ddb175f7c35361f90"),
}


def event(prefix, **fields):
    record = {"time": time.time(), **fields}
    with (prefix / "events.jsonl").open("a") as out:
        out.write(json.dumps(record, sort_keys=True) + "\n")
    print(json.dumps(record, sort_keys=True), flush=True)


def fetch(prefix, name, repository, revision):
    archive = prefix / "downloads" / (name + ".tar.gz")
    url = f"https://api.github.com/repos/{repository}/tarball/{revision}"
    command = ["curl", "--fail", "--location", "--connect-timeout", "15",
               "--max-time", "600", "--retry", "1", "--retry-delay", "5",
               "--retry-max-time", "1210", "--output", str(archive), url]
    event(prefix, state="downloading", name=name, revision=revision,
          argv=command, controller_pid=os.getpid())
    with (prefix / (name + "-download.log")).open("wb") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        event(prefix, state="download_pid", name=name, pid=process.pid)
        try:
            returncode = process.wait(timeout=1230)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=15)
            event(prefix, state="download_timeout", name=name)
            raise
    if returncode:
        event(prefix, state="download_failed", name=name, returncode=returncode)
        raise RuntimeError(f"{name}: download failed ({returncode}); inspect log")
    digest = hashlib.file_digest(archive.open("rb"), "sha256").hexdigest()
    receipt = {"repository": repository, "revision": revision, "url": url,
               "archive_sha256": digest, "archive_bytes": archive.stat().st_size,
               "archive": str(archive)}
    (prefix / (name + "-source.json")).write_text(json.dumps(receipt, indent=2) + "\n")
    event(prefix, state="archive_ready", name=name, **receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("prefix", type=Path)
    args = parser.parse_args()
    prefix = args.prefix.resolve()
    if prefix.exists() and any(prefix.iterdir()):
        raise FileExistsError("Source prefix must be new or empty; preserve existing receipts")
    prefix.mkdir(parents=True, exist_ok=True)
    for directory in ("downloads", "source"):
        (prefix / directory).mkdir()
    event(prefix, state="controller_started", pid=os.getpid(),
          cpu_count=os.cpu_count(), argv=list(__import__("sys").argv))
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(fetch, prefix, name, *spec)
                   for name, spec in SOURCES.items()]
        results = [future.result() for future in futures]
    (prefix / "sources.json").write_text(json.dumps(results, indent=2) + "\n")
    event(prefix, state="archives_ready")


if __name__ == "__main__":
    main()
