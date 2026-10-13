#!/usr/bin/env python3
"""Audit single-invocation source/SYS-native association; never join SDK replays."""
import argparse,csv,hashlib,json,struct
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,default=Path('artifacts/study-goal-run/ascend-diagnosis-r001/joint-results'));p.add_argument('--output',type=Path,default=Path('FlagPrism/experiments/study/results/2026-10-13-porting/ascend-diagnosis/joint-sys'));a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,obj):path.write_text(json.dumps(obj,indent=2)+'\n')
def csvwrite(path,rows):
 with path.open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
summary={'status':'passed','association_status':'verified_shared_reported_SYS_epoch','counter_domain':'SYS_CNT reported by source GetSystemCycle and raw SDK task SYS fields','tick_ns':20,'claim_scope':'Empirical common reported epoch for these actual invocations; not independent physical clock calibration or hardware occupancy. Native windows are SDK actor lifecycle envelopes; source intervals are scalar control positions.','selection':'First lexicographic DeviceProf packet per configuration; uniquely match all three program0 actor windows to ONE source application; no replay joins','conditions':{'warm_up':0,'replay_mode':'application','requested_metric':'ArithmeticUtilization','launch_count':1,'source_kernel_calls_per_application':1,'added_barriers':0,'inner_native_profiler':False},'packet_schema':{'record_bytes':128,'stream_id_offset_u16':4,'task_id_offset_u16':6,'core_bits_offset_u16':20,'core_type_bit':'bits & 1 (0 AIC, 1 AIV)','core_id':'(bits >> 1) & 127','subblock_offset_u16':28,'program_offset_u16':30,'start_SYS_offset_u64':112,'end_SYS_offset_u64':120},'configurations':{}}
actorrows=[];issuerows=[]
for cfg in ['P32_K32','R_K32_K256']:
 receipt=json.loads((a.raw/f'joint-sys-{cfg}-receipt.json').read_text());assert receipt['returncode']==0
 sources=[]
 for path in sorted((a.raw/f'joint-sys-{cfg}-source').glob('*/result.json')):
  s=json.loads(path.read_text());assert s['status']=='passed' and s['matmul_calls_in_app']==1 and s['added_barriers']==0
  assert [(h[2],h[1],h[0]) for h in s['actor_headers']]==[(0,0,0),(1,0,0),(1,1,0)]
  sources.append((path,s))
 assert len({s['binary_sha256'] for _,s in sources})==1 and len({json.dumps(s['input_sha256'],sort_keys=True) for _,s in sources})==1
 matches=[]
 for packet in sorted((a.raw/f'joint-sys-{cfg}').glob('*/dump/DeviceProf*.bin')):
  blob=packet.read_bytes();assert len(blob)%128==0;native={}
  for off in range(0,len(blob),128):
   rec=blob[off:off+128];sub,bid=struct.unpack_from('<HH',rec,28)
   if bid!=0:continue
   bits=struct.unpack_from('<H',rec,20)[0];key=(bits&1,sub);assert key not in native
   start,end=struct.unpack_from('<QQ',rec,112)
   native[key]={'actor_type':bits&1,'subblock':sub,'program':bid,'core_id':(bits>>1)&127,'stream_id':struct.unpack_from('<H',rec,4)[0],'task_id':struct.unpack_from('<H',rec,6)[0],'start_SYS':start,'end_SYS':end,'record_byte_offset':off}
  assert set(native)=={(0,0),(1,0),(1,1)}
  assert len({(v['stream_id'],v['task_id'],v['start_SYS']) for v in native.values()})==1
  candidates=[(path,s) for path,s in sources if all(native[(h[2],h[1])]['start_SYS']<=h[3]<=h[4]<=native[(h[2],h[1])]['end_SYS'] for h in s['actor_headers'])]
  assert len(candidates)==1,(cfg,packet,len(candidates));path,s=candidates[0];origin=native[(0,0)]['start_SYS'];hs=s['actor_headers'];loops=s['loop_records']
  assert len(loops)==4096//s['tile'][2]
  for i,row in enumerate(loops):
   assert row[0]==i and hs[0][3]<=row[2]<=row[3]<=row[4]<=row[5]<=row[6]<=row[7]<=row[8]<=row[9]<=row[10]<=row[11]<=row[12]<=row[13]<=hs[0][4]
   if i:assert loops[i-1][13]<=row[2]
  for h in hs[1:]:assert h[3]<=h[5]<=h[6]<=h[7]<=h[8]<=h[4]
  assert hs[0][3]<=hs[0][5]<=hs[0][6]<=hs[0][4]
  # Producer scalar signal issue must precede consumer observed wait return.
  assert all(hs[0][5]<=h[6] for h in hs[1:])
  actors=[]
  for h in hs:
   n=native[(h[2],h[1])];row={'configuration':cfg,'actor':'AIC' if h[2]==0 else f'AIV{h[1]}',**n,'body_enter_SYS':h[3],'body_exit_SYS':h[4],'signal_enter_SYS':h[5] if h[2]==0 else None,'signal_return_SYS':h[6] if h[2]==0 else None,'wait0_enter_SYS':h[5] if h[2]==1 else None,'wait0_return_SYS':h[6] if h[2]==1 else None,'workspace_load_issue_enter_SYS':h[7] if h[2]==1 else None,'workspace_load_issue_return_SYS':h[8] if h[2]==1 else None}
   for name in ['body_enter','body_exit','signal_enter','signal_return','wait0_enter','wait0_return','workspace_load_issue_enter','workspace_load_issue_return']:
    v=row[name+'_SYS'];row[name+'_us']=(v-origin)*.02 if v is not None else None
   row['native_start_us']=(n['start_SYS']-origin)*.02;row['native_end_us']=(n['end_SYS']-origin)*.02;actors.append(row)
  match={'source_result_path':str(path),'source_result_sha256':sha(path),'source_pid':s['pid'],'packet_path':str(packet),'packet_sha256':sha(packet),'packet_record_count':len(blob)//128,'origin_SYS':origin,'binary_sha256':s['binary_sha256'],'input_sha256':s['input_sha256'],'max_abs_error':s['max_abs_error'],'actors':actors,'actor_headers':hs,'loop_records':loops,'assertions':{'unique_all_actor_packet_match':True,'same_stream_task_start_epoch':True,'source_body_inside_native_actor_window':True,'all_iteration_markers_monotonic_in_AIC_body':True,'original_wait_brackets_monotonic_in_AIV_body':True,'producer_signal_issue_before_consumer_wait_return':True}}
  matches.append(match)
 assert len(matches)==2 and len({m['source_pid'] for m in matches})==2
 selected=matches[0];write(a.output/f'{cfg}-selected.json',selected)
 actorrows.extend(selected['actors']);origin=selected['origin_SYS']
 names=['iteration','buffer_slot','iteration_enter','A_reuse_wait_enter','A_reuse_wait_return','A_load_issue_enter','A_load_issue_return','B_reuse_wait_enter','B_reuse_wait_return','B_load_issue_enter','B_load_issue_return','MMA_helper_issue_enter','MMA_helper_issue_return','iteration_exit','A_L1_address','B_L1_address']
 for row in selected['loop_records']:
  r={'configuration':cfg,'source_pid':selected['source_pid'],'iteration':row[0],'buffer_slot':row[1],'A_L1_address':row[14],'B_L1_address':row[15]}
  for j in range(2,14):r[names[j]+'_SYS']=row[j];r[names[j]+'_us']=(row[j]-origin)*.02
  issuerows.append(r)
 summary['configurations'][cfg]={'source_application_count':len(sources),'native_packet_count':len(matches),'unmatched_baseline_source_pids':[s['pid'] for _,s in sources if s['pid'] not in {m['source_pid'] for m in matches}],'selected_source_pid':selected['source_pid'],'selected_packet':selected['packet_path'],'selected_origin_SYS':selected['origin_SYS'],'selected_actor_values':selected['actors'],'loop_count':len(selected['loop_records']),'all_matches':[{k:v for k,v in m.items() if k not in ['loop_records','actor_headers']} for m in matches]}
write(a.output/'summary.json',summary);csvwrite(a.output/'selected_actor_windows.csv',actorrows);csvwrite(a.output/'selected_issue_points.csv',issuerows)
print(json.dumps({'status':summary['status'],'output':str(a.output),'selected_actor_rows':len(actorrows),'selected_iteration_rows':len(issuerows),'selected_pids':{k:v['selected_source_pid'] for k,v in summary['configurations'].items()}},indent=2))
