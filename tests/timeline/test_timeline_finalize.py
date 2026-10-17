"""Fault contracts for finalization, not device/timing qualification."""
import hashlib
import importlib
import json
from pathlib import Path

import pytest
from flagtree.profiler.hooks.timeline import TimelineInstrumentationMixin, _persist
from flagtree.profiler.timeline_runtime import TimelineOwnerPool


class Transport:
    def __init__(self):
        self.actions = []
        self.fail_release = set()
        self.fail_read = set()

    def plan_storage(self, plan, **kwargs):
        return dict(raw_bytes=16, scratch_size=16, slots=[0], grid=[1, 1, 1])

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
        return True

    def read_raw(self, owner):
        identity = owner['invocation_id']
        self.actions.append(('read', identity))
        if identity in self.fail_read:
            raise OSError('injected read failure')
        return bytes(16)

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
        identity = hook.timeline_pool.prepare(dict(binary_id='binary'),
            binary_id='binary', function=42, grid=(1, 1, 1), scratch_size=16,
            alignment=16, num_ctas=1, device=0, stream=i)
        hook.timeline_pool.allocate(identity)
        hook.timeline_pool.mark_submitting(identity)
        hook.timeline_pool.finish_submission(identity)
        hook._timeline_descriptors[identity] = dict(launch={'invocation_id':identity},
            metadata=dict(compiler_metadata={'num_warps':1}, scope_id_names=[[1, 'region']]))
    ids = hook.timeline_pool.invocation_ids
    decoder = importlib.import_module('flagtree.profiler.timeline_nvidia')
    mapper = importlib.import_module('flagtree.profiler.timeline_nvidia_async')
    adapter = importlib.import_module('flagtree.profiler.timeline_events_nvidia')
    machine = importlib.import_module('flagtree.profiler.timeline_nvidia_machine')
    monkeypatch.setattr(decoder, 'decode_timeline_ring', lambda *a, **kw: {'complete':True})
    monkeypatch.setattr(mapper, 'derive_cp_async_facts', lambda *a, **kw: {})
    monkeypatch.setattr(adapter, 'canonicalize_nvidia_capture', lambda *a, **kw: {})
    monkeypatch.setattr(machine, 'inspect_capture_binary', lambda *a, **kw: {'status':'fixture'})
    yield hook, transport, ids
    # Cleanup only the fake transport, never releases unknown actual writers.
    transport.fail_read.clear()
    transport.fail_release.clear()
    for identity in hook.timeline_pool.invocation_ids:
        if hook.timeline_pool.snapshot(identity)['state'] == 'read_failed':
            hook.timeline_pool.retry_read(identity)
        else:
            hook.timeline_pool.read(identity)
        hook.timeline_pool.release(identity)
    hook.timeline_pool.close()


def read_index(base):
    return json.loads(Path(base).with_suffix('.timeline').joinpath('index.json').read_text())


def test_decoder_failure_saves_all_owners_and_retry_uses_only_originals(collector, tmp_path, monkeypatch):
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
    base = tmp_path/'capture'
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
    originals = {p:hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in directory.glob('captures/*') if p.suffix == '.raw' or p.name.endswith('.input.json')}
    if len(originals) != 4:
        raise RuntimeError('Not all invocation originals were retained')
    actions = list(transport.actions)
    first_attempt = (directory/'attempts/flush-0001.json').read_bytes()
    monkeypatch.setattr(hook, '_decode_timeline_original', original)
    hook.flush_timeline(base)
    index = read_index(base)
    if len(index['captures']) != 2 or index['pending_decode'] or index['failures']:
        raise RuntimeError('Retry lost, duplicated or failed a capture')
    if transport.actions != actions:
        raise RuntimeError('Retry touched the device transport')
    if any(hashlib.sha256(p.read_bytes()).hexdigest() != sha for p,sha in originals.items()):
        raise RuntimeError('Retry changed originals')
    if (directory/'attempts/flush-0001.json').read_bytes() != first_attempt:
        raise RuntimeError('Retry overwrote first failure history')


def test_read_failure_does_not_block_other_owner(collector, tmp_path):
    hook, transport, ids = collector
    transport.fail_read.add(ids[0])
    with pytest.raises(OSError, match='read failure'):
        hook.flush_timeline(tmp_path/'capture')
    if hook.timeline_pool.invocation_ids != (ids[0],) or hook.timeline_pool.snapshot(ids[0])['state'] != 'read_failed':
        raise RuntimeError('Read failure prematurely released resource')
    if read_index(tmp_path/'capture')['captures'][0]['invocation_id'] != ids[1]:
        raise RuntimeError('Read failure prevented second salvage')
    transport.fail_read.clear()
    hook.flush_timeline(tmp_path/'capture')
    if hook.timeline_pool.invocation_ids or len(read_index(tmp_path/'capture')['captures']) != 2:
        raise RuntimeError('Read retry failed')


def test_release_failure_is_owned_and_not_decoded(collector, tmp_path):
    hook, transport, ids = collector
    transport.fail_release.add(ids[0])
    with pytest.raises(OSError, match='release failure'):
        hook.flush_timeline(tmp_path/'capture')
    if hook.timeline_pool.invocation_ids != (ids[0],):
        raise RuntimeError('Release error lost ownership')
    index = read_index(tmp_path/'capture')
    if index['pending_decode'] != [ids[0]] or len(index['captures']) != 1:
        raise RuntimeError('Release failure decoded unresolved owner or blocked next owner')
    transport.fail_release.clear()
    hook.flush_timeline(tmp_path/'capture')
    if hook.timeline_pool.invocation_ids:
        raise RuntimeError('Release retry still owns buffer')


def test_changed_original_detected_without_device_work(collector, tmp_path, monkeypatch):
    hook, transport, ids = collector
    original = hook._decode_timeline_original
    def fail(*args):
        raise ValueError('injected failure')
    monkeypatch.setattr(hook, '_decode_timeline_original', fail)
    with pytest.raises(ValueError):
        hook.flush_timeline(tmp_path/'capture')
    actions = list(transport.actions)
    directory = (tmp_path/'capture').with_suffix('.timeline')
    (directory/'captures'/f'{ids[0]}.raw').write_bytes(bytes([1])*16)
    monkeypatch.setattr(hook, '_decode_timeline_original', original)
    with pytest.raises(RuntimeError, match='raw changed'):
        hook.flush_timeline(tmp_path/'capture')
    if transport.actions != actions or len(read_index(tmp_path/'capture')['captures']) != 1:
        raise RuntimeError('Corruption triggered device work or blocked intact capture')


def test_recovery_directory_cannot_silently_mix_capture_paths(collector, tmp_path):
    hook, _, _ = collector
    hook.flush_timeline(tmp_path/'first')
    with pytest.raises(RuntimeError, match='original evidence directory'):
        hook.flush_timeline(tmp_path/'other')


def test_persistence_keeps_original_immutable_and_atomically_updates_journal(tmp_path):
    original = tmp_path/'original.raw'
    _persist(original, b'one')
    with pytest.raises(RuntimeError, match='Refusing to replace'):
        _persist(original, b'two')
    _persist(original, b'one')
    journal = tmp_path/'index.json'
    _persist(journal, b'one')
    _persist(journal, b'two', replace=True)
    if journal.read_bytes() != b'two' or original.read_bytes() != b'one':
        raise RuntimeError('Persistence mutated evidence or failed journal update')
    if list(tmp_path.glob('.timeline-*')):
        raise RuntimeError('Temporary persistence files leaked')
