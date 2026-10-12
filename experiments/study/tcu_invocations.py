"""Importer for TCU --print-gcu-trace CSV; IDs retain their capture-local namespace."""
import csv,re,math
from pathlib import Path

def time_us(s):
 m=re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)(ns|us|µs|ms|s)',s)
 if not m:raise ValueError(f'Unknown time syntax {s}')
 return float(m[1])*{'ns':.001,'us':1,'µs':1,'ms':1000,'s':1e6}[m[2]]

def parse(path):
 records=[];record=None;metric=None
 for row in csv.reader(Path(path).open()):
  row=[x.strip() for x in row]
  if not row or not any(row):continue
  if row==['','Device','Kernel ID','Kernel Name','Start','Duration']:continue
  if row[0]=='' and len(row)==6 and row[2].isdigit():
   record={'device_identifier':row[1],'tcu_kernel_id':int(row[2]),'configuration':row[3],'relative_start_us':time_us(row[4]),'duration_us':time_us(row[5]),'metrics':[]};records.append(record);metric=None
  elif row[0]=='' and len(row)==4 and row[1].startswith('SIP/'):
   if record is None:raise ValueError('Metric lacks invocation')
   metric={'name':row[1],'unit':row[2],'value':number(row[3]),'instances':[]};record['metrics'].append(metric)
  elif row[:1]==['GCU Metric Trace']:
   if metric is None:raise ValueError('Instance lacks metric')
   metric['instances'].append({'die':int(row[1]),'sip':int(row[2]),'value':number(row[3])})
  elif row[:1]==['Type']:continue
  else:raise ValueError(f'Unrecognized TCU trace row: {row}')
 if not records or any(not r['metrics'] for r in records):raise ValueError('No complete invocation records')
 return records

def number(s):
 value=int(s) if re.fullmatch(r'[0-9]+',s) else float(s)
 if value<0 or not math.isfinite(value):raise ValueError(f'Invalid metric {s}')
 return value
