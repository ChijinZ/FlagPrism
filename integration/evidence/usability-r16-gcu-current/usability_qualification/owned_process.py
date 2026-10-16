"""Linux owned descendant lifecycle, including nested setsid children."""
import ctypes,json,os,signal,subprocess,time
from pathlib import Path
class Interrupted(BaseException):
    def __init__(self,signum):self.signum=signum

def table():
    rows={}
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            data=path.read_text();fields=data[data.rindex(')')+2:].split();pid=int(path.parent.name)
            rows[pid]=dict(pid=pid,ppid=int(fields[1]),pgid=int(fields[2]),startticks=int(fields[19]),argv=(path.parent/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace'))
        except (OSError,ValueError,IndexError):pass
    return rows

def run(command,directory,env,timeout):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    # Adopt daemonized grandchildren so every owned descendant can be reaped.
    if ctypes.CDLL(None,use_errno=True).prctl(36,1,0,0,0)!=0:raise RuntimeError('PR_SET_CHILD_SUBREAPER failed')
    owner=os.getpid();owned={};started=time.monotonic();old={};proc=None;interrupted=None;timed_out=False
    def scan():
        rows=table();parents={owner}|set(owned)
        changed=True
        while changed:
            changed=False
            for pid,row in rows.items():
                if pid!=owner and row['ppid'] in parents and pid not in owned:
                    owned[pid]=row;parents.add(pid);changed=True
        return rows
    def stop(signum,frame):raise Interrupted(signum)
    for sig in [signal.SIGTERM,signal.SIGINT]:old[sig]=signal.signal(sig,stop)
    try:
        with (directory/'stdout.log').open('xb') as out,(directory/'stderr.log').open('xb') as err:
            proc=subprocess.Popen(command,stdout=out,stderr=err,env=env,start_new_session=True)
            scan();identity=owned.get(proc.pid)
            if identity is None:raise RuntimeError('child exited before identity capture')
            (directory/'process.json').write_text(json.dumps(dict(**identity,command=command,owner_pid=owner,outer_timeout_s=timeout),indent=2))
            while proc.poll() is None:
                scan()
                if time.monotonic()-started>timeout:timed_out=True;break
                time.sleep(.1)
    except Interrupted as error:interrupted=error.signum
    finally:
        for sig in old:signal.signal(sig,signal.SIG_IGN)
        scan()
        for sig,grace in [(signal.SIGTERM,2),(signal.SIGKILL,2)]:
            limit=time.monotonic()+grace
            while True:
                current=scan()
                live=[]
                for pid,identity in owned.items():
                    row=current.get(pid)
                    if row and row['startticks']==identity['startticks'] and row['pgid']==identity['pgid']:
                        live.append(pid)
                        try:os.kill(pid,sig)
                        except ProcessLookupError:pass
                if not live or time.monotonic()>=limit:break
                time.sleep(.05)
        if proc is not None:proc.wait(timeout=5)
        while True:
            try:
                pid,status=os.waitpid(-1,os.WNOHANG)
                if pid==0:break
            except ChildProcessError:break
        current=table();survivors=[pid for pid,v in owned.items() if pid in current and current[pid]['startticks']==v['startticks']]
        (directory/'owned-processes.json').write_text(json.dumps(dict(owner_pid=owner,identities=list(owned.values()),survivors=survivors),indent=2))
        for sig,handler in old.items():signal.signal(sig,handler)
        if survivors:raise RuntimeError('owned descendants survived cleanup')
    result=dict(returncode=(128+interrupted if interrupted else proc.returncode),timed_out=timed_out,interrupted_signal=interrupted,host_process_wall_s=time.monotonic()-started)
    (directory/'terminal.json').write_text(json.dumps(result,indent=2))
    return result
