"""Assemble SDK-native text and compare actual function bytes; CPU only."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from flagtree.profiler._deadline import _stop_worker

p = argparse.ArgumentParser()
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True)
source = Path('/tmp/chijin-timeline-r065-gcu/runs/assembly-format-v3/output/assembly-output.mlir')
text = source.read_text()
marker = 'assembly = "'
if text.count(marker) != 1:
    raise RuntimeError('Expected one SDK assembly object')
i = text.index(marker) + len(marker)
blob = bytearray()
while i < len(text) and text[i] != '"':
    if text[i] == '\\':
        if i + 1 < len(text) and text[i+1] in ('\\', '"'):
            blob.append(ord(text[i+1]))
            i += 2
            continue
        pair = text[i+1:i+3]
        if len(pair) != 2 or any(c not in '0123456789abcdefABCDEF' for c in pair):
            raise RuntimeError('Unknown MLIR assembly string escape')
        blob.append(int(pair,16))
        i += 3
    else:
        blob.extend(text[i].encode('utf-8'))
        i += 1
if i >= len(text):
    raise RuntimeError('Unterminated assembly string')
assembly = a.output/'SDK-native.s'
assembly.write_bytes(blob)
tool = Path('/opt/tops/llvm11/bin/llvm-mc')
obj = a.output/'assembled.o'
command = [str(tool), '-triple=dtu', '-mcpu=gcu300', '-filetype=obj', '-o', str(obj), str(assembly)]
with (a.output/'assembler.stdout').open('xb') as out, (a.output/'assembler.stderr').open('xb') as err:
    child = subprocess.Popen(command,stdout=out,stderr=err,start_new_session=True)
    try:
        child.wait(timeout=30)
    except subprocess.TimeoutExpired:
        _stop_worker(child)
        raise RuntimeError('Bounded assembler timed out')


def function(path, name):
    b = path.read_bytes()
    h = struct.unpack_from('<16sHHIQQQIHHHHHH',b)
    if h[0][:6] != b'\x7fELF\x02\x01':
        raise RuntimeError('Expected ELF64 little endian')
    sh = [struct.unpack_from('<IIQQQQIIQQ',b,h[6]+j*h[11]) for j in range(h[12])]
    found = []
    for sec in sh:
        if sec[1] != 2:
            continue
        st = sh[sec[6]]
        strings = b[st[4]:st[4]+st[5]]
        for o in range(sec[4],sec[4]+sec[5],sec[9]):
            sn,info,other,index,value,size = struct.unpack_from('<IBBHQQ',b,o)
            symbol = strings[sn:].split(b'\0',1)[0].decode()
            if symbol != name or not index or index >= len(sh):
                continue
            data = sh[index]
            offset = value-data[3]
            if offset < 0 or offset+size > data[5]:
                raise RuntimeError('Function outside ELF section')
            found.append((b[data[4]+offset:data[4]+offset+size],dict(name=name,address=value,bytes=size,info=info)))
    if len(found) != 1:
        raise RuntimeError('Expected one actual function symbol')
    return found[0]


original_elf = Path('/tmp/chijin-timeline-r061-gcu/runs/final-inspect-v1/output/32-8/1.elf')
disassembler = Path('/opt/tops/llvm11/bin/llvm-objdump')
discommand = [str(disassembler), '-d', '--triple=dtu', '--mcpu=gcu300', '--demangle', '--line-numbers', str(original_elf)]
with (a.output/'llvm11-disassembly.stdout').open('xb') as out, (a.output/'llvm11-disassembly.stderr').open('xb') as err:
    dis = subprocess.run(discommand, stdout=out, stderr=err, timeout=30)
distext = (a.output/'llvm11-disassembly.stdout').read_text()
disresult = dict(argv=discommand, returncode=dis.returncode, tool_sha256=hashlib.sha256(disassembler.read_bytes()).hexdigest(), stdout_sha256=hashlib.sha256(distext.encode()).hexdigest(), stdout_bytes=len(distext.encode()), decode_failure_count=distext.count('error in decoding'), unknown_count=distext.count('<unknown>'))

result = dict(status='SDK_native_assembly_probe',assembler_returncode=child.returncode,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),assembly_sha256=hashlib.sha256(blob).hexdigest(),tool_sha256=hashlib.sha256(tool.read_bytes()).hexdigest(),argv=command,llvm11_disassembly=disresult,device_executed=False,application_replayed=False,original_region_qualification=False)
if child.returncode == 0:
    old = Path('/tmp/chijin-timeline-r061-gcu/runs/final-inspect-v1/output/32-8/1.elf')
    left,li = function(old,'product')
    right,ri = function(obj,'product')
    result.update(original=li,assembled=ri,original_function_sha256=hashlib.sha256(left).hexdigest(),assembled_function_sha256=hashlib.sha256(right).hexdigest(),function_bytes_identical=left==right,first_different_byte=next((i for i,(x,y) in enumerate(zip(left,right)) if x!=y),None),original_ELF_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),assembled_ELF_sha256=hashlib.sha256(obj.read_bytes()).hexdigest())
(a.output/'result.json').write_text(json.dumps(result,indent=2))
if child.returncode:
    raise RuntimeError('Assembler rejected SDK native output; preserve diagnostics')
