"""SSH transport only: wait for the existing queue, seal new views, start SQL.

No mathematical application or product module is imported or replayed here.
An uncertain remote launch is polled at its registered root, never retried.
"""
import hashlib
import importlib.util
import json
import shlex
import subprocess
import time
from pathlib import Path

ROOT = Path('/home/jin-lab-pc/workspace/osdi_flagprism')
PRE = ROOT / 'artifacts/timeline/run-062/preflight'
OUT = PRE / 'audit-orchestration-v1'
OUT.mkdir(exist_ok=False)
spec = importlib.util.spec_from_file_location('ssh_transport', ROOT / 'scripts/study_remote.py')
remote = importlib.util.module_from_spec(spec)
spec.loader.exec_module(remote)
ASC = ['sudo', '-n', '-u', 'chijin', 'docker', 'exec', 'chijin_v3.5.x', '/usr/local/python3.11.15/bin/python3.11', '-I', '-c']
NV = ['docker', 'exec', '-i', 'chijin-study-pro6000', '/workspace/venv/bin/python', '-I', '-c']


def call(host, command, data=None):
    result = remote.run(host, command, timeout=30, stdin=data)
    if result.returncode:
        raise RuntimeError('Remote operation failed: ' + result.stderr.decode(errors='replace')[-2000:])
    return result.stdout


def poll_terminal(host, prefix, root):
    code = ('from pathlib import Path;import json;r=Path(' + repr(root) + ');'
            'p=r/"terminal.json";print(p.read_text() if p.exists() else "null")')
    started = time.monotonic()
    while time.monotonic() - started < 350:
        try:
            data = call(host, shlex.join(prefix + [code]))
        except subprocess.TimeoutExpired:
            time.sleep(3)
            continue
        value = json.loads(data)
        if value is not None:
            if value['returncode'] != 0:
                raise RuntimeError('Registered controller failed: ' + root)
            return value
        time.sleep(3)
    raise RuntimeError('Unknown controller outcome; preserve owner and do not relaunch: ' + root)


queue = PRE / 'queue-v2'
owner = json.loads((queue / 'launch.json').read_text())
started = time.monotonic()
while not (queue / 'result.json').exists():
    proc = Path('/proc') / str(owner['pid']) / 'stat'
    if not proc.exists():
        raise RuntimeError('Existing queue owner missing without result; do not restart')
    fields = proc.read_text().rsplit(')', 1)[1].split()
    if int(fields[19]) != owner['startticks'] or fields[0] == 'Z':
        raise RuntimeError('Existing queue owner stopped without result; do not restart')
    if time.monotonic() - started > 1800:
        raise RuntimeError('Queue observation allowance expired; do not restart')
    time.sleep(3)
result = json.loads((queue / 'result.json').read_text())
if result['passed'] != 60 or result['not_completed'] != 0:
    raise RuntimeError('Original affected60 queue incomplete; do not package partial denominator')
(OUT / 'queue-result.json').write_text(json.dumps(result, indent=2))
print('Original affected60 queue complete; packaging retained bytes only', flush=True)
try:
    reply = call('zhiyuan_ascend', (PRE / 'ascend-affected-audit-prepare-launch-command-v1.txt').read_text(), (PRE / 'ascend-affected-audit-prepare-input-v1.tgz').read_bytes())
    (OUT / 'prepare-launch.json').write_bytes(reply)
except subprocess.TimeoutExpired:
    (OUT / 'prepare-launch-observation-timeout.txt').write_text('Poll registered root; launch not repeated.\n')
ascroot = '/tmp/chijin-timeline-r062-ascend/runs/audit-prepare-v1'
(OUT / 'prepare-terminal.json').write_text(json.dumps(poll_terminal('zhiyuan_ascend', ASC, ascroot), indent=2))
code = 'from pathlib import Path;print(Path(' + repr(ascroot + '/output/result.json') + ').read_text())'
prepared = json.loads(call('zhiyuan_ascend', shlex.join(ASC + [code])))
(OUT / 'prepare-result.json').write_text(json.dumps(prepared, indent=2))
destination = '/workspace/chijin-timeline-r062-nvidia/imported/ascend'
chunks = []
for chunk in prepared['chunks']:
    code = 'from pathlib import Path;import sys;sys.stdout.buffer.write(Path(' + repr(ascroot + '/output/chunks/' + chunk['file']) + ').read_bytes())'
    data = call('zhiyuan_ascend', shlex.join(ASC + [code]))
    if len(data) != chunk['bytes'] or hashlib.sha256(data).hexdigest() != chunk['sha256']:
        raise RuntimeError('Transferred chunk differs')
    local = OUT / chunk['file']
    local.write_bytes(data)
    code = ('from pathlib import Path;import sys,hashlib;p=Path(' + repr(destination + '/chunks/' + chunk['file']) + ');'
            'd=sys.stdin.buffer.read();'
            'assert len(d)==' + str(chunk['bytes']) + ' and hashlib.sha256(d).hexdigest()==' + repr(chunk['sha256']) + ';'
            'p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(d) if not p.exists() else None;assert p.read_bytes()==d')
    call('zhangquan_pro6000', shlex.join(NV + [code]), data)
    chunks.append(chunk)
    (OUT / 'transferred.json').write_text(json.dumps(chunks, indent=2))
    print('Transferred SHA-checked chunk ' + chunk['file'], flush=True)
code = '''from pathlib import Path
import io,sys,tarfile,json,hashlib
config=json.loads(sys.stdin.buffer.read());r=Path(DESTINATION)
data=b''.join((r/'chunks'/c['file']).read_bytes() for c in config['chunks'])
if len(data)!=config['archive_bytes'] or hashlib.sha256(data).hexdigest()!=config['archive_sha256']:raise RuntimeError('Original archive differs')
out=r/'data';out.mkdir()
with tarfile.open(fileobj=io.BytesIO(data)) as t:
 for m in t:
  if not m.isfile() or Path(m.name).is_absolute() or '..' in Path(m.name).parts:raise RuntimeError('Unsafe transferred archive')
  p=out/m.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(t.extractfile(m).read())
(r/'prepare-result.json').write_text(json.dumps(config,indent=2))
print(json.dumps(dict(captures=config['captures'],traces=config['traces'],archive_sha256=config['archive_sha256'])))
'''.replace('DESTINATION', repr(destination))
(OUT / 'import-result.json').write_bytes(call('zhangquan_pro6000', shlex.join(NV + [code]), json.dumps(prepared).encode()))
try:
    reply = call('zhangquan_pro6000', (PRE / 'nvidia-ascend-affected-tp-launch-command-v1.txt').read_text(), (PRE / 'ascend-affected-tp-input-v1.tgz').read_bytes())
    (OUT / 'TP-launch.json').write_bytes(reply)
except subprocess.TimeoutExpired:
    (OUT / 'TP-launch-observation-timeout.txt').write_text('Poll registered root; launch not repeated.\n')
nvroot = '/workspace/chijin-timeline-r062-nvidia/runs/affected60-tp-v1'
(OUT / 'TP-terminal.json').write_text(json.dumps(poll_terminal('zhangquan_pro6000', NV, nvroot), indent=2))
code = 'from pathlib import Path;print(Path(' + repr(nvroot + '/output/result.json') + ').read_text())'
(OUT / 'TP-result.json').write_bytes(call('zhangquan_pro6000', shlex.join(NV + [code])))
print('New affected60 export SQL audit terminal; inspect receipts before claiming completion', flush=True)
