#!/usr/bin/env python3
"""Bounded SDK legality experiment, not a dynamic trace implementation.

Keep ordinary user math in native i32-index/f32 TTIR. Clock i64 is confined to
LLVM Call/Trunc/LShr/Constant; no replacement SDK symbol, no new barrier, no LLVM
text mutation. Test whether the SDK still requires global enable_i64=True.
"""
import argparse, hashlib, json, traceback
from pathlib import Path
import torch
import torch_gcu  # noqa:F401
import triton

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=False)
text = '''module {
 llvm.func @_ZN4tops12global_timerEv() -> i64
 tt.func public @scoped_clock_words(%X: !tt.ptr<f32>, %Y: !tt.ptr<f32>, %T: !tt.ptr<i32>) {
  %range = tt.make_range {start = 0 : i32, end = 128 : i32} : tensor<128xi32>
  %xs = tt.splat %X : !tt.ptr<f32> -> tensor<128x!tt.ptr<f32>>
  %xp = tt.addptr %xs, %range : tensor<128x!tt.ptr<f32>>, tensor<128xi32>
  %x = tt.load %xp : tensor<128x!tt.ptr<f32>>
  %one = arith.constant 1.0 : f32
  %ones = tt.splat %one : f32 -> tensor<128xf32>
  %y = arith.addf %x, %ones : tensor<128xf32>
  %ys = tt.splat %Y : !tt.ptr<f32> -> tensor<128x!tt.ptr<f32>>
  %yp = tt.addptr %ys, %range : tensor<128x!tt.ptr<f32>>, tensor<128xi32>
  tt.store %yp, %y : tensor<128x!tt.ptr<f32>>
  %clock = llvm.call @_ZN4tops12global_timerEv() : () -> i64
  %low = llvm.trunc %clock : i64 to i32
  %shift = llvm.mlir.constant(32 : i64) : i64
  %upper = llvm.lshr %clock, %shift : i64
  %high = llvm.trunc %upper : i64 to i32
  tt.store %T, %low : !tt.ptr<i32>
  %next = arith.constant 1 : i32
  %highptr = tt.addptr %T, %next : !tt.ptr<i32>, i32
  tt.store %highptr, %high : !tt.ptr<i32>
  tt.return
 }
}
'''
ir = a.output / 'clock-math.ttir'
ir.write_text(text)
library = Path('/opt/tops/llvm11/lib/krt/gcu300_api_profile.bc')
result = {
    'kind':
    'bounded_legality_probe',
    'requested_enable_i64':
    False,
    'primitive':
    '_ZN4tops12global_timerEv',
    'library_sha256':
    hashlib.sha256(library.read_bytes()).hexdigest(),
    'clock_frequency_verified':
    False,
    'user_math':
    'i32 vector indices; FP32 x+1; one logical program and one work-item; no new synchronization'
}
try:
    target = triton.runtime.driver.active.get_current_target()
    kernel = triton.compile(str(ir),
                            target=target,
                            options={
                                'num_warps':
                                1,
                                'num_stages':
                                1,
                                'enable_i64':
                                False,
                                'extern_libs':
                                (('sdk_readonly_global_timer', str(library)), )
                            })
    metadata = kernel.metadata._asdict()
    metadata.pop('target', None)
    result['compiled_metadata'] = metadata
    assert metadata['enable_i64'] is False
    cpu = torch.arange(128, dtype=torch.float32, device='cpu')
    x = cpu.to('gcu')
    y = torch.empty_like(x)
    ticks = torch.empty((2, ), dtype=torch.int32, device='gcu')
    samples = []
    for _ in range(8):
        kernel[(1, 1, 1)](x, y, ticks)
        torch.gcu.synchronize()
        torch.testing.assert_close(y.cpu(), cpu + 1, rtol=0, atol=0)
        words = [int(v) & 0xffffffff for v in ticks.cpu().tolist()]
        value = words[0] | (words[1] << 32)
        assert 0 < value < (1 << 46)
        samples.append({'words': words, 'raw46_ticks': value})
    assert all(b['raw46_ticks'] > a['raw46_ticks']
               for a, b in zip(samples, samples[1:]))
    result.update(status='passed', samples=samples, binary_id=kernel.hash)
    for key, value in kernel.asm.items():
        if isinstance(value, (str, bytes)):
            (a.output / key
             ).write_bytes(value.encode() if isinstance(value, str) else value)
except Exception as error:
    result.update(status='failed',
                  error=repr(error),
                  traceback=traceback.format_exc())
    traceback.print_exc()
finally:
    (a.output / 'result.json').write_text(
        json.dumps(result, indent=2, default=str))
    print(json.dumps(result, default=str))
raise SystemExit(0 if result['status'] == 'passed' else 1)
