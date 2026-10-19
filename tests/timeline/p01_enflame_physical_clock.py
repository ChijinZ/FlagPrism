"""Actual installed GCU sampler and SDK helper-cache contracts.

Run inside the GCU Docker. This starts only owned anchor kernels and SDK helper
compilations; it does not replay user applications or qualify async dependencies.
Cache corruption is confined to the newly created output directory.
"""
import argparse
import json
import pathlib
import time

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=pathlib.Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=False)
from flagtree.debugger.gcu_clock import identity_library
from flagtree.profiler.timeline_enflame_clock import EnflameClockAnchors
from flagtree.profiler.timeline_calibration import empirical_period_bounds

cache = a.output / 'cache-test'
cold = identity_library(cache_root=cache)
warm = identity_library(cache_root=cache)
if cold != warm:
    raise RuntimeError('Clock helper cache changed an identical source/tool')
# A completed temporary build left behind before atomic directory publication
# must not poison the next build or alter its reproducible bitcode bytes.
artifact = pathlib.Path(cold['file']).parent
interrupted = artifact.parent / 'build-interrupted'
artifact.rename(interrupted)
recovered = identity_library(cache_root=cache)
if recovered['sha256'] != cold['sha256']:
    raise RuntimeError('Atomic helper retry did not reproduce bitcode')
binary = pathlib.Path(recovered['file'])
original = binary.read_bytes()
binary.write_bytes(bytes([original[0] ^ 1]) + original[1:])
rejected = False
try:
    identity_library(cache_root=cache)
except ValueError:
    rejected = True
if not rejected or binary.read_bytes() == original:
    raise RuntimeError('Corrupt helper was accepted or erased')
# Actual sampler uses a separate healthy default namespace, not the corrupt
# deliberately isolated cache above.
sampler = EnflameClockAnchors()
initial = json.loads(json.dumps(sampler.evidence))
time.sleep(.12)
closed = sampler.finish()
if sampler.finish() != closed:
    raise RuntimeError('Closed calibration replayed actual anchors')
ids = set.intersection(*[{r['full_sipinfo']
                          for r in row['domains']}
                         for row in closed['training'] + closed['heldout']])
if len(ids) < 2:
    raise RuntimeError(
        'Physical sampler did not observe distinct hardware identities')
checks = []
for identity in sorted(ids):
    rows = []
    for sample in closed['training'] + closed['heldout']:
        actual = next(r for r in sample['domains']
                      if r['full_sipinfo'] == identity)
        rows.append(
            dict(raw_tick=actual['raw_tick'],
                 before_ns=sample['before_ns'],
                 after_ns=sample['after_ns']))
    lo, hi = empirical_period_bounds(rows, bits=46)
    checks.append(
        dict(full_sipinfo=identity,
             period_ns=[[lo.numerator, lo.denominator],
                        [hi.numerator, hi.denominator]]))
(a.output / 'initial.json').write_text(json.dumps(initial, indent=2))
(a.output / 'closed.json').write_text(json.dumps(closed, indent=2))
(a.output / 'result.json').write_text(
    json.dumps(dict(
        status=
        'actual_installed_full_identity_sampler_and_SDK_cache_contracts_passed_not_async_qualification',
        identities=len(ids),
        checks=checks,
        helper_sha256=cold['sha256'],
        corruption_rejected=True,
        atomic_interruption_recovered=True,
        closed_retry_replayed=False),
               indent=2))
