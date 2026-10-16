"""Version-only authorization bridge; mathematical and complete raw gates unchanged."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
VERSION='R16-NVIDIA-authorization-v2-explicit-require'
def require(condition,message):
    if not condition: raise RuntimeError(message)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify(here,freeze):
    expected=json.loads((ROOT/'cpu-freeze.json').read_text())
    require(freeze==expected,'current authorization differs from CPU frozen bytes')
    require(sys.executable==freeze['python'] and sys.prefix==freeze['venv'],'interpreter namespace')
    require(freeze['backend']=='nvidia' and freeze['device']==0,'NVIDIA device authorization')
    for p,h in freeze['immutable_files'].items(): require(sha(p)==h,'frozen installed/source/gate bytes: '+p)
    return freeze['immutable_files']
