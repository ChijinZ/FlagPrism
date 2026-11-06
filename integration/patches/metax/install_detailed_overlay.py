"""Assemble an isolated MetaX detailed package from the matching native base.

The base is built using the recorded native build recipe. Existing installed
FlagTree, Torch, native libraries and other backend environments are preserved.
"""
import argparse,hashlib,json,os,shlex,shutil,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--base-python',type=Path,required=True)
p.add_argument('--llvm-root',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--compiler',default='g++')
a=p.parse_args();source=Path(__file__).resolve().parents[3];output=a.output.resolve()
if output.exists():raise ValueError('Choose a fresh output directory')
base=a.base_python.resolve(strict=True)
for component in ('profiler','debugger'):
    if not list((base/'flagtree'/component).glob('*_native*.so')):raise ValueError('Matching native base missing '+component)
output.mkdir(parents=True)
shutil.copytree(base,output/'python',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for name,relative in [('profiler','Profiler/python/flagtree_profiler'),('debugger','Debugger/python/flagtree_debugger')]:
    shutil.copytree(source/relative,output/'python/flagtree'/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
subprocess.run([sys.executable,str(source/'integration/patches/metax/build_metax_timeline_tool.py'),'--llvm-root',str(a.llvm_root.resolve()),'--compiler',a.compiler,'--output',str(output/'tool-build')],check=True)
tool=output/'python/flagtree/profiler/_bin/metax-timeline';tool.parent.mkdir(parents=True,exist_ok=True)
shutil.copy2(output/'tool-build/metax-timeline',tool)
activate=output/'activate.sh'
activate.write_text('export FLAGTREE_BACKEND=metax\nexport FLAGPRISM_BACKEND=metax\nexport FLAGPRISM_SOURCE_DIR='+shlex.quote(str(source))+'\nexport PYTHONPATH='+shlex.quote(str(output/'python'))+'${PYTHONPATH:+:$PYTHONPATH}\n')
receipt={'source':str(source),'base_python':str(base),'package':str(output/'python'),'activation':str(activate),'native':{str(f.relative_to(output)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (output/'python').rglob('*.so')},'tool_sha256':hashlib.sha256(tool.read_bytes()).hexdigest()}
(output/'install-receipt.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt,indent=2))
