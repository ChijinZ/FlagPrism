import argparse,json,re,subprocess,hashlib
from pathlib import Path
from triton._C.libtriton import llvm
from triton.backends.nvidia.compiler import get_ptxas
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True)
original=Path('/workspace/chijin-timeline-r061-nvidia/runs/compute-fence-v1/output');llvm.init_targets();src=(original/'transformed.ll').read_text()
ptx=llvm.translate_to_asm(src,'nvptx64-nvidia-cuda','sm_120a','+ptx88',['nvptx-mad-wide-opt'],True,False)
ptx=re.sub(r",\s*debug|debug,\s*", "", ptx);(a.output/'modified.ptx').write_text(ptx);(a.output/'plan.json').write_bytes((original/'plan.json').read_bytes())
steps=[]
def run(name,cmd):
 with (a.output/(name+'.stdout')).open('xb') as out,(a.output/(name+'.stderr')).open('xb') as err:r=subprocess.run([str(x) for x in cmd],stdout=out,stderr=err,timeout=40)
 steps.append(dict(name=name,argv=[str(x) for x in cmd],returncode=r.returncode));(a.output/'steps.json').write_text(json.dumps(steps,indent=2))
 if r.returncode:raise RuntimeError(name+' failed')
run('ptxas',[get_ptxas(120).path,'-lineinfo','-v','--gpu-name=sm_120a',a.output/'modified.ptx','-o',a.output/'modified.cubin'])
tool=Path('/workspace/chijin-timeline-r058-nvidia/runs/native-install-v2/output/venv/lib/python3.10/site-packages/nvidia/cu13/bin/nvdisasm')
for name,flags in [('lines',['--print-code','--print-line-info-ptx']),('json',['--emit-json'])]:run(name,[tool,*flags,a.output/'modified.cubin'])
(a.output/'result.json').write_text(json.dumps(dict(status='release_mode_CPU_codegen_only_not_device',files={n:hashlib.sha256((a.output/n).read_bytes()).hexdigest() for n in ['modified.ptx','modified.cubin','lines.stdout','json.stdout']},steps=steps,source_LLVM_sha256=hashlib.sha256(src.encode()).hexdigest(),prototype_tool_reused=True,device_executed=False),indent=2))
