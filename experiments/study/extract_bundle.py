#!/usr/bin/env python3
"""Extract bounds-checked LLVM offload bundles for vendor disassembly."""
import argparse,hashlib,json,re,struct
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('binary',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
b=a.binary.read_bytes();magic=b'__CLANG_OFFLOAD_BUNDLE__'
if not b.startswith(magic):raise SystemExit('Not an LLVM binary offload bundle')
pos=len(magic);n,=struct.unpack_from('<Q',b,pos);pos+=8
if n>100:raise SystemExit('Invalid bundle count')
rows=[];a.output.mkdir(parents=True,exist_ok=False)
for i in range(n):
 offset,size,length=struct.unpack_from('<QQQ',b,pos);pos+=24
 if length>4096 or pos+length>len(b) or offset+size>len(b):raise SystemExit('Invalid bundle bounds')
 target=b[pos:pos+length].decode();pos+=length
 name=f'{i}-'+re.sub(r'[^A-Za-z0-9_.-]','_',target)+'.bin'
 payload=b[offset:offset+size];(a.output/name).write_bytes(payload)
 rows.append({'target':target,'file':name,'offset':offset,'bytes':size,'sha256':hashlib.sha256(payload).hexdigest()})
(a.output/'bundles.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows))
