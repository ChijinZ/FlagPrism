"""Run inside Docker after restoration; never patch the user's main checkout.

The exported handoff patch predates cache-key support. This idempotent restore
adds the exact later callback on the pinned independent FlagTree worktree and
exports its complete resulting diff plus dependency identities.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

BASELINE='0364ed4bc39d1dfae483741ec272298297fa5bda'
NPU_IR_BASELINE='4c30492166f6cfbc5fa0c81a72f53630b9a3e6a9'
root=Path('/tmp/flagprism-method-ascend/FlagTree')
if root.resolve()==Path('/workspace/FlagTree').resolve():
    raise RuntimeError('refusing to patch the user main checkout')
artifacts=Path('/tmp/flagprism-method-ascend/recovery')
patch=Path(sys.argv[1])
if subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()!=BASELINE:
    raise RuntimeError('refusing to modify an unpinned FlagTree checkout')
bridge=root/'python/flagtree/_flagprism.py';backend=root/'third_party/ascend/backend/compiler.py'
if 'def prepare_compiler_driver(' not in bridge.read_text():
    subprocess.run(['git','-C',str(root),'apply','--check',str(patch.resolve())],check=True)
    subprocess.run(['git','-C',str(root),'apply',str(patch.resolve())],check=True)
source=bridge.read_text()
if 'def compiler_driver_cache_key(' not in source:
    source+='''\n\ndef compiler_driver_cache_key() -> str:
    """Components identify codegen-affecting driver configuration before caching."""
    values = []
    for callback in _registered_callbacks("compiler_driver_cache_key"):
        values.append(str(callback()))
    return "|".join(values)
'''
    bridge.write_text(source)
source=backend.read_text()
old='        key = "_".join([key, get_cann_version_file_hash()])'
new='        key = "_".join([key, get_cann_version_file_hash(), _flagprism.compiler_driver_cache_key()])'
if new not in source:
    if source.count(old)!=1:raise RuntimeError('Ascend compiler cache location is missing or ambiguous')
    backend.write_text(source.replace(old,new,1))
if backend.read_text().count('_flagprism.prepare_compiler_driver(')!=2:
    raise RuntimeError('both supported Ascend compiler driver paths were not patched')
artifacts.mkdir(parents=True,exist_ok=True)
full=subprocess.check_output(['git','-C',str(root),'diff','--binary','HEAD','--','python/flagtree/_flagprism.py','third_party/ascend/backend/compiler.py'])
(artifacts/'flagtree-driver-handoff-complete.patch').write_bytes(full)
manifest={'baseline':BASELINE,'initial_patch_sha256':hashlib.sha256(patch.read_bytes()).hexdigest(),'complete_patch_sha256':hashlib.sha256(full).hexdigest(),'files':{str(path.relative_to(root)):hashlib.sha256(path.read_bytes()).hexdigest() for path in (bridge,backend)},'dependencies':{}}
for name,path in [('AscendNPU-IR',root/'third_party/ascend/AscendNPU-IR'),('FLIR',root/'third_party/flir')]:
    dependency_head=subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip()
    if name=='AscendNPU-IR' and dependency_head!=NPU_IR_BASELINE:
        raise RuntimeError('AscendNPU-IR does not match the declared dependency pin')
    dirty=subprocess.check_output(['git','-C',str(path),'status','--porcelain','--untracked-files=no'],text=True).strip()
    if dirty:
        raise RuntimeError(f'{name} has tracked modifications; a HEAD alone cannot reproduce it')
    manifest['dependencies'][name]=dependency_head
manifest['validation_status']='export_only_build_and_runtime_pending'
manifest['combined_patch_files']=['python/flagtree/_flagprism.py','third_party/ascend/backend/compiler.py']
(artifacts/'core-handoff.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
