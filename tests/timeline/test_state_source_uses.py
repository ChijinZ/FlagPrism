"""Real MLIR parsing for the finite source admission, without a device."""
import importlib.util
from pathlib import Path

import pytest
from triton._C.libtriton import ir

spec = importlib.util.spec_from_file_location(
    'state_source_uses',
    Path(__file__).with_name('state_source_uses.py'))
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)


def check(tmp_path, extra='', *, suffix='', result=''):
    text = '''module {
  tt.func public @kernel(%State: !tt.ptr<i32>, %Out: !tt.ptr<i64>) ''' + result + ''' {
    %value = tt.load %State : !tt.ptr<i32>
    tt.store %State, %value : !tt.ptr<i32>
''' + extra + '\n    tt.return' + suffix + '''
  }
}'''
    path = tmp_path / 'input.mlir'
    path.write_text(text)
    context = ir.context()
    ir.load_dialects(context)
    module = ir.parse_mlir_module(str(path), context)
    return source.check_state_source_uses(module,
                                          function_name='kernel',
                                          state_index=0)


def test_direct_state_access(tmp_path):
    answer = check(tmp_path)
    if answer['state_address_noescape'] is not True:
        raise AssertionError(answer)


def test_original_address_payload_is_not_an_observer(tmp_path):
    with pytest.raises(ValueError, match='State source address escapes'):
        check(
            tmp_path, '''
    %bits = tt.ptr_to_int %State : !tt.ptr<i32> -> i64
    tt.store %Out, %bits : !tt.ptr<i64>''')


def test_original_returned_pointer(tmp_path):
    with pytest.raises(ValueError, match='State source address escapes'):
        check(tmp_path,
              suffix=' %State : !tt.ptr<i32>',
              result='-> !tt.ptr<i32>')


def test_original_pointer_region_forwarding(tmp_path):
    with pytest.raises(ValueError, match='State source address escapes'):
        check(
            tmp_path, '''
    %true = arith.constant true
    %alias = scf.if %true -> (!tt.ptr<i32>) {
      scf.yield %State : !tt.ptr<i32>
    } else {
      scf.yield %State : !tt.ptr<i32>
    }
    tt.store %alias, %value : !tt.ptr<i32>''')
