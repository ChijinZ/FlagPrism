"""Stdlib-only retained-byte audit; no product imports or new device execution."""
from pathlib import Path
import argparse, hashlib, json, struct, base64, tarfile, re
root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--archive',type=Path,default=root/'outlined-final-original-evidence.tgz')
parser.add_argument('--repo',type=Path,default=root.parents[3]/'FlagPrism-method')
parser.add_argument('--output',type=Path,default=root/'retained-byte-audit.json')
options=parser.parse_args()
archive=options.archive
with tarfile.open(archive) as t:
    files={m.name:t.extractfile(m).read() for m in t.getmembers() if m.isfile()}
def need(value,message):
    if not value:raise RuntimeError(message)
def j(name):return json.loads(files[name])
def identifier(identity,kind,*parts):
    data=json.dumps([*identity,kind,*parts],ensure_ascii=False,separators=(',',':')).encode()
    return kind+'-'+hashlib.sha256(data).hexdigest()
repo=options.repo
need(j('native-outlined/terminal.json')['state']=='build_passed_not_device_qualified','Actual native build failed')
need(b'Building CXX object' in files['native-outlined/native-wheel-build.stdout.log'],'Native source was not compiled')
need(j('package-multifunction/terminal.json')['state']=='build_passed_not_device_qualified','Python package failed')
bridge=j('package-multifunction/native-byte-bridge.json')
need(bridge['byte_equal'] and len(bridge['native_members'])==7,'Python delta changed native')
need(files['installed/timeline_nvidia_machine.py']==(repo/'Profiler/python/flagtree_profiler/timeline_nvidia_machine.py').read_bytes(),'Installed mapper/source mismatch')
for n in ['install-v1','boundary-math-v1','public-outlined-v1','outlined-objects-v1','ui-install-v1']:
    need(j('runs/'+n+'/terminal.json')['returncode']==0,'Actual owned job failed: '+n)
for mode in ['normal','optimized']:
    log=files[f'runs/install-v1/output/machine-contract-{mode}.stderr.log']
    need(b'Ran 20 tests' in log and b'\nOK\n' in log,'Mapper contracts')
    need(b'4 passed' in files[f'runs/install-v1/output/public-contract-{mode}.stdout.log'],'Public contracts')
    n=j('runs/install-v1/output/boundary-native-contract-'+mode+'/result.json')
    need(n['anchors']==34 and n['dependent_counter_reads']==17 and len(n['rejected'])==12 and n['legacy_path_unchanged'],'Boundary2 positive/negative contract')
need(j('runs/install-v1/output/result.json')['installed_members_byte_verified']==607,'Wheel install identity')
need(b'3 passed' in files['runs/install-v1/output/legacy-automatic-hook.stdout.log'],'Legacy hook')
for n in ['p01_nvidia_boundary_math.py','p01_nvidia_public_timeline.py','ordinary_timeline_workload.py','test_nvidia_machine_map.py','nvidia_boundary_binding_smoke.py']:
    need(files['check-input-v1/'+n]==(repo/'tests/timeline'/n).read_bytes(),'Executed source mismatch: '+n)
need(files['object-input-v1/p01_nvidia_outlined_objects.py']==(repo/'tests/timeline/p01_nvidia_outlined_objects.py').read_bytes(),'Object inspector source mismatch')
base='runs/public-outlined-v1/output/'
phases=['api-cold','api-warm','recovered-raw.timeline','api-after-failure','api-overflow','cli','types']
raw_count=intervals=orphans=groups=overwritten=0
seen_invocations=set();phase_functions=[]
for name in phases:
    prefix=('runs/boundary-math-v1/output/public/timeline/' if name=='types' else base+name+('/' if name.endswith('.timeline') else '/timeline/'))
    idx=j(prefix+'index.json')
    need(idx['status']=='partial_clock_unverified','False clock certification')
    need(len(idx['captures'])==(5 if name=='types' else 1 if name=='api-overflow' else 4),'Actual request count')
    handles=[]
    for item in idx['captures']:
        capture=j(prefix+item['capture_file']);owner=capture['owner']
        identity=tuple(owner[k] for k in ('capture_id','invocation_id','binary_id'))
        need(identity[1] not in seen_invocations,'Reused invocation identity')
        seen_invocations.add(identity[1]);handles.append(owner['function'])
        need(owner['plan'].get('timeline_boundary_version')==2 and owner['plan'].get('timeline_boundary_strategy')=='outlined_device_calls_pending_region_audit','False or missing compiler boundary strategy')
        need(owner['state']=='raw_ready' and owner['submission_outcome']=='returned','Writer completion')
        raw=files[prefix+capture['raw_file']]
        need(hashlib.sha256(raw).hexdigest()==capture['raw_sha256'],'Original raw SHA')
        input_name=prefix+str(Path(capture['raw_file']).with_suffix('.input.json'))
        input_document=j(input_name)
        need(input_document['capture_status']=='raw_persisted_pending_decode','False predecode completeness')
        need(input_document['owner']==owner and input_document['metadata']==capture['metadata'],'Input snapshot changed')
        canonical=j(prefix+capture['events_file']);decoded=j(prefix+capture['decoded_file']);facts=j(prefix+capture['async_file'])
        need(canonical['clock_status']=='unverified' and canonical['boundary_status']=='unverified','Raw pairing certified timing')
        need(tuple(canonical['identity'][k] for k in ('capture_id','invocation_id','binary_id'))==identity,'Canonical identity')
        need(canonical['raw_artifact']==dict(sha256=capture['raw_sha256'],bytes=len(raw)),'Canonical raw binding')
        layout=owner['layout'];stride=layout['scratch_size'];grid=layout['grid']
        need(len(raw)==layout['raw_bytes']==len(layout['slots'])*stride,'Compact extent')
        record_map={r['id']:r for r in canonical['records']}
        observer_map={o['id']:o for o in canonical['observers']}
        site_map={s['id']:s for s in canonical['sites']}
        physical={};expected_pairs=[];expected_orphans=[]
        for slot,program in layout['slots']:
            magic,pid,sm,size=struct.unpack_from('<4I',raw,slot*stride)
            need((magic,pid,size)==(0x46505432,program,32768),'Physical header')
            coordinates=[program%grid[0],(program//grid[0])%grid[1],program//(grid[0]*grid[1])]
            for warp in range(4):
                words=struct.unpack_from('<I',raw,slot*stride+16+warp*4)[0]
                need(words!=0xffffffff and words%4==0,'Unexpected saturated/misaligned physical counter')
                written=words//4;first=max(0,written-512);overwritten+=first
                oid=identifier(identity,'observer','nvidia.recording_warp',str(warp),coordinates)
                observer=observer_map[oid]
                need(observer['retained_records']==min(written,512) and observer['written_records']==written and observer['overwritten_records']==first,'Observer physical counts')
                need(observer['physical_identity']=={'nvidia.finalize_smid':sm},'Header SM was reinterpreted')
                stack=[]
                for seq in range(first,written):
                    offset=slot*stride+32+warp*8192+(seq%512)*16
                    tag,lo,hi,absolute=struct.unpack_from('<4I',raw,offset)
                    need(seq==absolute,'Physical record absolute sequence')
                    site=identifier((identity[2],),'site',str(tag&0x7fffffff))
                    rid=identifier(identity,'record',oid,seq)
                    expected=dict(id=rid,observer_id=oid,site_id=site,phase='exit' if tag>>31 else 'entry',tick=(hi<<32|lo),sequence=seq,offset=offset,length=16)
                    need(record_map[rid]==expected,'Canonical record differs from physical payload')
                    physical[rid]=expected
                    backend_id=identifier(identity,'record',program,warp,seq)
                    need(canonical['backend_record_map']['nvidia.cp_async.groups.v1'][backend_id]==rid,'Mechanism record correspondence')
                    if expected['phase']=='entry':
                        stack.append(expected)
                    elif stack and stack[-1]['site_id']==site:
                        begin=stack.pop();expected_pairs.append((begin['id'],rid))
                    else:
                        need(not observer['complete'],'Complete physical stream has orphan')
                        expected_orphans.extend((r['id'],'entry') for r in stack);stack=[]
                        expected_orphans.append((rid,'exit'))
                expected_orphans.extend((r['id'],'entry') for r in stack)
        need(set(physical)==set(record_map),'Canonical silently added/dropped records')
        actual_pairs=[];actual_orphans=[]
        for event in canonical['events']:
            refs=event['record_ids'];points=[physical[k] for k in refs]
            need(event['id']==identifier(identity,'event',*refs),'Event namespace')
            need(event['semantic']==site_map[event['site_id']]['semantic'] and event['iteration_id'] is None,'Changed source/iteration semantic')
            if event['kind']=='interval':
                need(len(points)==2 and event['start_tick']==points[0]['tick'] and event['end_tick']==points[1]['tick'],'Actual interval endpoints')
                actual_pairs.append(tuple(refs));intervals+=1
            else:
                need(event['kind']=='incomplete' and len(points)==1,'Unexpected event type')
                p=points[0]
                need((event['start_tick'],event['end_tick'])==((p['tick'],None) if p['phase']=='entry' else (None,p['tick'])),'Synthesized orphan endpoint')
                actual_orphans.append((refs[0],p['phase']));orphans+=1
        need(set(actual_pairs)==set(expected_pairs) and set(actual_orphans)==set(expected_orphans),'Canonical pairing differs from physical nesting')
        need(not facts['time_arrow_verified'],'False time arrow')
        if name=='api-overflow':
            need(not canonical['complete'] and not facts['groups'] and not facts['dependencies'],'Loss inferred async generations')
        else:
            need(canonical['complete'] and decoded['complete'],'Normal capture incomplete')
        for source in capture['metadata']['scope_origin_sources']:
            if source.get('status')=='captured':
                need(source['encoding']=='base64' and hashlib.sha256(base64.b64decode(source['content'])).hexdigest()==source['sha256'],'Retained source snapshot')
        for artifact in capture['metadata']['timeline_artifacts']:
            if artifact['retained_file'].endswith('.llir'):
                llvm=files[prefix+artifact['retained_file']].decode()
                getters=[line for line in llvm.splitlines() if '%globaltimer' in line]
                need(getters and all('~{memory}' in line and 'asm sideeffect' in line for line in getters),'Getter missing actual LLVM memory clobber')
            need(hashlib.sha256(files[prefix+artifact['retained_file']]).hexdigest()==artifact['sha256'],'Compiled artifact')
        raw_count+=len(physical);groups+=len(facts['groups'])
    phase_functions.append(handles)
    if not name.endswith('.timeline'):
        manifest_prefix='runs/boundary-math-v1/output/public/' if name=='types' else base+name+'/'
        manifest=j(manifest_prefix+'manifest.json')
        for file,entry in manifest['files'].items():
            payload=files[manifest_prefix+file]
            need(len(payload)==entry['bytes'] and hashlib.sha256(payload).hexdigest()==entry['sha256'],'Bundle manifest')
need(phase_functions[0]==phase_functions[1],'Cold/warm loaded function identity changed')
for name in ['api-cold','api-warm','api-export-failure','api-after-failure','api-overflow','cli','legacy-auto']:
    need(base+name+'-math/host-once.txt' in files and base+name+'-math/math-passed.txt' in files,'Original once/math proof')
need(len(j(base+'legacy-auto/ai/observations.json')['captures'])==4,'Legacy count lost')
proofs={};mapping_captures=0;command_files=set()
for name in phases:
    prefix=('runs/boundary-math-v1/output/public/timeline/' if name=='types' else base+name+('/' if name.endswith('.timeline') else '/timeline/'))
    for item in j(prefix+'index.json')['captures']:
        c=j(prefix+item['capture_file']);m=c['machine_counter_mapping']
        need(m['status']=='counter_mapping_complete_region_unverified','Actual mapper unavailable')
        proof=j(prefix+m['counter_map_file']);mapping_captures+=1
        need(proof['binary_id']==c['owner']['binary_id'] and not proof['region_boundaries_verified'] and not proof['clock_qualified'],'False certificate or binary identity')
        rows=c['metadata']['timeline_artifacts']
        def artifact(suffix):
            matches=[r for r in rows if r['retained_file'].endswith(suffix)]
            need(len(matches)==1,'Missing actual artifact')
            return files[prefix+matches[0]['retained_file']]
        cubin,ptx=artifact('.cubin'),artifact('.ptx')
        machine_prefix=prefix+str(Path(m['counter_map_file']).parent)+'/'
        text=files[machine_prefix+'lines.stdout'];doc=json.loads(files[machine_prefix+'json.stdout'])
        version=files[machine_prefix+'version.stdout']
        for k,raw in [('cubin',cubin),('ptx',ptx),('sass_lines',text),('sass_json',files[machine_prefix+'json.stdout'])]:
            need(hashlib.sha256(raw).hexdigest()==proof['artifacts'][k+'_sha256'],'Machine proof input SHA')
        need(proof['tool_sha256']=='6df0054fac801e7ab7d251506cfe52a1171c207de0923d8a3d57fdd5a1f6d982' and hashlib.sha256(version).hexdigest()==proof['tool_version_sha256'],'Actual disassembler version/SHA')
        commands=j(machine_prefix+'commands.json')
        need(len(commands)==3 and all(v['state']=='terminal' and v['returncode']==0 for v in commands),'Tool failure hidden')
        command_files.add(machine_prefix+'commands.json')
        # Independent ELF section retrieval, not the product decoder.
        start=struct.unpack_from('<Q',cubin,40)[0];stride,count,names=struct.unpack_from('<HHH',cubin,58)
        need(stride==64,'Unexpected real ELF section size')
        sections=[struct.unpack_from('<IIQQQQIIQQ',cubin,start+i*stride) for i in range(count)]
        strings=cubin[sections[names][4]:sections[names][4]+sections[names][5]]
        hs=[s for s in sections if strings[s[0]:].split(b'\0',1)[0]==b'.nv_debug_ptx_txt']
        need(len(hs)==1,'Ambiguous embedded PTX')
        h=hs[0];embedded=cubin[h[4]:h[4]+h[5]]
        need(hashlib.sha256(embedded).hexdigest()==proof['artifacts']['embedded_ptx_sha256'],'Embedded PTX SHA')
        pl=ptx.decode().splitlines();dl=embedded.decode().split('\0')[:-1]
        need(len(pl)==len(dl),'Actual PTX line alignment')
        actual={};function=None;line=None
        descriptors={f['function-name']:f for f in doc[1]}
        function_sections={};current_section=None
        for txt in text.decode().splitlines():
            sec=re.match(r'\s*\.section\s+(\.text\.[^,\s]+)',txt)
            if sec:current_section=sec[1];function=current_section[6:];line=None
            label=re.fullmatch(r'\s*([^\s:]+):\s*',txt)
            if label and label[1] in descriptors:function=label[1];line=None
            if function in descriptors:function_sections[function]=current_section
            loc=re.match(r'\s*//## File "\.nv_debug_ptx_txt", line (\d+)',txt)
            if loc:line=int(loc[1])
            ins=re.match(r'\s*/\*([0-9a-f]+)\*/\s*(.*?)\s*;',txt)
            if ins and 'SR_GLOBALTIMERLO' in ins[2]:
                actual[(function,int(ins[1],16))]=(line,ins[2])
        body={f['function-name']:f['sass-instructions'] for f in doc[1]}
        gt={(f,descriptors[f]['start']+16*i) for f,ins in body.items() for i,row in enumerate(ins) if 'SR_GLOBALTIMER' in row.get('operands','')}
        need(gt==set(actual)=={(v['function'],v['pc']) for v in proof['counter_pcs']},'Static getter PC set differs')
        for v in proof['counter_pcs']:
            line,ins=actual[(v['function'],v['pc'])];n=line-1
            need(line==v['ptx_line'] and '%globaltimer' in pl[n] and re.sub(r'\s+','',pl[n])==re.sub(r'\s+','',dl[n]),'Getter does not bind exact actual PTX debug line')
            annotation=pl[v['annotation_line']-1].strip()
            need(re.fullmatch(r'//\s*flagprism_timeline_v1_site_'+str(v['site_id'])+'_'+v['phase']+r'\s*;?',annotation) is not None,'Actual annotation mismatch')
            need(all('%globaltimer' not in x and 'flagprism_timeline_v1_site_' not in x for x in pl[v['annotation_line']:n]),'Marker crosses another getter or marker')
            need(v['section']==function_sections[v['function']] and v['function_start']==descriptors[v['function']]['start'] and v['relative_pc']==v['pc']-v['function_start'],'Helper function/section/PC identity')
            opcode=body[v['function']][v['relative_pc']//16]
            need(opcode['opcode']=='CS2R' and opcode['operands']==v['operands'] and opcode.get('predicate')==v['sass_predicate'],'Machine PC payload mismatch')
        expected={(int(site),phase) for site,_ in c['metadata']['scope_id_names'] for phase in ['entry','exit']}
        need(expected=={(v['site_id'],v['phase']) for v in proof['counter_pcs']},'Missing actual site phase')
        need(all(not x.get('opcode','').startswith('MEMBAR') for ins in body.values() for x in ins),'New hardware completion barrier')
        key=proof['artifacts']['cubin_sha256']
        summary=dict(cubin_sha256=key,binary_id=proof['binary_id'],functions=list(body),instructions=sum(len(x) for x in body.values()),counter_pcs=len(gt),site_phases=len(expected),debug_omissions=len(proof['ptx_debug_omissions']))
        if key in proofs:need(proofs[key]==summary,'Same actual object has differing PC proof')
        proofs[key]=summary
for job in j('owned-outlined-final.json'):
    need(all(w['current_state'] in ['Z','missing'] or not w['same_startticks'] for w in job['owners']),'Owned process still live')
objects=j('runs/outlined-objects-v1/output/result.json')
need(objects['device_launches']==0 and len(objects['objects'])==7,'Missing final object/CFG evidence')
need(sum(len(o['counters']) for o in objects['objects'])==140,'Lost counter helpers')
for obj in objects['objects']:
    need(obj['functions']==1+obj['nonzero_function_starts'] and not obj['membar_instructions'],'Unexpected function or barrier')
    cfg_path='runs/outlined-objects-v1/output/'+obj['cubin_sha256']+'/cfg.stdout'
    need(hashlib.sha256(files[cfg_path]).hexdigest()==obj['cfg_sha256'] and b'digraph' in files[cfg_path],'Actual CFG SHA')
    need(not obj['region_boundaries_verified'] and not obj['clock_qualified'],'Static inspection overclaims')
    need(all(c['direct_call_sites'] for c in obj['counters']),'Counter callee has no caller')
types=j('runs/boundary-math-v1/output/result.json')
need(types['actual_math_launches']==5 and all(x['exact_cpu_math'] and x['state']==[1,1,1] for x in types['math']),'Type math or once oracle')
need(mapping_captures==len(seen_invocations)==26 and len(proofs)==7,'Incomplete actual capture/binary scope')
out=dict(status='outlined_calls_raw_and_static_objects_audited_not_full_P01',captures=len(seen_invocations),physical_records=raw_count,paired_intervals=intervals,incomplete_endpoints=orphans,logical_groups=groups,overwritten_records=overwritten,counter_mapped_captures=mapping_captures,unique_mapped_cubins=len(proofs),unique_static_counter_pcs=sum(x['counter_pcs'] for x in proofs.values()),actual_machine_commands=sum(len(j(f)) for f in command_files),counter_mapping_tool_references=3*mapping_captures,objects=list(proofs.values()),machine_cpu_methods_each_mode=20,native_abi_negative_methods_each_mode=12,type_math_calls=5,archive_bytes=archive.stat().st_size,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),limits=['Counter PCs do not prove source-region machine boundaries','Clock scale/endpoint error/epoch unqualified; no ns or time arrows','Physical buffer reuse, other backend producers, Perfetto and independent qualification incomplete'])
options.output.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
