import concurrent.futures,hashlib,html,json,re,time,urllib.request
from pathlib import Path
root=Path('/workspace/downloads/llvm-chunks');root.mkdir(exist_ok=True)
url='https://oaitriton.blob.core.windows.net/public/llvm-builds/llvm-f6ded0be-ubuntu-x64.tar.gz'
name='llvm-f6ded0be.tar.gz';size=1234838471;chunk=16*1024*1024
expected=None
old=Path('/workspace/downloads/llvm-f6ded0be.tar.gz')
if old.exists() and old.stat().st_size<size:
 with old.open('rb') as f:
  i=0
  while data:=f.read(chunk):
   dest=root/f'llvm-chunk-{i:03d}'
   if not dest.exists():dest.write_bytes(data)
   i+=1
def get(i):
 start=i*chunk;end=min(size-1,start+chunk-1);dest=root/f'llvm-chunk-{i:03d}'
 if dest.exists() and dest.stat().st_size==end-start+1:return dest
 for attempt in range(5):
  try:
   offset=dest.stat().st_size if dest.exists() else 0
   if offset>end-start+1:dest.unlink();offset=0
   req=urllib.request.Request(url,headers={'Range':f'bytes={start+offset}-{end}'})
   with urllib.request.urlopen(req,timeout=30) as r:
    assert r.status==206,(i,r.status)
    assert r.headers.get('Content-Range','').startswith(f'bytes {start+offset}-'),r.headers.get('Content-Range')
    with dest.open('ab') as f:
     while data:=r.read(262144):f.write(data)
   assert dest.stat().st_size==end-start+1,(i,dest.stat().st_size)
   print('CHUNK',i,dest.stat().st_size,flush=True);return dest
  except Exception as e:print('RETRY',i,attempt,repr(e),flush=True);time.sleep(2)
 raise RuntimeError(f'chunk{i} exhausted')
count=(size+chunk-1)//chunk
with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:parts=list(pool.map(get,range(count)))
out=Path('/workspace/downloads')/name;h=hashlib.sha256()
with out.open('wb') as f:
 for part in parts:
  with part.open('rb') as r:
   while data:=r.read(1048576):f.write(data);h.update(data)
assert out.stat().st_size==size
expected=h.hexdigest()
(root/'llvm-archive-downloaded.json').write_text(json.dumps({'url':url,'sha256':expected,'bytes':size,'path':str(out)},indent=2))
print('VERIFIED',str(out),flush=True)
