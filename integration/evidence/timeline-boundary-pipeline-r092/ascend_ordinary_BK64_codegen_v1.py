"""CPU-only passive SDK source capture for one frozen ordinary math object."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time

p = argparse.ArgumentParser()
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def section(raw, wanted):
    if raw[:7] != b'\x7fELF\x02\x01\x01' or len(raw) > 32 * 1024 * 1024:
        raise ValueError('Expected bounded original ELF64 little endian')
    offset = struct.unpack_from('<Q', raw, 40)[0]
    size, count, names = struct.unpack_from('<HHH', raw, 58)
    if size != 64 or not 0 < count < 8192 or names >= count or offset + count * size > len(raw):
        raise ValueError('Invalid ELF sections')
    headers = [struct.unpack_from('<IIQQQQIIQQ', raw, offset + i * size) for i in range(count)]
    def data(h):
        if h[4] + h[5] > len(raw):
            raise ValueError('Invalid ELF section extent')
        return raw[h[4]:h[4] + h[5]]
    table = data(headers[names])
    for h in headers:
        if h[0] >= len(table):
            raise ValueError('Invalid section name')
        if table[h[0]:].split(b'\0', 1)[0].decode() == wanted:
            return dict(address=h[3], bytes=h[5], sha256=sha(data(h)))
    raise ValueError('Missing section ' + wanted)


r = Path(__file__).parent
root=Path('/tmp/chijin-timeline-r057-ascend/runs/controlled-density-v1/output')
ordinary=root/'BK64-density-1/64-ordinary-1'
metadata_file=root/'compile-cache/EFUB3NG3WUCZWWKUIIPFXFZTJVTQWKNFOGGY6DKUJL2UKBFG5EOQ/product.json'
if sha(metadata_file.read_bytes())!='9c9d10e405528bff59051abbd695648ee84bd623931ecdc34ec5172cd8e3289d':raise ValueError('Frozen ordinary metadata changed')
metadata=json.loads(metadata_file.read_bytes());identity=metadata['ascend_compiler_identity'];sdk=Path(identity['path'])
if sha(sdk.read_bytes())!=identity['sha256'] or identity['sha256']!='1f5cc5054402e901add18af133b3495b861775d68e2113bb8ba94667eef6cf9e':raise ValueError('Original SDK identity changed')
artifacts={name:(ordinary/('ordinary.'+name)).read_bytes() for name in ['bcmlir','npubin']}
if sha(artifacts['bcmlir'])!='ba28b45729536dd89c4bc13e615ac0b64409b909ab5f15bb7c2f4eacf9252302' or sha(artifacts['npubin'])!='7a0eb2a0f452653cb0c5a48c17f16b9b623ae2ba726a49729efd79d80b127238':raise ValueError('Original ordinary compiler artifacts changed')
source=a.output/'kernel.mlir';source.write_bytes(artifacts['bcmlir']);original=artifacts['npubin'];(a.output/'original.npubin').write_bytes(original)
row=dict(original_bcmlir_path=str(ordinary/'ordinary.bcmlir'),original_npubin_path=str(ordinary/'ordinary.npubin'),original_compiled_hash=metadata['hash'])
if metadata['hash']!='21681db4dbb5059b5954421e5b97334d670b29a5718d8f0d544af54504a6e91d' or metadata['arch']!='Ascend910B4-1' or not metadata['use_bytecode'] or metadata['enable_auto_blockify']:raise ValueError('Original ordinary configuration differs')
object_root=a.output/'objects';object_root.mkdir();os.environ['CHIJIN_PASSIVE_OBJECT_ROOT']=str(object_root)
libdevice = Path(metadata['bisheng_options'].split(' -cce-link-aicore-ll-module ')[-1].removeprefix('-cce-link-aicore-ll-module '))
if not libdevice.is_file():
    raise ValueError('Original libdevice unavailable')
real_bisheng = Path('/usr/local/Ascend/ascend-toolkit/latest/bin/bisheng')
if not real_bisheng.is_file():
    raise ValueError('Original actual code generator unavailable')
wrapper_dir = a.output / 'bin'
wrapper_dir.mkdir()
capture = a.output / 'codegen'
capture.mkdir()
wrapper = wrapper_dir / 'bisheng'
wrapper.write_text('#!' + sys.executable + '\n' + r'''
import hashlib,json,os,subprocess,sys,uuid
from pathlib import Path
args=sys.argv[1:]
root=Path(os.environ['CHIJIN_PASSIVE_CODEGEN_CAPTURE'])
folder=root/uuid.uuid4().hex
folder.mkdir()
rows=[]
for index,value in enumerate(args):
    if value.startswith('-'):continue
    p=Path(value)
    if p.suffix not in ('.ll','.bc') or not p.is_file():continue
    if p.stat().st_size>64*1024*1024:raise RuntimeError('Bounded original codegen input')
    raw=p.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    kept=Path(os.environ['CHIJIN_PASSIVE_OBJECT_ROOT'])/(digest+p.suffix)
    if not kept.exists():kept.write_bytes(raw)
    if hashlib.sha256(kept.read_bytes()).hexdigest()!=digest:raise RuntimeError('Retained input CAS changed')
    rows.append(dict(argument_index=index,path=str(p),sha256=digest,bytes=len(raw),retained_file=str(kept)))
real=os.environ['CHIJIN_PASSIVE_REAL_BISHENG']
receipt=dict(argv=[real]+args,inputs=rows,tool_sha256=hashlib.sha256(Path(real).read_bytes()).hexdigest(),state='running',pid=os.getpid())
(folder/'receipt.json').write_text(json.dumps(receipt,indent=2))
code=subprocess.call([real]+args)
receipt.update(state='finished',exit=code)
(folder/'receipt.json').write_text(json.dumps(receipt,indent=2))
sys.exit(code)
''')
wrapper.chmod(0o755)
multi=metadata.get('multibuffer')
stages=metadata.get('num_stages')
command=[str(sdk),str(source),'--target='+metadata['arch']]
if multi is not None or stages is not None:
    value=not (multi is False or stages==1)
    command.append('--enable-auto-multi-buffer='+str(value))
for name,flag in [('enable_ubuf_saving','enable-ubuf-saving'),('enable_preload','enable-preload')]:
    if metadata.get(name) is not None:command.append('--'+flag+'='+str(metadata[name]))
bind=metadata.get('enable_auto_bind_sub_block')
if bind is None:bind=metadata['auto_tile_and_bind_subblock']
command.append('--enable-auto-bind-sub-block='+str(bind))
for name,flag in [('enable_hivm_auto_cv_balance','enable-hivm-auto-cv-balance'),('unit_flag','enable-hivm-unit-flag-sync'),('enable_drop_unit_dims','enable-drop-unit-dims'),('enable_flatten','enable-flatten'),('enable_auto_vectorize_v2','enable-auto-vectorize-v2'),('inject_barrier_all','enable-hivm-inject-barrier-all-sync'),('inject_block_all','enable-hivm-inject-block-all-sync'),('limit_auto_multi_buffer_only_for_local_buffer','limit-auto-multi-buffer-only-for-local-buffer'),('set_workspace_multibuffer','set-workspace-multibuffer'),('tile_mix_vector_loop','tile-mix-vector-loop'),('tile_mix_cube_loop','tile-mix-cube-loop'),('limit_auto_multi_buffer_of_local_buffer','limit-auto-multi-buffer-of-local-buffer'),('disable_auto_inject_block_sync','disable-auto-inject-block-sync'),('disable_size_align_for_cast','disable-size-align-for-cast')]:
    if metadata.get(name) is not None:command.append('--'+flag+'='+str(metadata[name]))
if metadata.get('sync_solver') is not None:
    command+=['--enable-hivm-graph-sync-solver='+str(metadata['sync_solver']),'--enable-hivm-cross-core-gss='+str(metadata['sync_solver'])]
for bitcode in metadata.get('bitcodes') or []:command.append('--link-aicore-bitcode='+bitcode)
command+=['--link-aicore-bitcode='+str(libdevice),'--enable-hfusion-compile=true','--enable-hivm-compile=true','--enable-triton-kernel-compile=true','-o',str(a.output/'kernel')]

env = dict(os.environ)
for key in list(env):
    if key.startswith('FLAGPRISM_'):
        del env[key]
env.update(ASCEND_RT_VISIBLE_DEVICES='', CHIJIN_PASSIVE_CODEGEN_CAPTURE=str(capture),
           CHIJIN_PASSIVE_REAL_BISHENG=str(real_bisheng),
           PATH=str(wrapper_dir) + os.pathsep + env.get('PATH', ''), TMPDIR=str(a.output / 'tmp'))
Path(env['TMPDIR']).mkdir()
(a.output / 'command.json').write_text(json.dumps(dict(argv=command, sdk=identity, libdevice_sha256=sha(libdevice.read_bytes()),
    source_sha256=sha(source.read_bytes()), original_compiled_hash=metadata['hash'], source_row=row,
    metadata_path=str(metadata_file),metadata_sha256=sha(metadata_file.read_bytes()),
    ordinary_options_reconstructed=True, binary_identity_required=True), indent=2))
spec = importlib.util.spec_from_file_location('owned_probe_deadline', '/tmp/chijin-timeline-r019/input/Profiler/python/flagtree_profiler/_deadline.py')
deadline = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = deadline
spec.loader.exec_module(deadline)
started = time.monotonic()
with (a.output / 'sdk.stdout').open('xb') as out, (a.output / 'sdk.stderr').open('xb') as err:
    child = subprocess.Popen(command, stdout=out, stderr=err, env=env, start_new_session=True)
    try:
        child.wait(timeout=45)
    except BaseException:
        deadline._stop_worker(child)
        raise
produced=[]
for f in sorted(a.output.glob('kernel*.o')):
    raw=f.read_bytes()
    produced.append(dict(path=str(f), sha256=sha(raw), bytes=len(raw), text=section(raw,'.text'),
                         whole_binary_identical=raw==original, text_identical=section(raw,'.text')==section(original,'.text')))
result=dict(status='ordinary_passive_codegen_probe',exit=child.returncode,elapsed_s=time.monotonic()-started,
            original_sdk=identity, original_npubin_sha256=sha(original), original_text=section(original,'.text'),
            produced=produced,codegen_receipts=[str(f) for f in sorted(capture.glob('*/receipt.json'))],
            application_replayed=False,device_executed=False,SDK_or_original_modified=False,
            state_writer_qualified=False)
(a.output / 'result.json').write_text(json.dumps(result,indent=2))
if child.returncode or not any(p['whole_binary_identical'] for p in produced):raise RuntimeError('Original CPU codegen/binary binding incomplete, retain diagnostics')
