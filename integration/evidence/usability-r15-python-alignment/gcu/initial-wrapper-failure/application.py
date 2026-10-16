"""External startup witness; executes the unchanged ordinary application once."""
import hashlib,json,os,runpy,sys,time
from pathlib import Path
p=Path(__file__).resolve().parent;target=p/sys.argv[1];ledger=p/'startup-ledger.jsonl'
def write(stage,mode):
 imports={n:str(m.__file__) for n,m in list(sys.modules.items()) if n.startswith(('triton','flagtree')) and getattr(m,'__file__',None)}
 assert all(Path(x).is_relative_to(sys.prefix) for x in imports.values()),imports
 with ledger.open(mode) as f:f.write(json.dumps(dict(stage=stage,pid=os.getpid(),time=time.time(),python=sys.executable,prefix=sys.prefix,source=str(target),source_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),imports=imports))+'\n')
write('startup','x');sys.path.insert(0,str(p));sys.argv=[str(target),*sys.argv[2:]];runpy.run_path(str(target),run_name='__main__');write('completed','a')
