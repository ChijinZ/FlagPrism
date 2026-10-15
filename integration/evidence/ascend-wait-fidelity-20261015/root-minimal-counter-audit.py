"""Independent offline check of the retained minimal two-read control."""
import hashlib
import json
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
BASE = HERE / 'root-small-extracted'
P = BASE / 'round2/minimal-counter-gpu'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
r = json.loads((P/'result.json').read_text())
raw = (P/'all-storage-int64.bin').read_bytes()
assert len(raw) == r['guarded_allocation_bytes'] == 17408
words = struct.unpack('<'+'q'*(len(raw)//8), raw)
assert len(r['raw_pairs']) == r['limit_calls'] == 64
for index, pair in enumerate(r['raw_pairs']):
    row = words[index*34:(index+1)*34]
    assert len(row) == 34 and all(v == -564738291 for v in row[:16]+row[18:])
    assert pair['call'] == index and row[16] == pair['first_tick'] and row[17] == pair['second_tick']
    assert row[17]-row[16] == pair['delta_ticks'] == 0
    assert pair['valid_nonnegative'] is True and pair['negative_reason'] is None
assert all(a['first_tick']<b['first_tick'] for a,b in zip(r['raw_pairs'],r['raw_pairs'][1:]))
assert r['observer'] is False and r['added_completion_barriers_in_kernel'] is False
launch = r['actual_public_launch']
assert r['grid'] == [1,1,1] and launch['block_dim'] == 1 and launch['mix_ratio'] == 0 and launch['task_type'] == 'AIV'
assert launch['registration_magic'] == 'RT_DEV_BINARY_MAGIC_ELF_AIVEC'
assert sha(P/'actual-public-launcher.cpp') == r['actual_launcher_sha256']
cpu = BASE/'round2/counter-inline-cpu'
assert sha(cpu/'compiled-npubin') == r['compiled_binary_sha256']
receipt = json.loads((cpu/'object-replay-receipt.json').read_text())
assert receipt['cpu_only'] is True and receipt['returncode'] == 0
assert sha(cpu/'isolated-original-argv-replay.o') == receipt['actual_replayed_object_sha256'] == receipt['original_object_receipt_sha256']
assert receipt['input_sha256'] == r['original_input_sha256']
result = {'status':'passed', 'scope':'offline original raw storage/pair/canary/image and replay-object integrity, not a fresh hardware run',
          'calls':64,'raw_storage_bytes':len(raw),'zero_tick_pairs':64,'distinct_monotonically_advancing_start_ticks':True,
          'all_exact_declared_canaries':True,'actual_gpu_image_sha256':r['compiled_binary_sha256'],
          'cpu_replayed_object_matches_original_receipt':True,'archive_sha256':sha(HERE/'round2-final-small-proof-r2.tgz'),
          'limits':['Original LLVM has two side-effect counter reads; device-side -S was rejected, so adjacent final-machine instructions are not certified.',
                    'This minimal source control does not bound fusion-wait perturbation or establish shared actor/native epochs.']}
(HERE/'root-minimal-counter-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
