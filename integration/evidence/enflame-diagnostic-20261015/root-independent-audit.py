"""Read-only offline audit, independent of profiler decoders and audit summaries."""
import argparse
import ast
import base64
import collections
import hashlib
import json
import re
from pathlib import Path
import statistics
import struct

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--evidence-dir', type=Path, default=Path(__file__).resolve().parent)
parser.add_argument('--source-root', type=Path, default=Path.cwd() / 'FlagPrism-method')
args = parser.parse_args()
HERE = args.evidence_dir.resolve()
BASE = HERE / 'root-extracted'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
counts = {'bundle_files': 0, 'raw_buffers': 0, 'raw_records': 0, 'native_samples': 0}
for p in BASE.rglob('manifest.json'):
    m = json.loads(p.read_text())
    for name, expected in m['files'].items():
        q = Path(name)
        assert not q.is_absolute() and '..' not in q.parts
        f = p.parent / q
        assert f.is_file() and f.stat().st_size == expected['bytes'] and sha(f) == expected['sha256'], str(f)
        counts['bundle_files'] += 1
for p in BASE.glob('i3-evidence/round2-softmax/w?/*0/bundle/ai/observations.json'):
    d = json.loads(p.read_text())
    assert len(d['captures']) == len(d['observations']) == 1
    c, = d['captures']; e, = d['observations']
    raw = base64.b64decode(c['raw_base64'], validate=True)
    assert hashlib.sha256(raw).hexdigest() == c['raw_sha256']
    h = struct.unpack_from('<8I', raw)
    assert h == (1, 64, 0, 0, 64, 4128, 1, 0)
    kind, reserved, site, program, start, end, duration, actor, sequence, attempted, tag = struct.unpack_from('<HHIQQQQIIQQ', raw, 32)
    assert (kind, reserved, site, program, actor, sequence, attempted, tag) == (7, 0, 29, 0, 0, 0, 0, 0x465044594e563031)
    assert e['start_tick'] == start and e['end_tick'] == end and e['duration_ticks'] == duration == end - start
    assert e['association_status'] == 'verified' and e['invocation_id'] == 'launch-1'
    assert e['duration_ns'] is None and e['relative_start_ns'] is None
    x = json.loads((p.parent / 'execution.json').read_text())['binaries'][0]['mapping']
    k = collections.Counter(v['kind'] for v in x['sites'])
    w = 4 if '/w4/' in str(p) else 1
    metadata = json.loads((p.parents[2] / 'compiled-metadata.json').read_text())
    assert metadata['enable_i64'] is False and metadata['num_warps'] == w
    assert x['work_item_count'] == w and k['barrier'] == (2 if w == 4 else 0)
    assert k['partial_exchange_storage'] == (10 if w == 4 else 0)
    counts['raw_buffers'] += 1; counts['raw_records'] += 1
original_audit = json.loads((HERE / 'retained-controls-audit.json').read_text())
medians = {}
for worker in original_audit['historical_native_controls']:
    w = worker['work_items']; medians[w] = []
    for batch in worker['batches']:
        p = BASE / f"round2-offline-study/native/b{batch['batch']}-w{w}"
        result = json.loads((p / 'result.json').read_text())
        assert sha(p / 'result.json') == batch['result_sha256']
        assert result['phase'] == 'native' and result['measurement']['launch_count'] == 30
        assert re.search(r'\benable_i64=False\b', result['compiled_metadata'])
        assert result['input_hashes'] == original_audit['canonical_input_hashes']
        assert result['requested_compile_config'] == batch['config']
        ep = p / 'profile/ai/events.jsonl'
        assert sha(ep) == batch['native_event_file_sha256']
        events = [json.loads(s) for s in ep.read_text().splitlines()]
        kernels = [e for e in events if e['kind'] == 'kernel']
        values = [e['duration_us'] for e in kernels]
        assert len(values) == 30 and values == batch['native_source_observer_disabled_samples_us']
        assert statistics.median(values) == batch['median_us']
        for stage, expected in batch['asm_sha256'].items(): assert sha(p / 'asm' / stage) == expected
        assert 'global_timer' not in (p / 'asm/llir').read_text()
        medians[w].append(statistics.median(values)); counts['native_samples'] += 30
old = next(BASE.glob('round2-offline-study/native/b0-w4/profile/ai/sources/920e*.py'))
current = args.source_root / 'Profiler/test/fixtures/enflame_method/kernels.py'
def rows_ast(p):
    return ast.dump(next(x for x in ast.parse(p.read_text()).body if isinstance(x, ast.FunctionDef) and x.name == 'rows'), include_attributes=False)
assert rows_ast(old) == rows_ast(current)
out = {'status': 'passed', 'scope': 'independent read-only stored-byte/static/output analysis, no new math or hardware experiment', 'archive_sha256': sha(HERE / 'diagnostic-raw-evidence.tar.gz'), 'skipped_absolute_pytest_links': 2, **counts, 'rows_AST_equal': True, 'native_controls_and_current_enable_i64': False, 'medians_us': medians, 'w4_to_w1_ratios': [a / b for a, b in zip(medians[4], medians[1])], 'limits': ['Old90samples/config retain historical nativecollector-on/sourceobserver-off context, not final-source performance.', 'Static ownership is not measured utilization; no exclusive barrier cost or shared clocks inferred.']}
(HERE / 'root-independent-audit.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps(out, indent=2))
