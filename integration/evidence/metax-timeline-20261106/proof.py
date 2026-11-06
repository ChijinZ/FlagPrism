"""Compiler/launcher ABI proof only; not the public automatic backend."""
import json,subprocess
from pathlib import Path
import torch,triton
import triton.language as tl
from triton.backends.metax.compiler import MACABackend
from triton.runtime import _allocation
root=Path('/workspace/metax-detailed-20261106/proof');root.mkdir(parents=True,exist_ok=True)
ordinary=MACABackend.make_llir
manifest=None
buf=None

def transformed(src,metadata,options,capability):
 global manifest
 text=ordinary(src,metadata,options,capability)
 (root/'ordinary.ll').write_text(text)
 subprocess.run(['/workspace/metax-detailed-20261106/tools/metax-timeline',str(root/'ordinary.ll'),'--flagtree-profile-abi=1','--compact-programs','--actors=1','--capacity=512','--max-sites=8','--output='+str(root/'instrumented.ll'),'--manifest='+str(root/'manifest.json')],check=True)
 manifest=json.loads((root/'manifest.json').read_text())
 metadata['profile_scratch_size']=manifest['segment_words']*8
 metadata['profile_scratch_align']=8
 return (root/'instrumented.ll').read_text()
MACABackend.make_llir=staticmethod(transformed)
class Allocator:
 def __call__(self,size,alignment,stream):
  global buf
  buf=torch.zeros(2*manifest['segment_words'],device='cuda',dtype=torch.int64)
  return buf
_allocation.set_profile_allocator(Allocator())
@triton.jit
def metax_proof_vector(X,Y,N:tl.constexpr):
 o=tl.program_id(0)*32+tl.arange(0,32)
 v=tl.load(X+o,o<N,0)
 tl.store(Y+o,v*2+1,o<N)
x=torch.arange(256,device='cuda',dtype=torch.float32);y=torch.empty_like(x)
k=metax_proof_vector[(8,)](x,y,256);torch.cuda.synchronize()
torch.testing.assert_close(y,x*2+1)
raw=buf.cpu();(root/'raw.bin').write_bytes(raw.numpy().tobytes())
print('header0',raw[:6].tolist());print('header1',raw[manifest['segment_words']:manifest['segment_words']+6].tolist());print('sites',len(manifest['sites']));print('correct',True)
