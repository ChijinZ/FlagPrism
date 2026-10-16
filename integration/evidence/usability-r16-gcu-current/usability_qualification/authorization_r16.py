"""Exact r16 installed-byte authorization; no old ce00 authorization reuse."""
import hashlib,json,sys
from pathlib import Path
from check_common_report import require
def verify_authorization(here,freeze):
    seal=Path(here).parent/'freeze.json'
    require(hashlib.sha256(seal.read_bytes()).hexdigest()==EXPECTED_FREEZE_SHA256,'r16 freeze bytes changed')
    expected=json.loads(seal.read_text())
    require(freeze==expected,'r16 candidate changed')
    require(sys.executable==freeze['python'] and sys.prefix==freeze['venv'],'r16 interpreter mismatch')
    for path,digest in freeze['file_sha256'].items():
        require(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,'r16 frozen bytes changed: '+path)
    require(freeze['backend']=='enflame' and freeze['device']==0,'r16 backend/device mismatch')
    return freeze['verifier_sha256']

EXPECTED_FREEZE_SHA256 = '0a81905568c8d0a3a9477cb7ced3fc3957a0645e391e378dc21bf8ce14486ba4'
