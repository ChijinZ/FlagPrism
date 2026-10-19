"""Package Python-only changes, explicitly reuse matched native/compiler inputs."""
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

# Native sources must match the actual reused installation. A GCU-only
# standalone recorder source is not a native input for NVIDIA/Ascend wheels.
old_source = Path(config['installed_source'])
checked_native_sources = []
run('actual-late-native-build',[sys.executable,'-I',source/'integration/patches/nvidia/build_late_timeline_tool.py','--llvm-root','/workspace/cache/triton/.triton/llvm/llvm-f6ded0be-ubuntu-x64','--output',args.output/'late-native','--source',source/'Profiler/Dialect/tools/late-timeline/late-timeline.cpp','--deadline-module',source/'Profiler/python/flagtree_profiler/_deadline.py'])
late_receipt=json.loads((args.output/'late-native/build-receipt.json').read_text())
late_source=source/'Profiler/Dialect/tools/late-timeline/late-timeline.cpp'
if late_receipt['returncode']!=0 or late_receipt['source_sha256']!=hashlib.sha256(late_source.read_bytes()).hexdigest():raise RuntimeError('Actual new standalone build does not bind current source')
config['tool']=str(args.output/'late-native/late-timeline')
if late_receipt['executable_sha256']!=hashlib.sha256(Path(config['tool']).read_bytes()).hexdigest():raise RuntimeError('New native tool changed')
separate_sources=[]
for directory in ['Debugger', 'Profiler']:
    for path in (source/directory).rglob('*'):
        if not path.is_file() or not (path.suffix in ('.cpp','.h','.hpp','.inc','.td','.cmake') or path.name=='CMakeLists.txt'):
            continue
        name = str(path.relative_to(source))
        if backend != 'nvidia' and name == 'Profiler/Dialect/tools/late-timeline/late-timeline.cpp':
            continue
        if backend != 'enflame' and name == 'Debugger/lib/Instrumentation/GcuTimeline.cpp':
            continue
        # Ascend's standalone LLVM plugin is built outside the NVIDIA core.
        # The changed NVIDIA standalone source has its new build receipt above.
        if name.startswith('Profiler/llvm/') or name == 'Profiler/Dialect/tools/late-timeline/late-timeline.cpp':
            separate_sources.append(dict(path=name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),reason='Ascend standalone plugin is not NVIDIA build input' if name.startswith('Profiler/llvm/') else 'matching new standalone build'))
            continue
        previous = old_source/name
        if not previous.is_file() or path.read_bytes() != previous.read_bytes():
            raise RuntimeError('Changed native source cannot reuse old objects: '+name)
        checked_native_sources.append(name)
(args.output/'native-source-reuse.json').write_text(json.dumps(dict(
    reused_native=config['native'], compiler=config['core'], recorder=config.get('tool'),
    unchanged_sources=checked_native_sources,separate_inputs=separate_sources,new_late_build_receipt=late_receipt),indent=2))

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
shutil.copytree(config['native'], native, symlinks=True, ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
# Native compiler and standalone recorder are unchanged inputs, never relabelled
# as rebuilt. Wheel assemblers independently check packaged native bytes.
command = [sys.executable,'-I',source/config['assembler'],'--flagtree',parent,'--component',source,'--native-python',native,'--core-library',config['core'],'--output',args.output/'wheel']
if backend == 'nvidia':
    command += ['--backend-build',config['backend_build'],'--late-timeline-tool',config['tool']]
elif backend == 'enflame':
    command += ['--backend-build', config['backend_build']]
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
run('installed-import', [python,'-I','-c',"from flagtree.debugger.native import runtime_binding; import flagtree.profiler; print(runtime_binding().__file__); print(flagtree.profiler.__file__)"])
result = dict(status='wheel_installed_new_late_tool_other_native_reused_pending_device', backend=backend, source_commit=config['commit'], source=str(source), python=str(python), native=str(native), installed_members=checked, wheel=str(wheels[0]), wheel_sha256=hashlib.sha256(wheels[0].read_bytes()).hexdigest(), unchanged_compiler=config['core'], unchanged_recorder=config.get('tool'), steps=steps)
(args.output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
