"""Presentation-only local counter coordinates; this is not ns conversion.

Perfetto's file coordinate requires an integer timestamp. Each raw tick advances
one synthetic display coordinate. The physical unit, epoch and read precision
remain unknown. One file contains one observer, preventing false alignment.
"""
import hashlib
from pathlib import Path
from .timeline_perfetto import _uint,_bytes,_text,_annotation,TRACE_FILE_CLOCK
from .timeline_events import validate_raw_batch,canonical_document_byte_budget
from .hooks.timeline import _persist

def write_counter_tick_exports(directory,prefix,batch):
    batch=validate_raw_batch(batch);sites={s['id']:s for s in batch['sites']};exports=[]
    for index,observer in enumerate(batch['observers']):
        events=[e for e in batch['events'] if e['observer_id']==observer['id']]
        if not events:continue
        origin=min(e['start_tick'] for e in events);output=bytearray();first=True
        def packet(payload,tick=None):
            nonlocal first
            header=_uint(10,1)
            if first:header+=_uint(13,1);first=False
            if tick is not None:header+=_uint(8,tick)+_uint(58,TRACE_FILE_CLOCK)
            output.extend(_bytes(1,header+payload))
            if len(output)>canonical_document_byte_budget():raise ValueError('MetaX counter-tick display exceeds byte budget; raw retained')
        packet(_bytes(6,_uint(2,TRACE_FILE_CLOCK)))
        root=int.from_bytes(hashlib.sha256(observer['id'].encode()).digest()[:8],'little') or 1
        label=('INCOMPLETE / TRUNCATED — ' if not batch['complete'] or not observer['complete'] else '')+'MetaX LOCAL COUNTER TICKS (display coordinates; NOT ns) / program '+str(observer['program_coordinates'])
        packet(_bytes(60,_uint(1,root)+_text(2,label)))
        tids={}
        for sid in sorted({e['site_id'] for e in events}):
            tid=int.from_bytes(hashlib.sha256((observer['id']+sid).encode()).digest()[:8],'little') or 1;tids[sid]=tid
            packet(_bytes(60,_uint(1,tid)+_text(2,sites[sid]['name'])+_uint(5,root)))
        pending=[]
        for e in events:
            sid=e['site_id'];start=e['start_tick']-origin;end=e['end_tick']-origin if e['end_tick'] is not None else start
            if end<start:raise ValueError('MetaX counter moved backwards')
            message=_uint(9,1 if e['kind']=='interval' and end>start else 3)+_uint(11,tids[sid])+_text(23,sites[sid]['name'])
            for k,v in {'capture_complete':batch['complete'],'observer_complete':observer['complete'],'coordinate_unit':'raw counter tick','display_coordinate_only':True,'physical_ns_conversion_verified':False,'cross_observer_alignment_verified':False,'raw_start_tick':str(e['start_tick']),'raw_end_tick':str(e['end_tick']),'source_ids':sites[sid]['source_ids'],'semantics':e['semantic']}.items():message+=_annotation(k,v)
            pending.append((start,1,message))
            if e['kind']=='interval' and end>start:pending.append((end,0,_uint(9,2)+_uint(11,tids[sid])))
        for tick,_,payload in sorted(pending,key=lambda x:(x[0],x[1])):packet(_bytes(11,payload),tick)
        file=str(Path(prefix).with_suffix(f'.observer-{index}.counter-ticks.pftrace'));data=bytes(output);_persist(Path(directory)/file,data)
        exports.append({'file':file,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'observer_id':observer['id'],'coordinate_unit':'raw_counter_ticks','presentation_only':True,'physical_ns_conversion_verified':False,'clock_alignment_verified':False})
    return exports
