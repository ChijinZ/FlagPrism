#!/usr/bin/env python3
"""One immutable input byte set shared by all backends, including both GEMM probes."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
rng=np.random.Generator(np.random.PCG64(1729));manifest={}
for family,shapes in [('matmul',[(128,128,128),(512,512,512),(257,193,320),(32,32,32)]),('rows',[(32,256),(256,1024),(127,769),(4,64)]),('transpose',[(256,256),(1024,1024),(513,257),(32,64)])]:
 for shape in shapes:
  label='x'.join(map(str,shape))
  arrays=[((shape[0],shape[2]),'<f2'),((shape[2],shape[1]),'<f2'),((shape[1],),'<f4')] if family=='matmul' else ([((shape[0],shape[1]),'<f4'),((shape[1],),'<f4'),((shape[1],),'<f4')] if family=='rows' else [(shape,'<f4')])
  for i,(dimensions,dtype) in enumerate(arrays):
   x=(rng.standard_normal(dimensions)*.1).astype(dtype);raw=x.tobytes();name=f'{family}-{label}-{i}.bin';(a.output/name).write_bytes(raw);manifest[name]={'shape':dimensions,'dtype':dtype,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
(a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
