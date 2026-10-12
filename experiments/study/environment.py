#!/usr/bin/env python3
"""Record the loaded runtime rather than infer it from a nearby checkout."""
import argparse,hashlib,importlib,json,os,platform,subprocess
from pathlib import Path
os.environ.setdefault('TORCH_DEVICE_BACKEND_AUTOLOAD','0')
p=argparse.ArgumentParser();p.add_argument('--backend',choices=['cann','enflame','cuda'],required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
import torch
extension={'cann':'torch_npu','enflame':'torch_gcu','cuda':None}[a.backend]
if extension:importlib.import_module(extension)
import triton
info={'backend':a.backend,'python':platform.python_version(),'machine':platform.machine(),'target':str(triton.runtime.driver.active.get_current_target()),'modules':{},'nearby_checkouts':{}}
for name in ['torch',extension,'triton','flagtree.profiler','flagtree.debugger']:
 if not name:continue
 try:
  m=importlib.import_module(name);path=Path(m.__file__)
  info['modules'][name]={'version':getattr(m,'__version__',None),'file':str(path),'file_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
  if name=='flagtree.profiler':
   code=path.parent/'profile.py'
   if code.exists():info['modules'][name]['profile_py_sha256']=hashlib.sha256(code.read_bytes()).hexdigest()
 except Exception as e:info['modules'][name]={'error':repr(e)}
for path in ['/workspace/FlagTree','/workspace/FlagPrism']:
 if Path(path,'.git').exists():
  def git(*args):return subprocess.run(['git','-C',path,*args],text=True,capture_output=True).stdout.strip()
  info['nearby_checkouts'][path]={'head':git('rev-parse','HEAD'),'branch':git('branch','--show-current'),'status':git('status','--porcelain'),'note':'Nearby checkout; not proof that loaded installed modules were built from this commit.'}
iface={'cann':getattr(torch,'npu',None),'enflame':getattr(torch,'gcu',None),'cuda':torch.cuda}[a.backend]
info['device_count']=iface.device_count()
try:info['device_properties_0']=repr(iface.get_device_properties(0))
except Exception as e:info['device_properties_error']=repr(e)
info['code_hashes']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in Path(__file__).parent.glob('*.py')}
info['limits']=['No fixed-clock or exclusive-device guarantee was recorded.','Different backend compiler/SDK versions prevent attributing differences exclusively to hardware.']
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(info,indent=2)+'\n')
print(a.output)
