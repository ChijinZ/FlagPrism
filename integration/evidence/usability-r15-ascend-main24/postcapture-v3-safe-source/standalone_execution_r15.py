"""CPU proof for actual standalone AIV launch and a cross-admissible-bank total.
No product import, compiler invocation, source replay, or per-operator whitelist.
"""
import base64,hashlib,json,re,subprocess
from pathlib import Path
from authorization_r15 import require,sha,load

def disassembly(path):
    p=subprocess.run(['objdump','-d','-C',str(path)],capture_output=True,text=True,timeout=20)
    require(p.returncode==0,'actual native runtime object disassembly failed');return p.stdout

def functions(text):
    heads=list(re.finditer(r'^([0-9a-f]+) <([^\n]+)>:\n',text,re.M))
    return [(m[2],text[m.end():heads[i+1].start() if i+1<len(heads) else len(text)]) for i,m in enumerate(heads)]

def prove_native_blockdim(text):
    owners=[(n,t) for n,t in functions(text) if re.search(r'\bbl\s+[0-9a-f]+ <rtKernelLaunch@plt>',t)]
    require(len(owners)==1 and '_launch(' in owners[0][0] and '{lambda()#1}::operator()() const' in owners[0][0],'actual standalone native launch call missing/ambiguous')
    name,body=owners[0];ins=[re.sub(r'^\s*[0-9a-f]+:\s+[0-9a-f]+\s+','',line).split('//')[0].strip() for line in body.splitlines() if re.match(r'^\s*[0-9a-f]+:\s+[0-9a-f]+\s+',line)]
    # Exact generated native arithmetic: closure.gridX * gridY * gridZ,
    # stored once as uint32 blockNum; no factor 2, clamp or replacement.
    compact='\n'.join(ins)
    pattern=(r'ldr\s+x0, \[sp, #(\d+)\]\nldr\s+w1, \[x0\]\nldr\s+x0, \[sp, #\1\]\nldr\s+w0, \[x0, #4\]\nmul\s+w1, w1, w0\nldr\s+x0, \[sp, #\1\]\nldr\s+w0, \[x0, #8\]\nmul\s+w0, w1, w0\nstr\s+w0, \[sp, #(\d+)\]')
    matches=list(re.finditer(pattern,compact));require(len(matches)==1,'actual native blockDim product dataflow not proved');slot=matches[0][2]
    writes=re.findall(r'\bstr\s+w\w+, \[sp, #'+slot+r'\]',compact);require(len(writes)==1,'actual blockDim overwritten after product')
    callpos=next(i for i,line in enumerate(ins) if '<rtKernelLaunch@plt>' in line);require(any(re.fullmatch(r'ldr\s+w1, \[sp, #'+slot+r'\]',line) for line in ins[max(0,callpos-4):callpos]),'actual rtKernelLaunch blockDim argument not product')
    calls=re.findall(r'^\s*([0-9a-f]+):[^\n]*\bbl\s+[0-9a-f]+ <rtKernelLaunch@plt>',body,re.M);require(len(calls)==1,'actual native task launch call repeated');call=int(calls[0],16)
    begin=int(re.search(r'^\s*([0-9a-f]+):',body,re.M)[1],16)
    for branch in re.finditer(r'^\s*([0-9a-f]+):\s+[0-9a-f]+\s+b(?:\.[a-z]+)?\s+([0-9a-f]+) <',body,re.M):
        require(not (int(branch[1],16)>call and begin<=int(branch[2],16)<=call),'actual launch CFG can repeat native call')
    return dict(blockDim_formula='gridX*gridY*gridZ',actual_native_call_sites=1,product_stack_slot=int(slot),compiler_generated_function_sha256=hashlib.sha256(body.encode()).hexdigest(),actual_machine_dataflow_proved=True)

def prove_standalone(bundle,binary,receipt,cache,installed):
    bundle=Path(bundle);cache=Path(cache);installed=Path(installed);m=binary['compiler_metadata'];h=m['flagprism_ascend_handoff']
    require(m.get('mix_mode')=='aiv' and type(m.get('bs_task_type')) is int and m['bs_task_type']==10,'standalone task kind/mix ratio not exact AIV/0')
    artifacts=h['artifacts'];require(len(artifacts)==1 and artifacts[0]['driver_job']['actor_kind']=='AIV','standalone has multiple/mixed actual actor modules')
    sdk=h['sdk_ir_capture']['stderr'];headers=[l for l in sdk.splitlines() if 'func.func @' in l and ' attributes ' in l];require(len(headers)==1 and 'hivm.func_core_type<AIV>' in headers[0] and 'mix_mode = "aiv"' in headers[0] and 'part_of_mix' not in headers[0],'actual SDK function is mixed/unknown')
    require(len(receipt['grid'])==1 and type(receipt['grid'][0]) is int and receipt['grid'][0]>0,'standalone proof is for actual frozen one-dimensional grid')
    rawlaunch=load(bundle/'raw/native/capture.launches.json');launches=[x for x in rawlaunch['launches'] if x['binary_id']==binary['id']]
    require(len(launches)==len(receipt['calls']) and all(x['grid']==receipt['grid'] for x in launches),'actual host launch grid/cardinality mismatch')
    require(all(c['compiled_kernel_hash']==binary['id'] for c in receipt['calls']),'actual source kernel binary mismatch')
    loaders=list(cache.rglob('npu_utils.so'));launchers=list(cache.rglob('launcher*.so'));require(len(loaders)==len(launchers)==1,'actual runtime native module missing/ambiguous')
    source=installed/'triton/backends/ascend/npu_utils.cpp';data=source.read_bytes();key=base64.b32encode(hashlib.md5(data).digest()).decode().rstrip('=')
    require(loaders[0].parent.name==key,'actual native loader cache does not bind installed source bytes')
    text=source.read_text();require('if (kernel_mode == "aiv")\n    devbin.magic = RT_DEV_BINARY_MAGIC_ELF_AIVEC;' in text,'installed native AIVEC registration source semantics changed')
    loader=disassembly(loaders[0]);owners=[t for n,t in functions(loader) if n.startswith('registerKernel(')];require(len(owners)==1,'actual native binary registration function missing')
    require(re.search(r'mov\s+w0, #0x5246',owners[0]) and re.search(r'movk\s+w0, #0x4141, lsl #16',owners[0]) and '<rtDevBinaryRegister@plt>' in owners[0],'actual loader AIVEC magic/call not proved')
    launcher=disassembly(launchers[0]);block=prove_native_blockdim(launcher)
    query=load(bundle/'raw/native/capture.cann-launch-receipts.json')
    return dict(kind='standalone_aiv_one_instance',explicit_SUB0_guard=False,actual_sdk_AIV_not_part_of_mix=True,actual_mix_mode='aiv',actual_bs_task_type=10,native_binary_registration='RT_DEV_BINARY_MAGIC_ELF_AIVEC',native_magic=0x41415246,actual_host_launches=len(launches),actual_logical_programs=receipt['grid'][0],actual_native_blockDim=receipt['grid'][0],blockDim_basis='actual cached ELF machine dataflow plus exact captured host grid; not a dynamic SDK packet',dynamic_sdk_query_receipts=len(query['receipts']),native_blockDim_proof=block,native_loader_sha256=sha(loaders[0]),native_launcher_sha256=sha(launchers[0]),native_loader_source_sha256=sha(source),runtime_launch_record_sha256=sha(bundle/'raw/native/capture.launches.json'),sdk_capture_sha256=hashlib.sha256(sdk.encode()).hexdigest(),physical_semantics='standalone AIVEC registration: one vector work instance per rtKernelLaunch block; complete 1D grid maps BLOCK bijectively to source program',expected_admissible_actor_slots=[1,2],expected_terminal_count_sum_per_program=1,per_bank_execution_inferred_from_nonzero=False)

def verify_standalone_sum(cells,requirements):
    require(isinstance(cells,list) and cells and isinstance(requirements,list) and requirements,'standalone complete actual cells/obligations required')
    actual={}
    for c in cells:
        k=(c['program'],c['site'],c['actor']['id']);require(k not in actual,'duplicate actual standalone cell');actual[k]=c
    seen=set();out=[]
    for r in requirements:
        require(set(r)=={'program','site','actor_slots','count_sum'} and type(r['program']) is int and type(r['site']) is int and r['actor_slots']==[1,2] and type(r['count_sum']) is int and r['count_sum']==1,'standalone typed independently fixed sum obligation changed')
        key=(r['program'],r['site']);require(key not in seen,'duplicate standalone obligation');seen.add(key)
        keys=[(*key,slot) for slot in [1,2]];require(all(k in actual for k in keys),'whole admissible bank/program/site cell absent')
        require(all(type(actual[k]['count']) is int and actual[k]['count']>=0 for k in keys),'invalid actual standalone count')
        require(sum(actual[k]['count'] for k in keys)==1,'actual terminal count sum contradicts single standalone instance')
        out.append(dict(**r,raw_offsets=[actual[k]['raw_offset'] for k in keys],raw_sha256=[actual[k]['raw_sha256'] for k in keys]))
    return out
