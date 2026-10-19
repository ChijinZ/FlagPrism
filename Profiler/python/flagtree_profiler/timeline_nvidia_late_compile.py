"""NVIDIA optimized-LLVM transform used by automatic timeline capture.

The matching parent compiler invokes this after O3 and scratch metadata
extraction. Each attempt retains original IR, native output, logs and an
identity receipt. Metadata is committed only after bounded native validation.
This module does not launch kernels or assert machine/time qualifications.
"""
import base64
import zlib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import uuid


class LateCompileError(RuntimeError):
    pass


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _integer(value, name, lower, upper):
    if type(value) is not int or not lower <= value <= upper:
        raise LateCompileError('Invalid ' + name)
    return value


def _automatic_pair_budget(actors, full):
    if full:
        target = min(8 * 1024 * 1024,
                     max(2 * 1024 * 1024, 2 * actors * (6 + 4 * 512) * 8))
        return (1 << (target.bit_length() - 1)) - 128
    return min(8 * 1024 * 1024 - 128, 2 * actors * (6 + 4 * 4096) * 8)


class LateLLVMTransform:
    """One capture's callable compiler hook with retained per-compile attempts."""

    def __init__(self,
                 tool,
                 artifact_root,
                 *,
                 max_sites=8,
                 capacity=None,
                 timeout=120):
        self.tool = Path(tool).resolve(strict=True)
        if not self.tool.is_file() or not os.access(self.tool, os.X_OK):
            raise LateCompileError('Late recorder is not an executable file')
        self.tool_sha256 = _sha(self.tool)
        self.root = Path(artifact_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_sites = _integer(max_sites, 'site budget', 1, 128)
        self.capacity = None if capacity is None else _integer(
            capacity, 'record capacity', 1, 4096)
        self.timeout = _integer(timeout, 'compile timeout', 1, 120)

    @property
    def cache_identity(self):
        return dict(transform_version=2,
                    tool_sha256=self.tool_sha256,
                    max_sites=self.max_sites,
                    capacity=self.capacity,
                    capacity_policy='bounded-actor-bytes-v4'
                    if self.capacity is None else 'explicit-record-count',
                    profile_argument_abi=1,
                    actors='native-async-matrix-footprint-else-first4',
                    compact_programs=True,
                    batch_records=True)

    def __call__(self, llvm_text, metadata):
        if not isinstance(llvm_text, str) or not llvm_text.strip():
            raise LateCompileError('Expected nonempty optimized LLVM text')
        if not isinstance(metadata, dict):
            raise LateCompileError('Expected mutable compiler metadata')
        if (metadata.get('profile_scratch_size', 0) != 0
                or 'flagprism_late_manifest' in metadata):
            raise LateCompileError(
                'Existing instrumentation cannot be overwritten')
        if _sha(self.tool) != self.tool_sha256:
            raise LateCompileError(
                'Recorder executable changed after capture binding')
        attempt = self.root / ('compile-' + uuid.uuid4().hex)
        attempt.mkdir(exist_ok=False)
        source, output, manifest = (attempt / n
                                    for n in ('ordinary.ll', 'instrumented.ll',
                                              'manifest.json'))
        source.write_text(llvm_text)
        argv = [
            str(self.tool),
            str(source), '--flagtree-profile-abi=1', '--batch-records',
            '--group-matrix', '--compact-programs',
            '--max-sites=' + str(self.max_sites), '--capacity=' +
            str(self.capacity if self.capacity is not None else 4096),
            '--output=' + str(output), '--manifest=' + str(manifest)
        ]
        if self.capacity is None:
            argv.append('--auto-capacity')
        receipt = dict(state='starting',
                       argv=argv,
                       cache_identity=self.cache_identity,
                       input_sha256=_sha(source))
        receipt_path = attempt / 'compile-receipt.json'

        def save():
            receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')

        save()
        started = time.monotonic_ns()
        try:
            with (attempt / 'stdout.log').open('xb') as out, (
                    attempt / 'stderr.log').open('xb') as err:
                child = subprocess.Popen(argv,
                                         stdout=out,
                                         stderr=err,
                                         start_new_session=True)
                try:
                    fields = Path('/proc/' + str(child.pid) +
                                  '/stat').read_text().rsplit(')',
                                                              1)[1].split()
                    receipt.update(state='running',
                                   pid=child.pid,
                                   startticks=int(fields[19]),
                                   pgid=int(fields[2]))
                    save()
                    code = child.wait(timeout=self.timeout)
                except BaseException:
                    # Own process and descendants only; includes detached children.
                    from ._deadline import _stop_worker
                    try:
                        if child.poll() is None:
                            _stop_worker(child)
                    finally:
                        # Retain the direct-child fallback when /proc cannot
                        # provide the identity needed for descendant discovery.
                        if child.poll() is None:
                            child.kill()
                        child.wait(timeout=10)
                    raise
                finally:
                    receipt.update(returncode=child.returncode,
                                   wall_ns=time.monotonic_ns() - started)
                    save()
            if code:
                raise LateCompileError('Native LLVM recorder failed (exit ' +
                                       str(code) + ')')
            if output.stat().st_size > 64 * 1024 * 1024 or manifest.stat(
            ).st_size > 8 * 1024 * 1024:
                raise LateCompileError(
                    'Native LLVM output exceeds artifact budget')
            transformed = output.read_text()
            if not transformed.strip():
                raise LateCompileError(
                    'Native LLVM recorder returned empty IR')
            plan = json.loads(manifest.read_text())
            if (type(plan) is not dict or plan.get('schema_version') != 1
                    or plan.get('profile_argument_abi') != 1
                    or plan.get('word_layout') != 'program/logical_word/actor'
                    or plan.get('compact_programs') is not True
                    or plan.get('batch_records') is not True
                    or plan.get('max_sites') != self.max_sites):
                raise LateCompileError(
                    'Native manifest does not match requested recording ABI')
            actors = _integer(plan.get('actors'), 'actual actor count', 1,
                              1024)
            dims = plan.get('block_dimensions')
            if not isinstance(dims, list) or len(dims) != 3:
                raise LateCompileError('Missing actual block dimensions')
            product = 1
            for value in dims:
                product *= _integer(value, 'actual block dimension', 1, 1024)
            if actors > product:
                raise LateCompileError(
                    'Observer count exceeds actual block dimensions')
            capacity = self.capacity
            if capacity is None:
                full = plan.get('requires_full_footprint')
                if type(full) is not bool or plan.get(
                        'capacity_policy') != 'bounded-actor-bytes-v4':
                    raise LateCompileError(
                        'Native automatic record policy differs')
                budget = _automatic_pair_budget(actors, full)
                if plan.get('automatic_pair_budget_bytes') != budget:
                    raise LateCompileError(
                        'Native automatic raw byte budget differs')
                words = budget // (2 * actors * 8)
                if words < 10:
                    raise LateCompileError(
                        'Automatic record budget lacks room for its header')
                capacity = min(4096, (words - 6) // 4)
            if plan.get('header_words') != 6 or plan.get(
                    'capacity_per_program') != capacity:
                raise LateCompileError('Native record capacity/header differs')
            stride = actors * (6 + 4 * capacity) * 8
            if plan.get('segment_words') != stride // 8:
                raise LateCompileError('Native physical layout differs')
            if 2 * stride > 8 * 1024 * 1024:
                raise LateCompileError('Compact allocation exceeds raw budget')
            sites = plan.get('sites')
            if not isinstance(sites, list) or not 1 <= len(sites) <= 4096:
                raise LateCompileError(
                    'Native manifest lacks bounded site inventory')
            ids = [
                _integer(site.get('site_id'), 'native site ID', 1, 4096)
                for site in sites if isinstance(site, dict)
            ]
            if len(ids) != len(sites) or len(set(ids)) != len(ids):
                raise LateCompileError(
                    'Native site IDs are missing or duplicated')
            plan['compiler_binding'] = dict(
                input_sha256=receipt['input_sha256'],
                output_sha256=_sha(output),
                tool_sha256=self.tool_sha256,
                transform_version=2)
            receipt.update(state='validated',
                           output_sha256=_sha(output),
                           manifest_sha256=_sha(manifest),
                           stride_bytes=stride)
            save()
            metadata.update(
                flagprism_late_ordinary_llvm_zlib_b64=base64.b64encode(
                    zlib.compress(llvm_text.encode())).decode("ascii"),
                profile_scratch_size=stride,
                profile_scratch_align=8,
                flagprism_late_manifest=plan)
            return transformed
        except BaseException as error:
            receipt.update(state='failed',
                           error_type=type(error).__name__,
                           error=str(error),
                           wall_ns=time.monotonic_ns() - started)
            save()
            raise
