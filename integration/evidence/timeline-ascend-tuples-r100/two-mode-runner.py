from pathlib import Path
import argparse,subprocess,sys,shutil,json
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);d=Path(__file__).parent;steps=[]
formatter=shutil.which('yapf')
if formatter:
 c=subprocess.run([formatter,'-i',str(d/'regions.py'),str(d/'cases.py')],capture_output=True,timeout=15);(a.output/'format.log').write_bytes(c.stdout+c.stderr)
 if c.returncode:raise RuntimeError('Formatting failed')
for label,flags in [('normal',[]),('optimized',['-O'])]:
 with (a.output/(label+'.log')).open('xb') as log:c=subprocess.run([sys.executable,'-I',*flags,str(d/'probe.py'),'--output',str(a.output/label)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,timeout=60)
 steps.append(dict(name=label,returncode=c.returncode));(a.output/'steps.json').write_text(json.dumps(steps,indent=2))
 if c.returncode:raise RuntimeError(label+' failed')
