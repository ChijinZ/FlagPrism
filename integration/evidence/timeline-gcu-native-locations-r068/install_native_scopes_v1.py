"""Build the changed standalone GCU recorder, reuse unchanged core/runtime, install wheel."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True)
payload = Path(__file__).parent
config = json.loads((payload/'config.json').read_text())
backend = config['backend']
source = payload/'source'
parent = args.output/'FlagTree'
native = args.output/'native'
build = args.output/'build'
env = dict(os.environ)
env.pop('PYTHONPATH', None)
env['PATH']=str(Path(sys.executable).parent)+':/usr/lib/llvm-15/bin:'+env['PATH']
env.update(TORCH_DEVICE_BACKEND_AUTOLOAD='0', USE_FLAGCX='OFF', USE_FLIR='OFF', USE_FLAGPRISM='OFF', TRITON_OFFLINE_BUILD='ON')
if backend == 'nvidia':
    env.pop('FLAGTREE_BACKEND', None)
else:
    env['FLAGTREE_BACKEND'] = backend
steps = []

def run(name, command, cwd=None):
    command = [str(x) for x in command]
    with (args.output/(name+'.log')).open('xb') as log:
        child = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
        fields = Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')',1)[1].split()
        item = dict(name=name, argv=command, pid=child.pid, startticks=int(fields[19]))
        steps.append(item)
        (args.output/'steps.json').write_text(json.dumps(steps, indent=2))
        item['returncode'] = child.wait()
    (args.output/'steps.json').write_text(json.dumps(steps, indent=2))
    if item['returncode']:
        raise RuntimeError(name+' failed; see '+str(args.output/(name+'.log')))

# All shared runtime/core native sources are unchanged. Only the standalone
# GCU recorder is rebuilt; the four other-backend files are not its inputs.
old_source = Path(config['installed_source'])
changed, checked = [], []
recorder_changes = {
 'Debugger/include/Debugger/Instrumentation/GcuTimeline.h',
 'Debugger/lib/Instrumentation/GcuTimeline.cpp',
 'Debugger/lib/Instrumentation/GcuDebugScopes.cpp',
 'Debugger/tools/gcu-timeline/main.cpp',
 'Debugger/tools/gcu-timeline/CMakeLists.txt',
}
other_backend = {'Profiler/Dialect/tools/late-timeline/late-timeline.cpp',
 'Profiler/llvm/AscendLateObserver.cpp','Profiler/llvm/AscendNativeTimeline.h',
 'Profiler/llvm/AscendTimeline.h'}
for component in ('Debugger', 'Profiler'):
 for path in (source/component).rglob('*'):
  if not path.is_file() or '/test/' in str(path) or not (path.suffix in ('.cpp','.h','.hpp','.inc','.td','.cmake') or path.name == 'CMakeLists.txt'):continue
  name = str(path.relative_to(source));previous=old_source/name
  if not previous.is_file() or previous.read_bytes()!=path.read_bytes():
   if name not in recorder_changes | other_backend:raise RuntimeError('Unrebuilt native input changed: '+name)
   changed.append(name)
  else:checked.append(name)
(args.output/'native-source-inputs.json').write_text(json.dumps(dict(changed=changed, rebuilt_recorder_inputs=sorted(recorder_changes), excluded_other_backend_inputs=sorted(other_backend), unchanged_native_sources=checked, compiler=config['core'], reused_runtime=str(Path(config['native'])/'flagtree/debugger')),indent=2))

# Preserve the actually patched parent and external dependency trees.
def ignore(directory, names):
    return [n for n in names if n in ('.git','build','dist','__pycache__','AscendNPU-IR','flir') or n.endswith('.egg-info')]
old_parent = Path(config['parent'])
shutil.copytree(old_parent, parent, symlinks=True, ignore=ignore)
run('git-init', ['git','init','-q'], parent)
run('git-parent', ['git','fetch','--update-shallow',str(old_parent),'HEAD'], parent)
run('git-identity', ['git','reset','--mixed','FETCH_HEAD'], parent)
for name in ['third_party/ascend/AscendNPU-IR','third_party/flir']:
    original, target = old_parent/name, parent/name
    if original.exists() and not target.exists():
        target.symlink_to(original, target_is_directory=True)
alias = parent/'third_party/FlagPrism'
if alias.is_symlink():
    alias.unlink()
elif alias.exists():
    raise RuntimeError('Unexpected non-symlink component integration')
alias.symlink_to(source, target_is_directory=True)
# Apply the maintained patch to its exact public baseline in this owned copy.
for name in ('third_party/enflame/backend/compiler.py',
             'third_party/enflame/triton_gcu/triton_gcu300/lib/triton_gcu300_core.cpp',
             'third_party/enflame/triton_gcu/triton_gcu400/lib/triton_gcu400_core.cpp'):
 (parent/name).write_bytes(subprocess.check_output(['git','-C',str(old_parent),'show','add842f2c495a3974944733ea6b07ff6b5bfcee8:'+name],timeout=20))
run('current-parent-patch', ['git','apply',source/'integration/patches/enflame/flagtree-source.patch'], parent)
shutil.copytree(config['native'], native, symlinks=True, ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
run('configure-recorder', ['cmake','-S',source/'Debugger/tools/gcu-timeline','-B',build,'-G','Ninja','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_EXPORT_COMPILE_COMMANDS=ON','-DMLIR_DIR=/opt/flagtree-llvm/llvm-fc83c68-gcc9-x64/lib/cmake/mlir','-DFLAGPRISM_PYTHON_DIR='+str(native)])
run('build-recorder', ['cmake','--build',build,'--target','flagprism-gcu-timeline','--parallel','2'])
run('native-unit', [sys.executable,'-I',source/'Debugger/test/gcu_native_debug_scopes.py','--tool',native/'flagtree/debugger/_bin/gcu-timeline'])
# The core/runtime/backend libraries are unchanged inputs; the standalone tool
# was actually rebuilt above. The wheel assembler verifies packaged bytes.
command = [sys.executable,'-I',source/config['assembler'],'--flagtree',parent,'--component',source,'--native-python',native,'--core-library',config['core'],'--output',args.output/'wheel']
if backend == 'nvidia':
    command += ['--backend-build',config['backend_build'],'--late-timeline-tool',config['tool']]
elif backend == 'enflame':
    command += ['--backend-build',config['backend_build']]
else:
    command += ['--plugin',config['tool']]
run('assemble', command)
wheels = list((args.output/'wheel/dist').glob('*.whl'))
if len(wheels) != 1:
    raise RuntimeError('Expected one wheel')
venv = args.output/'venv'
run('venv', [sys.executable,'-m','venv','--without-pip',venv])
python = venv/'bin/python'
run('install', [sys.executable,'-I','-m','pip','--python',python,'install','--no-index','--no-deps',wheels[0]])
site = next((venv/'lib').glob('python*/site-packages'))
dependency_sites=list(dict.fromkeys(config['dependency_sites']+[p for p in sys.path if p.endswith(('site-packages','dist-packages'))])); (site/'vendor-dependencies.pth').write_text('\n'.join(dependency_sites)+'\n')
with zipfile.ZipFile(wheels[0]) as archive:
    checked = 0
    for name in archive.namelist():
        if name.startswith(('flagtree/','triton/')) and not name.endswith('/'):
            if (site/name).read_bytes() != archive.read(name):
                raise RuntimeError('Installed wheel mismatch '+name)
            checked += 1
if backend == 'nvidia':
    run('install-disassembler', [sys.executable, '-I', '-m', 'pip', '--python', python, 'install', '--no-index', '--no-deps', '--ignore-installed', config['nvdisasm_wheel']])
if backend == 'enflame':
    run('guard-binding-feature', [python,'-I','-c',"from flagtree.debugger.native import runtime_binding; m=runtime_binding(); v=getattr(m,'GCU_TIMELINE_ALLOCATION_GUARD_VERSION',None); print(v); raise SystemExit(0 if v==1 else 1)"])
run('installed-import', [python,'-I','-c',"from flagtree.debugger.native import runtime_binding; import flagtree.profiler; print(runtime_binding().__file__); print(flagtree.profiler.__file__)"])
result = dict(status='GCU_native_clock_locations_installed_pending_device', backend=backend, source_commit=config['commit'], source=str(source), python=str(python), native=str(native), installed_members=checked, wheel=str(wheels[0]), wheel_sha256=hashlib.sha256(wheels[0].read_bytes()).hexdigest(), unchanged_compiler=config['core'], rebuilt_recorder=str(native/'flagtree/debugger/_bin/gcu-timeline'), steps=steps)
(args.output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
