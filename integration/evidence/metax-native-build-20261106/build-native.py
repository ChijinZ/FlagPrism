import concurrent.futures,hashlib,json,shlex,shutil,subprocess,sys
from pathlib import Path
root=Path('/root/chijin-metax-detailed-20261106/base');source=root/'source';out=root/'output';out.mkdir(exist_ok=True)
oldsource='/workspace/FlagPrism';oldbuild=Path('/workspace/FlagTree/build/cmake.linux-x86_64-cpython-3.12')
commands=subprocess.check_output(['ninja','-C',str(oldbuild),'-t','commands','flagtree_profiler_native','flagtree_debugger_native'],text=True).splitlines()
(out/'original-commands.txt').write_text('\n'.join(commands)+'\n')
objectmap={};compiles=[];links=[];steps=[]
def remap(x):return x.replace(oldsource,str(source))
for line in commands:
 if ' -c ' not in line:continue
 words=shlex.split(line);oldobj=words[words.index('-o')+1]
 # Keep generated FlagTree headers in the matching existing compiler build.
 words=[remap(x) for x in words]
 newobj=str(out/'objects'/oldobj);objectmap[oldobj]=newobj
 for flag in ['-o','-MF','-MT']:
  if flag in words:
   i=words.index(flag)+1;words[i]=str(out/'objects'/oldobj)+('.d' if flag=='-MF' else '')
 Path(newobj).parent.mkdir(parents=True,exist_ok=True)
 compiles.append((Path(oldobj).name,words))
def run(name,words):
 logfile=out/(name+'.log')
 with logfile.open('w') as f:r=subprocess.run(words,cwd=oldbuild,stdout=f,stderr=subprocess.STDOUT,timeout=900)
 entry={'name':name,'argv':words,'returncode':r.returncode};steps.append(entry)
 (out/'steps.json').write_text(json.dumps(steps,indent=2))
 if r.returncode:raise RuntimeError(name+' failed: '+str(logfile))
 return entry
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(lambda item:run(*item),compiles))
package=out/'python/flagtree';package.mkdir(parents=True,exist_ok=True)
installed=Path('/opt/conda/lib/python3.12/site-packages/flagtree')
shutil.copytree(installed,package,dirs_exist_ok=True)
for folder,src in [('profiler','Profiler/python/flagtree_profiler'),('debugger','Debugger/python/flagtree_debugger')]:
 shutil.rmtree(package/folder);shutil.copytree(source/src,package/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for line in commands:
 if ' -shared ' not in line:continue
 command=line.split(' && ')[1] if line.startswith(': && ') else line
 command=command.split(' && ')[0];words=shlex.split(command)
 for i,w in enumerate(words):
  if w in objectmap:words[i]=objectmap[w]
 oldoutput=words[words.index('-o')+1];which='profiler' if '/profiler/' in oldoutput else 'debugger'
 native=package/which/Path(oldoutput).name;words[words.index('-o')+1]=str(native)
 run('link-'+which,words);links.append(str(native))
result={'source_commit':'2a288d66','compile_count':len(compiles),'native_libraries':links,'package':str(package.parent),'device_executed':False,'sha256':{f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in links}}
(out/'build-result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
