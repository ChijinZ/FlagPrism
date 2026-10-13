import concurrent.futures,hashlib,html,json,re,time,urllib.request
from pathlib import Path
root=Path('/workspace/downloads');root.mkdir(exist_ok=True)
base='https://download.pytorch.org/whl/cu128/'
name='torch-2.8.0%2Bcu128-cp310-cp310-manylinux_2_28_x86_64.whl'
index=urllib.request.urlopen(base+'torch/',timeout=30).read().decode()
links=re.findall(r'href="([^"]+)"',index)
link=next(html.unescape(x) for x in links if name in x)
expected=link.split('#sha256=')[1];url=link.split('#')[0]
size=889148606;chunk=16*1024*1024
print('EXPECTED_SHA256',expected,flush=True)
def get(i):
 start=i*chunk;end=min(size-1,start+chunk-1);dest=root/f'torch-chunk-{i:03d}'
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
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:parts=list(pool.map(get,range(count)))
out=root/name.replace('%2B','+');h=hashlib.sha256()
with out.open('wb') as f:
 for part in parts:
  with part.open('rb') as r:
   while data:=r.read(1048576):f.write(data);h.update(data)
assert h.hexdigest()==expected,(h.hexdigest(),expected)
(root/'torch-wheel-verified.json').write_text(json.dumps({'url':url,'sha256':expected,'bytes':size,'path':str(out)},indent=2))
print('VERIFIED',str(out),flush=True)
