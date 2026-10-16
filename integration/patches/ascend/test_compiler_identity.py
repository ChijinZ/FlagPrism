"""CPU-only actual Ascend selector, fingerprint and both JIT cache entrances."""
import builtins
import hashlib
import json
import os

import pytest

pytest_plugins = ['test_auto_blockify_cache']


def executable(tmp_path, name='bishengir-compile', data=b'compiler-one'):
    path = tmp_path / name
    path.write_bytes(data)
    path.chmod(0o755)
    return path


@pytest.fixture
def modules():
    import torch  # noqa: F401
    import torch_npu
    from triton.backends.ascend import compiler_identity, utils
    assert not torch_npu.npu.is_initialized()
    return compiler_identity, utils


@pytest.mark.parametrize(
    'kind', ['relative', 'missing', 'nonexec', 'directory', 'empty'])
def test_invalid_override_rejected(modules, monkeypatch, tmp_path, kind):
    _, utils = modules
    path = executable(tmp_path)
    choices = {
        'relative': path.name,
        'missing': str(tmp_path / 'absent'),
        'nonexec': str(path),
        'directory': str(tmp_path),
        'empty': ''
    }
    if kind == 'nonexec':
        path.chmod(0o644)
    monkeypatch.setenv('TRITON_ASCEND_COMPILER', choices[kind])
    with pytest.raises((ValueError, FileNotFoundError)):
        utils._get_npucompiler_path()


def test_override_realpath_and_stock_precedence(modules, monkeypatch,
                                                tmp_path):
    _, utils = modules
    packaged = tmp_path / 'bishengir/bin/bishengir-compile'
    packaged.parent.mkdir(parents=True)
    packaged.write_bytes(b'packaged')
    packaged.chmod(0o755)
    path_tool = executable(tmp_path, 'path-compiler')
    legacy = tmp_path / 'legacy'
    legacy.mkdir()
    executable(legacy, 'npuc')
    override = executable(tmp_path, 'override')
    link = tmp_path / 'override-link'
    link.symlink_to(override)
    monkeypatch.setattr(utils, '__file__', str(tmp_path / 'utils.py'))
    monkeypatch.setattr(utils.shutil, 'which', lambda name: str(path_tool))
    monkeypatch.setenv('TRITON_NPU_COMPILER_PATH', str(legacy))
    monkeypatch.delenv('TRITON_ASCEND_COMPILER', raising=False)
    assert utils._get_npucompiler_path()[0] == str(packaged)
    packaged.unlink()
    assert utils._get_npucompiler_path()[0] == str(path_tool)
    monkeypatch.setattr(utils.shutil, 'which', lambda name: None)
    assert utils._get_npucompiler_path()[0] == str(legacy / 'npuc')
    monkeypatch.setenv('TRITON_ASCEND_COMPILER', str(link))
    assert utils._get_npucompiler_path()[0] == str(override)


def test_digest_hot_calls_and_same_path_replacement(modules, monkeypatch,
                                                    tmp_path):
    identity, _ = modules
    path = executable(tmp_path, data=b'x' * (5 * 1024 * 1024))
    real_open = builtins.open
    reads = []

    def counted(file, *args, **kwargs):
        if os.fspath(file) == str(path):
            reads.append(file)
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, 'open', counted)
    token = identity.compiler_identity(str(path))
    for _ in range(30):
        assert identity.compiler_identity(str(path)) == token
    assert len(reads) == 1
    old = path.stat()
    replacement = executable(tmp_path, 'replacement', b'y' * old.st_size)
    os.utime(replacement, ns=(old.st_atime_ns, old.st_mtime_ns))
    replacement.replace(path)
    changed = identity.compiler_identity(str(path))
    assert changed != token and len(reads) == 2
    # In-place content update with size and mtime restored also changes ctime.
    path.write_bytes(b'z' * old.st_size)
    os.utime(path, ns=(old.st_atime_ns, old.st_mtime_ns))
    assert identity.compiler_identity(str(path)) != changed
    assert len(reads) == 3


def test_unstable_read_bounded_retry_and_recovery(modules, monkeypatch,
                                                  tmp_path):
    identity, _ = modules
    path = executable(tmp_path)
    real_open = builtins.open
    reads = []

    class ReplacingReader:

        def __init__(self, stream):
            self.stream = stream
            self.changed = False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def fileno(self):
            return self.stream.fileno()

        def read(self, count):
            data = self.stream.read(count)
            if not self.changed:
                self.changed = True
                replacement = executable(tmp_path, 'replacement',
                                         b'new-' + bytes([len(reads)]))
                replacement.replace(path)
            return data

    def replacing_open(file, *args, **kwargs):
        stream = real_open(file, *args, **kwargs)
        if os.fspath(file) == str(path):
            reads.append(file)
            return ReplacingReader(stream)
        return stream

    with monkeypatch.context() as patch:
        patch.setattr(builtins, 'open', replacing_open)
        with pytest.raises(RuntimeError, match='changed while fingerprinting'):
            identity.compiler_identity(str(path))
        assert len(reads) == 3
    token = identity.compiler_identity(str(path))
    assert json.loads(token)['sha256'] == hashlib.sha256(
        path.read_bytes()).hexdigest()
    metadata = {}
    assert identity.bind_compiler_identity(str(path), token,
                                           metadata) == str(path)
    assert metadata['ascend_compiler_identity'] == json.loads(token)
    path.write_bytes(b'changed')
    with pytest.raises(RuntimeError, match='after JIT option binding'):
        identity.bind_compiler_identity(str(path), token, {})


def test_actual_jit_compiler_identity_switch_and_replacement(
        jit_cache, monkeypatch, tmp_path):
    fn, compilations, torch_npu = jit_cache
    first = executable(tmp_path, 'first')
    second = executable(tmp_path, 'second', b'compiler-one')
    results = []
    for path in (first, second, first):
        monkeypatch.setenv('TRITON_ASCEND_COMPILER', str(path))
        results.append(fn.run(7, grid=(1, ), warmup=True))
    assert len(compilations) == 2 and results[0] is results[2]
    assert results[0].hash != results[1].hash
    assert json.loads(
        results[0].metadata.compiler_identity)['sha256'] == json.loads(
            results[1].metadata.compiler_identity)['sha256']
    monkeypatch.setenv('TRITON_ASCEND_COMPILER', str(tmp_path / 'absent'))
    with pytest.raises(FileNotFoundError):
        fn.run(7, grid=(1, ), warmup=True)
    monkeypatch.setenv('TRITON_ASCEND_COMPILER', str(first))
    assert fn.run(7, grid=(1, ), warmup=True) is results[0]
    assert len(compilations) == 2
    old = first.stat()
    first.write_bytes(b'compiler-new')
    os.utime(first, ns=(old.st_atime_ns, old.st_mtime_ns))
    replaced = fn.run(7, grid=(1, ), warmup=True)
    assert len(compilations) == 3 and replaced is not results[0]
    # Profiler mode changes independently; it binds the same compiler identity.
    profiled = fn.run(7,
                      grid=(1, ),
                      warmup=True,
                      instrumentation_mode='identity-test')
    assert profiled.metadata.compiler_identity == replaced.metadata.compiler_identity
    assert len(compilations) == 4
    assert not torch_npu.npu.is_initialized()


@pytest.mark.parametrize('failure', ['init', 'add'])
def test_watch_unavailable_fresh_hash_fallback(modules, monkeypatch, tmp_path,
                                               failure):
    identity, _ = modules
    watch = identity._Invalidations()
    function = 'inotify_init1' if failure == 'init' else 'inotify_add_watch'
    monkeypatch.setattr(watch.libc, function, lambda *args: -1)
    monkeypatch.setattr(identity, '_WATCH', watch)
    path = executable(tmp_path)
    real_open = builtins.open
    reads = []

    def counted(file, *args, **kwargs):
        if os.fspath(file) == str(path):
            reads.append(file)
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, 'open', counted)
    first = identity.compiler_identity(str(path))
    assert identity.compiler_identity(str(path)) == first
    old = path.stat()
    path.write_bytes(b'compiler-new')
    os.utime(path, ns=(old.st_atime_ns, old.st_mtime_ns))
    assert identity.compiler_identity(str(path)) != first
    assert len(reads) == 3 and str(path) not in identity._CACHE


def test_watch_overflow_disables_cache(modules, monkeypatch, tmp_path):
    import struct
    identity, _ = modules
    watch = identity._Invalidations()
    monkeypatch.setattr(identity, '_WATCH', watch)
    path = executable(tmp_path)
    identity.compiler_identity(str(path))
    assert watch.fd is not None and str(path) in identity._CACHE
    real_read = os.read
    fd = watch.fd

    def overflow(descriptor, size):
        if descriptor == fd:
            return struct.pack('iIII', -1, watch._OVERFLOW, 0, 0)
        return real_read(descriptor, size)

    with monkeypatch.context() as patch:
        patch.setattr(os, 'read', overflow)
        identity.compiler_identity(str(path))
    assert watch.failed and watch.fd is None and not identity._CACHE
    old = path.stat()
    path.write_bytes(b'compiler-new')
    os.utime(path, ns=(old.st_atime_ns, old.st_mtime_ns))
    assert json.loads(identity.compiler_identity(
        str(path)))['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_fork_resets_watch_and_inherited_lock(modules, tmp_path):
    import select
    import signal
    identity, _ = modules
    path = executable(tmp_path)
    first = identity.compiler_identity(str(path))
    reader, writer = os.pipe()
    identity._LOCK.acquire()
    pid = os.fork()
    if pid == 0:
        try:
            os.close(reader)
            path.write_bytes(b'compiler-new')
            token = identity.compiler_identity(str(path))
            result = json.dumps({
                'token': token,
                'watch_pid': identity._WATCH.pid,
                'pid': os.getpid()
            }).encode()
            os.write(writer, result)
            os._exit(0)
        except BaseException:
            os._exit(1)
    identity._LOCK.release()
    os.close(writer)
    try:
        ready, _, _ = select.select([reader], [], [], 10)
        if not ready:
            os.kill(pid, signal.SIGKILL)
        _, status = os.waitpid(pid, 0)
        assert ready and status == 0
        result = json.loads(os.read(reader, 4096))
    finally:
        os.close(reader)
    assert result['watch_pid'] == result['pid'] == pid
    assert result['token'] != first
    assert identity.compiler_identity(str(path)) == result['token']
    assert identity._WATCH.pid == os.getpid()


def test_watch_resources_bounded(modules, tmp_path):
    identity, _ = modules
    for index in range(70):
        identity.compiler_identity(str(executable(tmp_path, str(index))))
    assert not identity._WATCH.failed
    assert len(identity._WATCH.paths) <= 64
    assert len(identity._CACHE) <= 64


def test_notifications_invalidate_identical_stat_key(modules, monkeypatch,
                                                     tmp_path):
    identity, _ = modules
    path = executable(tmp_path)
    stamp = identity._stamp(path.stat())
    # Reproduce the observed same-tick metadata alias deterministically, without
    # sleeping or weakening the original real-JIT in-place replacement test.
    monkeypatch.setattr(identity, '_stamp', lambda info: stamp)
    first = identity.compiler_identity(str(path))
    assert not identity._WATCH.failed and str(path) in identity._CACHE
    old = path.stat()
    path.write_bytes(b'compiler-new')
    os.utime(path, ns=(old.st_atime_ns, old.st_mtime_ns))
    assert identity.compiler_identity(str(path)) != first


def test_concurrent_cold_identity_reads_binary_once(modules, monkeypatch,
                                                    tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    identity, _ = modules
    path = executable(tmp_path, data=b'x' * (5 * 1024 * 1024))
    real_open = builtins.open
    reads = []

    def counted(file, *args, **kwargs):
        if os.fspath(file) == str(path):
            reads.append(file)
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, 'open', counted)
    with ThreadPoolExecutor(max_workers=8) as pool:
        tokens = list(pool.map(identity.compiler_identity, [str(path)] * 16))
    assert len(set(tokens)) == 1 and len(reads) == 1
    assert not identity._WATCH.failed


def test_actual_jit_identical_stat_key_recompiles(jit_cache, monkeypatch,
                                                  tmp_path):
    from triton.backends.ascend import compiler_identity as identity
    fn, compilations, torch_npu = jit_cache
    path = executable(tmp_path)
    stamp = identity._stamp(path.stat())
    monkeypatch.setattr(identity, '_stamp', lambda info: stamp)
    monkeypatch.setenv('TRITON_ASCEND_COMPILER', str(path))
    first = fn.run(7, grid=(1, ), warmup=True)
    old = path.stat()
    path.write_bytes(b'compiler-new')
    os.utime(path, ns=(old.st_atime_ns, old.st_mtime_ns))
    changed = fn.run(7, grid=(1, ), warmup=True)
    hot = fn.run(7, grid=(1, ), warmup=True)
    assert len(compilations) == 2 and changed is hot and first is not changed
    assert first.hash != changed.hash
    assert first.metadata.compiler_identity != changed.metadata.compiler_identity
    assert not torch_npu.npu.is_initialized()


def test_parse_options_rejects_stale_binding_before_disk_cache(
        modules, monkeypatch, tmp_path):
    from triton.backends.ascend import compiler
    path = executable(tmp_path)
    monkeypatch.setenv('TRITON_ASCEND_COMPILER', str(path))
    backend = compiler.AscendBackend(compiler.GPUTarget(
        'npu', 'Ascend910B', 0))
    options = backend.normalize_launch_options({})
    old = path.stat()
    path.write_bytes(b'compiler-new')
    os.utime(path, ns=(old.st_atime_ns, old.st_mtime_ns))
    with pytest.raises(RuntimeError, match='after JIT option binding'):
        backend.parse_options(options)
    current = backend.normalize_launch_options({})
    assert backend.parse_options(
        current).compiler_identity == current['compiler_identity']
    assert current['compiler_identity'] != options['compiler_identity']
