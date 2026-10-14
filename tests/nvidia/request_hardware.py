"""Common ObservationRequest lowers recording controls and honest output selection."""
import importlib.util
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(os.environ['METHOD_COMPILER_SOURCE']) / 'python'))
import torch
import triton
import triton.language as tl
import flagtree

source = Path(os.environ['METHOD_SOURCE'])
package = source / 'Profiler/python/flagtree_profiler'
spec = importlib.util.spec_from_file_location(
    'flagtree.profiler',
    package / '__init__.py',
    submodule_search_locations=[str(package)])
profiler = importlib.util.module_from_spec(spec)
sys.modules['flagtree.profiler'] = profiler
spec.loader.exec_module(profiler)
from flagtree.profiler import language as pl
from flagtree.profiler.observations import ObservationRequest

pl.enable_semantic('triton')


@triton.jit
def loop(X, Y, repeats, B: tl.constexpr):
    offset = tl.program_id(0) * B + tl.arange(0, B)
    value = tl.load(X + offset)
    result = tl.full((B, ), 0., tl.float32)
    for iteration in range(repeats):
        pl.enter_scope('body')
        result += value
        pl.exit_scope('body')
    tl.store(Y + offset, result)


output = Path(sys.argv[1])
x = torch.arange(1024, device='cuda', dtype=torch.float32) / 128
y = torch.empty_like(x)
request = ObservationRequest(programs=(0, ), max_events_per_instance=4)
session = profiler.start(str(output),
                         backend='instrumentation',
                         hook='instrumentation',
                         observation_request=request)
compiled = loop[(4, )](x, y, 7, 256, num_warps=4, num_stages=1)
profiler.finalize(session)
torch.testing.assert_close(y.cpu(), x.cpu() * 7, rtol=1e-5, atol=1e-5)
exported = json.loads((output / 'ai/observations.json').read_text())
assert len(exported['observations']) == 4
assert all(record['program'] == 0 and record['duration_ns'] is None
           and record['association_status'] == 'verified'
           for record in exported['observations'])
decoded = exported['captures'][0]['decoded']
assert decoded['selection_stage'] == 'device_program_and_postcapture_site'
assert decoded['collection_scope']['programs'] == [0]
assert len(decoded['losses']) == 4
assert decoded['dropped_records'] == 6, decoded['losses']
assert decoded['output_filtered_intervals'] == 0
assert all(item['capacity_records'] == 8 and item['dropped_records'] == (
    6 if item['program'] == 0 else 0) for item in decoded['losses'])
assert all(item['written_records'] == (14 if item['program'] == 0 else 0)
           for item in decoded['losses'])
assert (output / 'raw/native/capture.hatchet').exists()
print(
    'PASS PUBLIC_REQUEST_CTA0_DEVICE_SELECTION_ZERO_UNSELECTED_COUNTS_AND_OVERFLOW',
    flush=True)
binaries = {compiled.hash}
for program in (1, 99):
    destination = output.with_name(output.name + '-program-' + str(program))
    session = profiler.start(str(destination),
                             backend='instrumentation',
                             hook='instrumentation',
                             observation_request=ObservationRequest(
                                 programs=(program, ),
                                 max_events_per_instance=4))
    compiled = loop[(4, )](x, y, 7, 256, num_warps=4, num_stages=1)
    binaries.add(compiled.hash)
    profiler.finalize(session)
    torch.testing.assert_close(y.cpu(), x.cpu() * 7, rtol=1e-5, atol=1e-5)
    exported = json.loads((destination / 'ai/observations.json').read_text())
    assert len(exported['observations']) == (4 if program < 4 else 0)
    decoded = exported['captures'][0]['decoded']
    assert decoded['dropped_records'] == (6 if program < 4 else 0)
    assert all(
        item['written_records'] == (14 if item['program'] == program else 0)
        for item in decoded['losses'])
assert len(binaries) == 3, binaries
print('PASS DEVICE_SELECTION_CACHE_IDENTITY_AND_NOT_LAUNCHED_PROGRAM_EMPTY',
      flush=True)
