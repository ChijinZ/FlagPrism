"""Real wrapper subprocess tests with an explicit CPU compiler fixture."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

DRIVER = Path(
    __file__).parents[1] / 'python/flagtree_profiler/ascend_driver.py'


def test_non_actor_link_receipt_retains_actual_inputs_and_output(tmp_path):
    tool = tmp_path / 'compiler-fixture'
    tool.write_text(
        '#!' + sys.executable + '\n'
        'import pathlib,sys\n'
        'a=sys.argv[1:];p=pathlib.Path(a[a.index("-o")+1]);'
        'p.write_bytes(b"linked:"+pathlib.Path(a[0]).read_bytes())\n')
    tool.chmod(0o755)
    obj = tmp_path / 'actor object.o'
    obj.write_bytes(b'actual fixture object\x00\xff')
    destination = tmp_path / 'final binary.o'
    output = tmp_path / 'receipts'
    output.mkdir()
    env = dict(os.environ,
               FLAGPRISM_ASCEND_REAL_BISHENG=str(tool),
               FLAGPRISM_ASCEND_COMPILER_OUTPUT=str(output),
               FLAGPRISM_ASCEND_COMPILE_ID='cpu-link-fixture')
    result = subprocess.run(
        [sys.executable,
         str(DRIVER),
         str(obj), '-o',
         str(destination)],
        env=env,
        capture_output=True,
        timeout=10)
    assert result.returncode == 0, result.stderr.decode()
    receipt_path, = output.glob('jobs/*/receipt.json')
    receipt = json.loads(receipt_path.read_text())
    assert receipt['state'] == 'finished' and receipt['exit_code'] == 0
    assert receipt['actor_kind'] is None
    assert receipt['driver_process_id'] > 0
    assert receipt['parent_process_id'] == os.getpid()
    assert receipt['process_group_id'] == os.getpgrp()
    assert receipt['executed_command'] == [
        str(tool), str(obj), '-o', str(destination)
    ]
    assert [item['path'] for item in receipt['input_files']] == [str(obj)]
    assert receipt['input_files'][0]['sha256'] == hashlib.sha256(
        obj.read_bytes()).hexdigest()
    assert receipt['object']['sha256'] == hashlib.sha256(
        destination.read_bytes()).hexdigest()
    assert Path(receipt['object']
                ['retained_path']).read_bytes() == destination.read_bytes()


@pytest.mark.parametrize('argv', [['-o'], ['-o', 'one', '-o', 'two']])
def test_ambiguous_output_cannot_start_compiler(tmp_path, argv):
    spec = importlib.util.spec_from_file_location('receipt_driver', DRIVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(RuntimeError, match='ambiguous'):
        module.command_inputs(argv)
