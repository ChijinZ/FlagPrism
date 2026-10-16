"""Public Ascend ownership diagnostic. Exactly one kernel invocation per process.

State is observed, never asserted to be an execution-count oracle. Run only in
the approved remote Docker environment after the device lease is released.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import traceback

os.environ['TORCH_DEVICE_BACKEND_AUTOLOAD'] = '0'
import torch
import torch_npu  # noqa: F401
import triton
import triton.language as tl
from flagtree import profiler


@triton.jit
def state_probe(a, b, bias, out, state, M: tl.constexpr, N: tl.constexpr,
                K: tl.constexpr, BM: tl.constexpr, BN: tl.constexpr,
                BK: tl.constexpr, STATE_KIND: tl.constexpr):
    p = tl.program_id(0)
    rows = p * BM + tl.arange(0, BM)
    cols = tl.arange(0, BN)
    inner = tl.arange(0, BK)
    av = tl.load(a + rows[:, None] * K + inner[None, :],
                 (rows[:, None] < M) & (inner[None, :] < K), 0)
    bv = tl.load(b + inner[:, None] * N + cols[None, :],
                 (inner[:, None] < K) & (cols[None, :] < N), 0)
    cv = tl.load(bias + cols, cols < N, 0)
    # Deliberately no row reduction: dot -> simple 2D elementwise -> store.
    value = tl.maximum(tl.dot(av, bv) + cv[None, :], 0.) + 0.25
    indices = rows[:, None] * N + cols[None, :]
    mask = (rows[:, None] < M) & (cols[None, :] < N)
    tl.store(out + indices, value, mask)
    if STATE_KIND == 0:
        prior = tl.load(state + p)
        tl.store(state + p, prior + 1)
    elif STATE_KIND == 1:
        prior = tl.load(state + indices, mask, 0)
        tl.store(state + indices, prior + 1, mask)
    else:
        tl.atomic_add(state + p, 1)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inventory(name, storage, view):
    return dict(name=name, storage_ptr=storage.data_ptr(),
                storage_bytes=storage.numel() * storage.element_size(),
                argument_ptr=view.data_ptr(),
                argument_bytes=view.numel() * view.element_size(),
                shape=list(view.shape), dtype=str(view.dtype))


def retain_compiled(compiled, destination):
    """Keep available in-memory compiler products without invoking a compiler."""
    destination.mkdir()
    entries = []
    for name, value in getattr(compiled, 'asm', {}).items():
        if not isinstance(value, (str, bytes, bytearray)):
            continue
        data = value.encode() if isinstance(value, str) else bytes(value)
        # Keys are compiler format labels, not arbitrary filesystem paths.
        safe = ''.join(c if c.isalnum() or c in '._-' else '_' for c in str(name))
        filename = safe + ('.txt' if isinstance(value, str) else '.bin')
        (destination / filename).write_bytes(data)
        entries.append(dict(format=str(name), file=filename, bytes=len(data),
                            sha256=sha(data)))
    metadata = getattr(compiled, 'metadata', None)
    if hasattr(metadata, '_asdict'):
        metadata = metadata._asdict()
    elif hasattr(metadata, '__dict__'):
        metadata = vars(metadata)
    # Metadata may contain non-JSON SDK objects; repr preserves their presence
    # without executing or pretending they establish pointer identity.
    (destination / 'metadata.txt').write_text(repr(metadata) + '\n')
    write_json(destination / 'index.json', entries)
    return entries


def retain_public_capture(capture, destination):
    """Retain only explicit actor LLVM and allowlisted generated objects."""
    source = capture / 'ai' / 'binaries.json'
    if not source.is_file():
        return dict(status='unavailable', reason='no exported binaries.json')
    destination.mkdir()
    entries = []

    def save(value, location, root, kind):
        if not isinstance(value, dict):
            entries.append(dict(location=location, status='bytes_unavailable',
                                excluded_reason='no_explicit_producer_record'))
            return
        entry = dict(location=location, producer_sha256=value.get('sha256'),
                     producer_path=value.get('path'), status='bytes_unavailable')
        entries.append(entry)
        candidate = value.get('retained_path') or value.get('path')
        if not isinstance(candidate, str) or root is None:
            entry['excluded_reason'] = 'missing_valid_declared_output_root_or_path'
            return
        path = Path(candidate)
        suffixes = {'.ll'} if kind == 'llvm' else {'.o', '.ll', '.npubin'}
        if (not path.is_absolute() or '..' in path.parts
                or not path.is_relative_to(root) or path.suffix not in suffixes):
            entry['excluded_reason'] = 'outside_declared_output_root_or_suffix_allowlist'
            return
        # Reject symlinked ancestors, including symlinked compiler output root.
        if any(part.is_symlink() for part in [path, *path.parents]):
            entry['excluded_reason'] = 'symlink_path_rejected'
            return
        if path.resolve().is_relative_to(root.resolve()) is False:
            entry['excluded_reason'] = 'resolved_path_escapes_output_root'
            return
        if kind == 'llvm' and value.get('encoding') == 'base64' and isinstance(value.get('data'), str):
            data = base64.b64decode(value['data'], validate=True)
        elif kind == 'llvm' and isinstance(value.get('llir'), str):
            data = value['llir'].encode()
        elif path.is_file():
            data = path.read_bytes()
        else:
            entry['excluded_reason'] = 'producer_bytes_no_longer_available'
            return
        digest = sha(data)
        expected = value.get('sha256')
        if not expected or digest != expected:
            entry['excluded_reason'] = 'missing_or_mismatched_producer_sha256'
            return
        if kind == 'llvm':
            text = data.decode('utf-8')
            if 'define ' not in text or ('; ModuleID' not in text and 'target triple' not in text):
                entry['excluded_reason'] = 'not_recognized_as_actor_llvm_text'
                return
        (destination / digest).write_bytes(data)
        entry.update(status='retained', sha256=digest, bytes=len(data),
                     representation=kind, retained_source_path=str(path))

    binaries = json.loads(source.read_text())
    if not isinstance(binaries, list):
        raise ValueError('expected explicit binaries list')
    def receipts_only(value):
        if isinstance(value, dict):
            return {key: ('omitted_from_receipt_copy' if key in {'data', 'llir'}
                          else receipts_only(child)) for key, child in value.items()}
        if isinstance(value, list):
            return [receipts_only(child) for child in value]
        return value
    write_json(destination / 'binaries-receipts.json', receipts_only(binaries))
    for binary_index, binary in enumerate(binaries):
        handoff = binary.get('compiler_metadata', {}).get('flagprism_ascend_handoff', {})
        declared = handoff.get('output')
        root = Path(declared) if isinstance(declared, str) else None
        if root is not None and (not root.is_absolute() or '..' in root.parts
                or len(root.parts) < 3 or root.parts[1] != 'tmp'
                or not root.parts[2].startswith('flagprism-ascend-compiler-')):
            root = None
        for index, artifact in enumerate(handoff.get('artifacts', [])):
            location = f'/{binary_index}/compiler_metadata/flagprism_ascend_handoff/artifacts/{index}'
            for field in ('original_input', 'adapted'):
                save(artifact.get(field), location + '/' + field, root, 'llvm')
            save(artifact.get('driver_job', {}).get('object'),
                 location + '/driver_job/object', root, 'object')
        # SDK/link inputs and final link outputs are receipt-only. Never decode
        # their embedded bytes or read a library/archive from the filesystem.
        for index, job in enumerate(handoff.get('codegen_jobs', [])):
            for item in job.get('input_files', []):
                if isinstance(item, dict):
                    entries.append(dict(location=f'/{binary_index}/codegen_jobs/{index}/input_files',
                                        producer_path=item.get('path'),
                                        producer_sha256=item.get('sha256'),
                                        status='excluded', excluded_reason='sdk_or_link_dependency_receipt_only'))
    write_json(destination / 'index.json', entries)
    return dict(status='retained_available_bytes', entries=len(entries))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', choices=['ordinary', 'default'], required=True)
    parser.add_argument('--config', choices=['bm16', 'bm32'], required=True)
    parser.add_argument('--state', choices=['scalar', 'vector', 'atomic'], required=True)
    parser.add_argument('--device', type=int, default=4)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).read_bytes()
    (args.output / 'source.py').write_bytes(source)
    bm, n, k, programs = (16 if args.config == 'bm16' else 32), 32, 32, 2
    m = bm * programs
    kind = {'scalar': 0, 'vector': 1, 'atomic': 2}[args.state]
    plan = dict(source_sha256=sha(source), mode=args.mode, state=args.state,
                config=args.config, shape=dict(M=m, N=n, K=k),
                tile=dict(BM=bm, BN=32, BK=32), grid=[programs, 1, 1],
                options=dict(enable_auto_blockify=False), device=args.device,
                invocation_budget=1, state_is_diagnostic_only=True,
                actor_bank_probe='not_available_no_verified_public_intrinsic')
    write_json(args.output / 'plan.json', plan)
    ledger = dict(attempted=0, returned=0, synchronized=False)
    write_json(args.output / 'host-ledger.json', ledger)
    torch.npu.set_device(args.device)
    device = f'npu:{args.device}'
    # Deterministic public values, no RNG, warmup, autotuning, or timing loop.
    ca = ((torch.arange(m * k).reshape(m, k) % 19) - 9).half() / 32
    cb = ((torch.arange(k * n).reshape(k, n) % 13) - 6).half() / 32
    cc = ((torch.arange(n) % 7) - 3).float() / 16
    expected = torch.relu(ca.float() @ cb.float() + cc) + 0.25
    a, b, bias = ca.to(device), cb.to(device), cc.to(device)
    guard, out_canary, state_canary = 64, -12345.0, -123456789
    state_elements = m * n if kind == 1 else programs
    out_storage = torch.full((m * n + 2 * guard,), out_canary, device=device)
    out = out_storage[guard:-guard].view(m, n)
    state_storage = torch.full((state_elements + 2 * guard,), state_canary,
                               dtype=torch.int32, device=device)
    state = state_storage[guard:-guard]
    state.zero_()
    write_json(args.output / 'launch-arguments.json',
               [inventory('a', a, a), inventory('b', b, b),
                inventory('bias', bias, bias), inventory('out', out_storage, out),
                inventory('state', state_storage, state)])
    session = None
    compiled = None
    errors = []
    result = dict(plan=plan, pid=os.getpid(), status='pending', checks={})
    try:
        if args.mode == 'default':
            session = profiler.start(str(args.output / 'capture'),
                                     backend='cann', detail='auto')
        ledger['attempted'] = 1
        write_json(args.output / 'host-ledger.json', ledger)
        compiled = state_probe[(programs,)](
            a, b, bias, out, state, m, n, k, bm, 32, 32, kind,
            enable_auto_blockify=False)
        ledger['returned'] = 1
        torch.npu.synchronize()
        ledger['synchronized'] = True
    except BaseException:
        errors.append(dict(phase='launch', traceback=traceback.format_exc()))
    finally:
        write_json(args.output / 'host-ledger.json', ledger)
        if session is not None:
            try:
                profiler.finalize(session)
            except BaseException:
                errors.append(dict(phase='finalize', traceback=traceback.format_exc()))
    # Do not read device storage after an unconfirmed/failed synchronization.
    if ledger['synchronized']:
        actual = state.cpu()
        result['state_observation'] = dict(
            elements=actual.numel(), values=actual.tolist(),
            unique=torch.unique(actual).tolist(),
            equals_one_observation=bool((actual == 1).all()),
            oracle='none; requires actual physical ownership analysis')
        checks = [
            ('math', lambda: torch.testing.assert_close(out.cpu(), expected, rtol=2e-3, atol=2e-4)),
            ('input_a', lambda: torch.testing.assert_close(a.cpu(), ca, rtol=0, atol=0)),
            ('input_b', lambda: torch.testing.assert_close(b.cpu(), cb, rtol=0, atol=0)),
            ('input_bias', lambda: torch.testing.assert_close(bias.cpu(), cc, rtol=0, atol=0)),
            ('output_canary_left', lambda: torch.testing.assert_close(out_storage[:guard].cpu(), torch.full((guard,), out_canary), rtol=0, atol=0)),
            ('output_canary_right', lambda: torch.testing.assert_close(out_storage[-guard:].cpu(), torch.full((guard,), out_canary), rtol=0, atol=0)),
            ('state_canary_left', lambda: torch.testing.assert_close(state_storage[:guard].cpu(), torch.full((guard,), state_canary, dtype=torch.int32), rtol=0, atol=0)),
            ('state_canary_right', lambda: torch.testing.assert_close(state_storage[-guard:].cpu(), torch.full((guard,), state_canary, dtype=torch.int32), rtol=0, atol=0)),
        ]
        for name, check in checks:
            try:
                check()
                result['checks'][name] = 'pass'
            except BaseException:
                result['checks'][name] = 'fail'
                errors.append(dict(phase=name, traceback=traceback.format_exc()))
    try:
        if compiled is not None:
            result['compiled_hash'] = str(compiled.hash)
            result['compiled_products'] = retain_compiled(compiled, args.output / 'compiled')
        result['capture_retention'] = retain_public_capture(
            args.output / 'capture', args.output / 'generated')
    except BaseException:
        errors.append(dict(phase='retention', traceback=traceback.format_exc()))
    result['host_ledger'] = ledger
    result['errors'] = errors
    result['status'] = 'error' if errors else 'diagnostic_completed'
    result['pointer_chain_limits'] = (
        'launch-arguments.json proves Python input/storage addresses only; '
        'final roles and State/trace GEPs need generated LLVM audit. '
        'Actual hidden trace runtime address is not exposed by this probe; '
        'no claim of complete launcher-to-formal pointer proof.')
    write_json(args.output / 'result.json', result)
    print(json.dumps(dict(status=result['status'], state=args.state,
                          config=args.config, mode=args.mode,
                          state_unique=result.get('state_observation', {}).get('unique'))))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
