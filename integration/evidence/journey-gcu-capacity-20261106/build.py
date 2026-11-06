import hashlib,json,shlex,subprocess
from pathlib import Path
root=Path('/root/chijin-journey-capacity-20261106')
source=root/'source'; output=root/'output'; output.mkdir(exist_ok=True)
old=Path('/tmp/chijin-timeline-r051-source-build-v1/work')
steps=[]
def run(name,argv,timeout=300,cwd=None):
    with (output/(name+'.log')).open('w') as log:
        result=subprocess.run(argv,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
    steps.append(dict(name=name,argv=argv,returncode=result.returncode))
    (output/'steps.json').write_text(json.dumps(steps,indent=2))
    if result.returncode: raise RuntimeError(name+' failed; inspect '+str(output/(name+'.log')))
commands=subprocess.check_output(['ninja','-C',str(old/'build'),'-t','commands','flagtree_debugger_native'],text=True).splitlines()
(output/'original-runtime-commands.txt').write_text('\n'.join(commands)+'\n')
def remap(token):
    return token.replace(str(old/'FlagPrism'),str(source))
objects=[]
for line in commands:
    words=shlex.split(line)
    if '-c' not in words: continue
    words=[remap(x) for x in words]
    for flag in ('-o','-MF','-MT'):
        if flag in words:
            index=words.index(flag)+1
            words[index]=str(output/'runtime-build'/words[index])
            Path(words[index]).parent.mkdir(parents=True,exist_ok=True)
    objects.append(words[words.index('-o')+1])
    run('compile-'+Path(words[-1]).stem,words)
if len(objects)!=8: raise RuntimeError('Expected complete eight-source runtime target')
link=next(x for x in commands if ' -shared ' in x)
link_words=shlex.split(link.split(' && ')[1])
for i,word in enumerate(link_words):
    if word.endswith('.cpp.o'): link_words[i]=str(output/'runtime-build'/remap(word))
    if word.startswith('-Wl,--dependency-file='):
        link_words[i]='-Wl,--dependency-file='+str(output/'runtime-build/link.d')
    if word.startswith(str(old/'native')): link_words[i]=word.replace(str(old/'native'),str(output/'native'))
native=Path(link_words[link_words.index('-o')+1]);native.parent.mkdir(parents=True,exist_ok=True)
run('link-runtime',link_words)
build=output/'recorder-build'
run('configure-recorder',['cmake','-S',str(source/'Debugger/tools/gcu-timeline'),'-B',str(build),'-G','Ninja','-DCMAKE_BUILD_TYPE=Release','-DMLIR_DIR=/opt/flagtree-llvm/llvm-fc83c68-gcc9-x64/lib/cmake/mlir'])
run('build-recorder',['cmake','--build',str(build),'--target','flagprism-gcu-timeline','--parallel','2'],600)
tool=build/'flagprism-gcu-timeline'
python='/tmp/chijin-timeline-r098-gcu/runs/normal-install-v3/output/venv/bin/python'
run('native-preservation',[python,'-I',str(source/'Debugger/test/gcu_execution_preservation.py'),'--tool',str(tool)],120)
(output/'build-result.json').write_text(json.dumps(dict(source_commit='44f06baa',device_executed=False,native=str(native),tool=str(tool),sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (native,tool)}),indent=2))
print('BUILD_AND_NATIVE_TESTS_PASSED',output)
