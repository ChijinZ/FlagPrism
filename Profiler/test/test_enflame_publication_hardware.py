"""Actual GCU publication bytes/layout and one-JIT shared-cache switch oracle."""
import os
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get('FLAGPRISM_TEST_ENFLAME') != '1',
    reason='requires selected formal Enflame hardware')


@pytest.mark.parametrize('work_items', [1, 4, 8])
def test_full_words_and_shared_cache_scalar_vector_scalar(
        tmp_path, monkeypatch, work_items):
    import json
    import torch
    import torch_gcu  # noqa:F401
    import triton
    import triton.language as tl
    import flagtree.profiler as profiler
    from flagtree.profiler import ObservationRequest

    @triton.jit(do_not_specialize=['ALPHA'])
    def original_vector_math(X, Y, N: tl.constexpr, B: tl.constexpr, ALPHA):
        offsets = tl.program_id(0) * B + tl.arange(0, B)
        values = tl.load(X + offsets, offsets < N, 0)
        tl.store(Y + offsets, values + ALPHA, offsets < N)

    n, block = 83, 64
    cpu = torch.arange(n, dtype=torch.float32, device='cpu')
    x = cpu.to('gcu')
    y = torch.empty_like(x)
    request = ObservationRequest(programs=(1, ), max_events_per_instance=64)
    kernels = []
    receipts = []
    for index, mode in enumerate(
        ('scalar16', 'vector16_per_work_item', 'scalar16')):
        monkeypatch.setenv('FLAGPRISM_GCU_DYNAMIC_PUBLISHER', mode)
        output = tmp_path / f'{index}-{mode}'
        session = profiler.start(str(output / 'bundle'),
                                 backend='enflame',
                                 hook='instrumentation',
                                 observation_request=request)
        try:
            kernel = original_vector_math[(2, )](x,
                                                 y,
                                                 n,
                                                 block,
                                                 1.,
                                                 num_warps=work_items)
            torch.gcu.synchronize()
        finally:
            profiler.finalize(session)
        torch.testing.assert_close(y.cpu(), cpu + 1, rtol=0, atol=0)
        metadata = kernel.metadata._asdict()
        metadata.pop('target', None)
        assert metadata['enable_i64'] is False
        assert metadata['debug_dynamic_publication_work_items'] == work_items
        expected = 'per_work_item_vector16_v1' if index == 1 else 'scalar16_v1'
        assert metadata['debug_dynamic_publication'] == expected
        assert f'"debug_dynamic_publication_mode":"{mode}"' in metadata[
            'instrumentation_mode']
        document = json.loads(
            (output / 'bundle/ai/observations.json').read_text())
        events = document['observations']
        captures = document['captures']
        assert len(captures) == 1 and events
        assert all(e['association_status'] == 'verified' and e['program'] == 1
                   and e['actor'] == 0 for e in events)
        assert all(e['start_tick'] > 0 and e['end_tick'] >= e['start_tick']
                   and e['duration_ns'] is None for e in events)
        header = captures[0]['header']
        assert header['record_size'] == 64 and header['overflow_count'] == 0
        assert header['write_idx'] == header['reserved0'] == len(events)
        # Decoder validates every word relationship and fixed 64-bit commit tag;
        # retain actual compiler ownership IR alongside the complete raw buffer.
        (output / 'metadata.json').write_text(
            json.dumps(metadata, indent=2, default=str))
        for stage, content in kernel.asm.items():
            if isinstance(content, (str, bytes)):
                (output / str(stage)).write_bytes(
                    content.encode() if isinstance(content, str) else content)
        kernels.append(kernel)
        receipts.append({
            'mode':
            mode,
            'binary_id':
            kernel.hash,
            'publication':
            expected,
            'work_items':
            work_items,
            'header':
            header,
            'math':
            True,
            'association':
            'same_launch_metadata_object',
            'ownership_status':
            'requires actual saved GCU IR inspection'
        })
    assert kernels[0].hash == kernels[2].hash and kernels[0].hash != kernels[
        1].hash
    assert kernels[0].asm['llir'] == kernels[2].asm['llir']
    assert kernels[0].asm['llir'] != kernels[1].asm['llir']
    (tmp_path / 'receipt.json').write_text(json.dumps(receipts, indent=2))
    monkeypatch.setenv('FLAGPRISM_GCU_DYNAMIC_PUBLISHER', 'unknown')
    session = profiler.start(str(tmp_path / 'rejected'),
                             backend='enflame',
                             hook='instrumentation',
                             observation_request=request)
    try:
        with pytest.raises(ValueError, match='Unknown GCU dynamic publisher'):
            original_vector_math[(2, )](x,
                                        y,
                                        n,
                                        block,
                                        1.,
                                        num_warps=work_items)
    finally:
        profiler.finalize(session)
