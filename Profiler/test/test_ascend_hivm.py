"""Typed static channels, provenance rejection and bounded real subprocess capture."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

PACKAGE = Path(__file__).parents[1] / 'python/flagtree_profiler'
spec = importlib.util.spec_from_file_location('ascend_hivm_test',
                                              PACKAGE / 'ascend_hivm.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
DUMP = '''// -----// IR Dump After GraphSyncSolver (hivm-graph-sync-solver) //----- //
func.func @producer() attributes {hivm.func_core_type = #hivm.func_core_type<AIC>} {
 hivm.hir.sync_block_set[<CUBE>, <PIPE_FIX>, <PIPE_S>] flag = 7
}
// -----// IR Dump After GraphSyncSolver (hivm-graph-sync-solver) //----- //
func.func @consumer() attributes {hivm.func_core_type = #hivm.func_core_type<AIV>} {
 hivm.hir.sync_block_wait[<VECTOR>, <PIPE_FIX>, <PIPE_S>] flag = 7
}
'''


def fixtures(text=DUMP):
    capture = {
        'stderr': text,
        'receipt': {
            'state': 'finished',
            'returncode': 0,
            'compile_id': 'actual-test-compile',
            'command': ['sdk', m.PRINT_FLAG],
            'streams': {
                'stderr': {
                    'truncated': False,
                    'sha256': hashlib.sha256(text.encode()).hexdigest()
                }
            }
        }
    }
    artifacts = []
    for kind, function in [('AIC', 'producer'), ('AIV', 'consumer')]:
        llir = 'define void @' + function + '() { ret void }'
        digest = hashlib.sha256(llir.encode()).hexdigest()
        artifacts.append({
            'sha256': digest,
            'llir': llir,
            'metadata': {
                'module_sha256': digest,
                'actors': [{
                    'function': function,
                    'actor_kind': kind
                }]
            },
            'driver_job': {
                'state': 'finished',
                'compile_id': 'actual-test-compile'
            }
        })
    return capture, artifacts


def test_general_typed_static_channel_without_llvm_encoding_guess():
    result = m.build_static_readiness(*fixtures())
    assert result['state'] == 'compiler_static'
    channel, = result['channels']
    assert channel['flag_id'] == 7 and channel[
        'producer_function'] == 'producer'
    assert channel['consumer_actor_kind'] == 'AIV' and channel[
        'dynamic_generation'] is None
    assert result['clock_alignment'] == 'not_established'


@pytest.mark.parametrize('change', [
    'sha', 'truncated', 'failed', 'flag_missing', 'missing_actor',
    'wrong_actor', 'duplicate_actor', 'compile_id', 'llvm_sha'
])
def test_invalid_capture_or_actor_cannot_certify_channel(change):
    capture, artifacts = fixtures()
    if change == 'sha':
        capture['receipt']['streams']['stderr']['sha256'] = 'wrong'
    if change == 'truncated':
        capture['receipt']['streams']['stderr']['truncated'] = True
    if change == 'failed': capture['receipt']['returncode'] = 1
    if change == 'flag_missing': capture['receipt']['command'] = ['sdk']
    if change == 'missing_actor': artifacts.pop()
    if change == 'wrong_actor':
        artifacts[-1]['metadata']['actors'][0]['actor_kind'] = 'AIC'
    if change == 'duplicate_actor':
        artifacts.append(copy.deepcopy(artifacts[-1]))
    if change == 'compile_id':
        artifacts[-1]['driver_job']['compile_id'] = 'another-compile'
    if change == 'llvm_sha': artifacts[-1]['llir'] += ' changed'
    assert not m.build_static_readiness(capture, artifacts)['channels']


def test_duplicate_static_set_is_not_dynamically_paired_by_order():
    text = DUMP.replace(
        ' hivm.hir.sync_block_set[<CUBE>, <PIPE_FIX>, <PIPE_S>] flag = 7',
        ' hivm.hir.sync_block_set[<CUBE>, <PIPE_FIX>, <PIPE_S>] flag = 7\n hivm.hir.sync_block_set[<CUBE>, <PIPE_FIX>, <PIPE_S>] flag = 7'
    )
    assert not m.build_static_readiness(*fixtures(text))['channels']


def test_unexecuted_pass_and_unmatched_flag_remain_partial():
    assert m.build_static_readiness(
        *fixtures(DUMP.replace('GraphSyncSolver',
                               'OtherPass')))['state'] == 'unavailable'
    assert not m.build_static_readiness(*fixtures(
        DUMP.replace(
            'wait[<VECTOR>, <PIPE_FIX>, <PIPE_S>] flag = 7',
            'wait[<VECTOR>, <PIPE_FIX>, <PIPE_S>] flag = 8')))['channels']


def test_wrapper_preserves_real_process_argv_streams_and_failure(tmp_path):
    code = "import sys; print(sys.argv[1]); print('sdk-error',file=sys.stderr);sys.exit(7)"
    environment = dict(os.environ,
                       FLAGPRISM_ASCEND_COMPILER_OUTPUT=str(tmp_path))
    completed = subprocess.run([
        sys.executable,
        str(PACKAGE / 'ascend_sdk_driver.py'), sys.executable, '-c', code,
        'argument with spaces'
    ],
                               env=environment,
                               capture_output=True)
    assert completed.returncode == 7 and completed.stdout == b'argument with spaces\n'
    assert completed.stderr == b'sdk-error\n'
    receipt = json.loads((tmp_path / 'sdk-compiler.json').read_text())
    assert receipt['state'] == 'failed' and receipt['returncode'] == 7
    assert (tmp_path / 'sdk-stderr.txt').read_bytes() == completed.stderr
    assert receipt['streams']['stderr']['truncated'] is False


def test_pipeline_is_part_of_channel_identity():
    second = DUMP.replace('producer', 'producer2').replace(
        'consumer', 'consumer2').replace('PIPE_FIX', 'PIPE_MTE3')
    capture, artifacts = fixtures(DUMP + second)
    _, extra = fixtures()
    for artifact in extra:
        actor = artifact['metadata']['actors'][0]
        actor['function'] += '2'
        artifact['llir'] = artifact['llir'].replace('()', '2()')
        artifact['sha256'] = hashlib.sha256(
            artifact['llir'].encode()).hexdigest()
        artifact['metadata']['module_sha256'] = artifact['sha256']
    result = m.build_static_readiness(capture, artifacts + extra)
    assert len(result['channels']) == 2
    assert len({channel['id'] for channel in result['channels']}) == 2


@pytest.mark.parametrize(
    'boundary', ['func.func @untyped() {', '// IR Dump After AnotherPass'])
def test_untyped_function_or_new_dump_does_not_inherit_actor(boundary):
    text = DUMP.replace(' hivm.hir.sync_block_set',
                        boundary + '\n hivm.hir.sync_block_set', 1)
    assert not m.build_static_readiness(*fixtures(text))['channels']


@pytest.mark.parametrize('failure', ['open', 'write'])
def test_capture_io_failure_still_drains_large_child_output(tmp_path, failure):
    package = str(PACKAGE / 'ascend_sdk_driver.py')
    setup = '''import importlib.util,sys
from pathlib import Path
s=importlib.util.spec_from_file_location('sdk_test',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
original=Path.open
class Failing:
 def write(self,data): raise OSError('simulated capture write failure')
 def close(self): pass
def patched(path,*args,**kwargs):
 if path.name=='sdk-stdout.txt':
  if sys.argv[2]=='open':raise OSError('simulated capture open failure')
  return Failing()
 return original(path,*args,**kwargs)
Path.open=patched
m.STREAM_LIMIT=32
m.sys.argv=[sys.argv[1],sys.executable,'-c',"import sys;sys.stdout.write('x'*262144);sys.stderr.write('y'*262144);sys.exit(9)"]
sys.exit(m.main())
'''
    completed = subprocess.run(
        [sys.executable, '-c', setup, package, failure],
        env=dict(os.environ, FLAGPRISM_ASCEND_COMPILER_OUTPUT=str(tmp_path)),
        capture_output=True,
        timeout=10)
    assert completed.returncode == 9
    assert len(completed.stdout) == 262144 and len(completed.stderr) == 262144
    receipt = json.loads((tmp_path / 'sdk-compiler.json').read_text())
    assert receipt['returncode'] == 9 and receipt['capture_errors']
    assert receipt['streams']['stdout']['bytes'] == 262144
    assert receipt['streams']['stdout']['truncated'] is True
    assert receipt['streams']['stderr']['retained_bytes'] == 32
