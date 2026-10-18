"""Fault contracts for finalization, not device/timing qualification."""
import hashlib
import importlib
import json
from pathlib import Path

import pytest
from flagtree.profiler.hooks.timeline import TimelineInstrumentationMixin, _persist
from flagtree.profiler.timeline_runtime import TimelineOwnerPool, TimelineReadback


class Transport:

    def __init__(self):
        self.actions = []
        self.fail_release = set()
        self.fail_read = set()
        self.blocked = set()
        self.readbacks = {}

    def plan_storage(self, plan, **kwargs):
        return dict(raw_bytes=16,
                    scratch_size=16,
                    slots=((0, 0), ),
                    grid=[1, 1, 1])

    def validate_target(self, **kwargs):
        pass

    def allocate(self, owner):
        return object()

    def initialize(self, owner):
        pass

    def launch_buffer(self, owner):
        return owner['resource']

    def record_completion(self, owner):
        pass

    def completion_ready(self, owner):
        return owner['invocation_id'] not in self.blocked

    def read_raw(self, owner):
        identity = owner['invocation_id']
        self.actions.append(('read', identity))
        if identity in self.fail_read:
            raise OSError('injected read failure')
        return self.readbacks.get(identity, bytes(16))

    def release(self, owner):
        identity = owner['invocation_id']
        self.actions.append(('release', identity))
        if identity in self.fail_release:
            raise OSError('injected release failure')
        owner['resource'] = None


@pytest.fixture
def collector(monkeypatch):
    transport = Transport()
    hook = TimelineInstrumentationMixin()
    hook.timeline_pool = TimelineOwnerPool(transport)
    hook._timeline_descriptors = {}
    hook._timeline_rows = []
    hook._timeline_machine = {}
    hook._timeline_pending = {}
    hook._timeline_directory = None
    hook._timeline_flush_attempt = 0
    for i in range(2):
        identity = hook.timeline_pool.prepare(dict(binary_id='binary',
                                                   timeline_record_version=2),
                                              binary_id='binary',
                                              function=42,
                                              grid=(1, 1, 1),
                                              scratch_size=16,
                                              alignment=16,
                                              num_ctas=1,
                                              device=0,
                                              stream=i)
        hook.timeline_pool.allocate(identity)
        hook.timeline_pool.mark_submitting(identity)
        hook.timeline_pool.finish_submission(identity)
        hook._timeline_descriptors[identity] = dict(
            launch={'invocation_id': identity},
            metadata=dict(compiler_metadata={'num_warps': 1},
                          scope_id_names=[[1, 'region']]))
    ids = hook.timeline_pool.invocation_ids
    decoder = importlib.import_module('flagtree.profiler.timeline_nvidia')
    mapper = importlib.import_module('flagtree.profiler.timeline_nvidia_async')
    adapter = importlib.import_module(
        'flagtree.profiler.timeline_events_nvidia')
    machine = importlib.import_module(
        'flagtree.profiler.timeline_nvidia_machine')

    def decode(*args, **kwargs):
        slots = kwargs['slots']
        if type(slots) is not tuple or not slots or any(
                type(row) is not tuple or len(row) != 2 for row in slots):
            raise ValueError(
                'Physical decoder requires tuple slot pairs after JSON rehydration'
            )
        return {'complete': True}

    monkeypatch.setattr(decoder, 'decode_timeline_ring', decode)
    monkeypatch.setattr(mapper, 'derive_cp_async_facts', lambda *a, **kw: {})
    monkeypatch.setattr(adapter, 'canonicalize_nvidia_capture',
                        lambda *a, **kw: {})
    monkeypatch.setattr(machine, 'inspect_capture_binary',
                        lambda *a, **kw: {'status': 'fixture'})
    yield hook, transport, ids
    # Cleanup only the fake transport, never releases unknown actual writers.
    transport.fail_read.clear()
    transport.fail_release.clear()
    transport.blocked.clear()
    for identity in hook.timeline_pool.invocation_ids:
        if hook.timeline_pool.snapshot(identity)['state'] == 'read_failed':
            hook.timeline_pool.retry_read(identity)
        else:
            hook.timeline_pool.read(identity)
        hook.timeline_pool.release(identity)
    hook.timeline_pool.close()


def read_index(base):
    return json.loads(
        Path(base).with_suffix('.timeline').joinpath('index.json').read_text())


def test_decoder_failure_saves_all_owners_and_retry_uses_only_originals(
        collector, tmp_path, monkeypatch):
    hook, transport, ids = collector
    original = hook._decode_timeline_original
    failure = ValueError('injected first decoder failure')

    def decode(identity, directory, deadline):
        if hook.timeline_pool.invocation_ids or hook.timeline_pool.pending_bytes:
            raise RuntimeError('Decoder ran before safe owners were released')
        if identity == ids[0]:
            raise failure
        return original(identity, directory, deadline)

    monkeypatch.setattr(hook, '_decode_timeline_original', decode)
    base = tmp_path / 'capture'
    with pytest.raises(ValueError) as error:
        hook.flush_timeline(base)
    if error.value is not failure:
        raise RuntimeError('First exception identity was lost')
    index = read_index(base)
    if index['pending_decode'] != [ids[0]] or index['retained_owners']:
        raise RuntimeError('Wrong pending/released state')
    if [c['invocation_id'] for c in index['captures']] != [ids[1]]:
        raise RuntimeError('First failure prevented second decode')
    directory = base.with_suffix('.timeline')
    originals = {
        p: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in directory.glob('captures/*')
        if p.suffix == '.raw' or p.name.endswith('.input.json')
    }
    if len(originals) != 4:
        raise RuntimeError('Not all invocation originals were retained')
    actions = list(transport.actions)
    first_attempt = (directory / 'attempts/flush-0001.json').read_bytes()
    monkeypatch.setattr(hook, '_decode_timeline_original', original)
    hook.flush_timeline(base)
    index = read_index(base)
    if len(index['captures']
           ) != 2 or index['pending_decode'] or index['failures']:
        raise RuntimeError('Retry lost, duplicated or failed a capture')
    if transport.actions != actions:
        raise RuntimeError('Retry touched the device transport')
    if any(
            hashlib.sha256(p.read_bytes()).hexdigest() != sha
            for p, sha in originals.items()):
        raise RuntimeError('Retry changed originals')
    if (directory / 'attempts/flush-0001.json').read_bytes() != first_attempt:
        raise RuntimeError('Retry overwrote first failure history')


def test_read_failure_does_not_block_other_owner(collector, tmp_path):
    hook, transport, ids = collector
    transport.fail_read.add(ids[0])
    with pytest.raises(OSError, match='read failure'):
        hook.flush_timeline(tmp_path / 'capture')
    if hook.timeline_pool.invocation_ids != (
            ids[0], ) or hook.timeline_pool.snapshot(
                ids[0])['state'] != 'read_failed':
        raise RuntimeError('Read failure prematurely released resource')
    if read_index(tmp_path /
                  'capture')['captures'][0]['invocation_id'] != ids[1]:
        raise RuntimeError('Read failure prevented second salvage')
    transport.fail_read.clear()
    hook.flush_timeline(tmp_path / 'capture')
    if hook.timeline_pool.invocation_ids or len(
            read_index(tmp_path / 'capture')['captures']) != 2:
        raise RuntimeError('Read retry failed')


def test_release_failure_is_owned_and_not_decoded(collector, tmp_path):
    hook, transport, ids = collector
    transport.fail_release.add(ids[0])
    with pytest.raises(OSError, match='release failure'):
        hook.flush_timeline(tmp_path / 'capture')
    if hook.timeline_pool.invocation_ids != (ids[0], ):
        raise RuntimeError('Release error lost ownership')
    index = read_index(tmp_path / 'capture')
    if index['pending_decode'] != [ids[0]] or len(index['captures']) != 1:
        raise RuntimeError(
            'Release failure decoded unresolved owner or blocked next owner')
    transport.fail_release.clear()
    hook.flush_timeline(tmp_path / 'capture')
    if hook.timeline_pool.invocation_ids:
        raise RuntimeError('Release retry still owns buffer')


def test_changed_original_detected_without_device_work(collector, tmp_path,
                                                       monkeypatch):
    hook, transport, ids = collector
    original = hook._decode_timeline_original

    def fail(*args):
        raise ValueError('injected failure')

    monkeypatch.setattr(hook, '_decode_timeline_original', fail)
    with pytest.raises(ValueError):
        hook.flush_timeline(tmp_path / 'capture')
    actions = list(transport.actions)
    directory = (tmp_path / 'capture').with_suffix('.timeline')
    (directory / 'captures' / f'{ids[0]}.raw').write_bytes(bytes([1]) * 16)
    monkeypatch.setattr(hook, '_decode_timeline_original', original)
    with pytest.raises(RuntimeError, match='raw changed'):
        hook.flush_timeline(tmp_path / 'capture')
    if transport.actions != actions or len(
            read_index(tmp_path / 'capture')['captures']) != 1:
        raise RuntimeError(
            'Corruption triggered device work or blocked intact capture')


def test_recovery_directory_cannot_silently_mix_capture_paths(
        collector, tmp_path):
    hook, _, _ = collector
    hook.flush_timeline(tmp_path / 'first')
    with pytest.raises(RuntimeError, match='original evidence directory'):
        hook.flush_timeline(tmp_path / 'other')


def test_persistence_keeps_original_immutable_and_atomically_updates_journal(
        tmp_path):
    original = tmp_path / 'original.raw'
    _persist(original, b'one')
    with pytest.raises(RuntimeError, match='Refusing to replace'):
        _persist(original, b'two')
    _persist(original, b'one')
    journal = tmp_path / 'index.json'
    _persist(journal, b'one')
    _persist(journal, b'two', replace=True)
    if journal.read_bytes() != b'two' or original.read_bytes() != b'one':
        raise RuntimeError(
            'Persistence mutated evidence or failed journal update')
    if list(tmp_path.glob('.timeline-*')):
        raise RuntimeError('Temporary persistence files leaked')


def test_journal_error_does_not_mask_original_decoder_error(
        collector, tmp_path, monkeypatch):
    hook, _, ids = collector
    module = importlib.import_module('flagtree.profiler.hooks.timeline')
    original_persist = module._persist
    original_decode = hook._decode_timeline_original
    failure = ValueError('first decoder error survives journal failure')

    def persist(path, payload, **kwargs):
        if path.parent.name == 'attempts':
            raise OSError('injected attempt journal failure')
        return original_persist(path, payload, **kwargs)

    def decode(identity, directory, deadline):
        if identity == ids[0]:
            raise failure
        return original_decode(identity, directory, deadline)

    monkeypatch.setattr(module, '_persist', persist)
    monkeypatch.setattr(hook, '_decode_timeline_original', decode)
    with pytest.raises(ValueError) as error:
        hook.flush_timeline(tmp_path / 'capture')
    if error.value is not failure or hook.timeline_pool.invocation_ids:
        raise RuntimeError(
            'Journal failure masked first error or retained safe resources')
    index = read_index(tmp_path / 'capture')
    if [e['stage'] for e in index['failures']
        ] != ['decode_export', 'persist_attempt']:
        raise RuntimeError(
            'Journal failure not reported alongside original error')


def test_invalid_readback_keeps_original_and_guard_then_releases(
        collector, tmp_path):
    hook, transport, ids = collector
    raw = bytes(range(16))
    guard = b'corrupted-allocation-guard'
    transport.readbacks[ids[0]] = TimelineReadback(
        raw, guard, ('allocation_guard_changed', ))
    base = tmp_path / 'capture'
    with pytest.raises(ValueError, match='readback integrity failed'):
        hook.flush_timeline(base)
    directory = base.with_suffix('.timeline')
    if hook.timeline_pool.invocation_ids:
        raise RuntimeError(
            'Safe persisted corrupt capture left device resources owned')
    if (directory / 'captures' / f'{ids[0]}.raw').read_bytes() != raw:
        raise RuntimeError('Integrity failure discarded acquired payload')
    if (directory / 'captures' / f'{ids[0]}.guard.raw').read_bytes() != guard:
        raise RuntimeError('Integrity failure discarded guard evidence')
    original = (directory / 'captures' / f'{ids[0]}.input.json').read_bytes()
    actions = list(transport.actions)
    with pytest.raises(ValueError, match='readback integrity failed'):
        hook.flush_timeline(base)
    if actions != transport.actions or original != (
            directory / 'captures' / f'{ids[0]}.input.json').read_bytes():
        raise RuntimeError(
            'Invalid original replayed application/transport or changed evidence'
        )
    if [c['invocation_id'] for c in read_index(base)['captures']] != [ids[1]]:
        raise RuntimeError(
            'Invalid capture blocked an independent valid capture')


def test_acquired_wrong_extent_is_retained_as_invalid_not_read_failure(
        collector, tmp_path):
    hook, transport, ids = collector
    transport.readbacks[ids[0]] = b'actually-acquired-wrong-extent'
    with pytest.raises(ValueError, match='raw_extent_differs_from_admission'):
        hook.flush_timeline(tmp_path / 'capture')
    raw = tmp_path / 'capture.timeline' / 'captures' / f'{ids[0]}.raw'
    if raw.read_bytes() != transport.readbacks[
            ids[0]] or hook.timeline_pool.invocation_ids:
        raise RuntimeError(
            'Acquired wrong-size bytes were discarded or owner leaked')


def test_unknown_first_owner_cannot_starve_ready_owner(collector, tmp_path,
                                                       monkeypatch):
    from types import SimpleNamespace
    hook, transport, ids = collector
    module = importlib.import_module('flagtree.profiler.hooks.timeline')
    real_time = module.time
    ticks = [0.0]

    def monotonic():
        ticks[0] += 1
        return ticks[0]

    monkeypatch.setattr(
        module, 'time',
        SimpleNamespace(monotonic=monotonic, sleep=lambda _: None))
    transport.blocked.add(ids[0])
    base = tmp_path / 'capture'
    with pytest.raises(TimeoutError, match='budget exhausted'):
        hook.flush_timeline(base)
    index = read_index(base)
    if index['retained_owners'] != [ids[0]] or [
            c['invocation_id'] for c in index['captures']
    ] != [ids[1]]:
        raise RuntimeError('Unknown owner starved a ready original')
    if index['retained_owner_states'][ids[0]]['state'] != 'completion_pending':
        raise RuntimeError('Deadline exhaustion pretended writer completion')
    if ('read', ids[0]) in transport.actions:
        raise RuntimeError('Unknown completion authorized readback')
    transport.blocked.clear()
    monkeypatch.setattr(module, 'time', real_time)
    hook.flush_timeline(base)
    if len(read_index(base)
           ['captures']) != 2 or hook.timeline_pool.invocation_ids:
        raise RuntimeError('Bounded retry lost an owner or failed to recover')


def test_cuda_transport_returns_bad_guard_evidence_instead_of_throwing():
    from contextlib import nullcontext
    from types import SimpleNamespace
    from flagtree.profiler.timeline_cuda_runtime import CudaTimelineTransport
    transport = object.__new__(CudaTimelineTransport)
    transport.torch = SimpleNamespace(cuda=SimpleNamespace(
        device=lambda _: nullcontext(), stream=lambda _: nullcontext()))
    acquired = bytes(range(16)) + b'BAD!'
    allocation = SimpleNamespace(cpu=lambda: SimpleNamespace(
        numpy=lambda: SimpleNamespace(tobytes=lambda: acquired)))
    result = transport.read_raw(
        dict(device=0,
             resource=dict(allocation=allocation, stream=0),
             layout=dict(raw_bytes=16),
             guard_bytes=4))
    if not isinstance(
            result, TimelineReadback
    ) or result.raw != acquired[:16] or result.guard != b'BAD!':
        raise RuntimeError('CUDA readback failed to return acquired evidence')
    if result.validation_errors != ('allocation_guard_changed', ):
        raise RuntimeError('CUDA transport silently qualified corrupt guard')
