"""The hidden-only compiler bridge requires the newly built compiler plugin."""
import pytest
from triton._C.libtriton import ir
from flagtree.debugger.native import compiler_binding


def parse(tmp_path, text):
    binding = compiler_binding()
    assert binding is not None and hasattr(
        binding, 'prepare_late_observation_abi'
    ), 'new Debugger compiler binding was not built/loaded'
    context = ir.context()
    ir.load_dialects(context)
    binding.load_dialects(context)
    file = tmp_path / 'late.mlir'
    file.write_text(text)
    return binding, context, ir.parse_mlir_module(str(file), context)


def test_hidden_only_formal_identity_and_idempotency(tmp_path):
    binding, context, module = parse(
        tmp_path, '''module {
      tt.func public @fresh_entry(%input: !tt.ptr<f32>, %count: i32) {
        tt.return
      }
    }''')
    index = binding.prepare_late_observation_abi(module)
    assert index == 2
    assert binding.prepare_late_observation_abi(module) == index
    text = str(module)
    assert 'ascend_actor_dynamic_v1' in text
    assert 'flagtree_debug.collect' not in text
    assert 'tt.store' not in text


@pytest.mark.parametrize('attribute_location', ['module', 'function'])
def test_snapshot_instrumentation_cannot_reuse_dynamic_buffer(
        tmp_path, attribute_location):
    attr = 'flagtree.debug.instrumentation_inserted = true'
    module_attr = ' attributes {' + attr + '}' if attribute_location == 'module' else ''
    function_attr = ' attributes {' + attr + '}' if attribute_location == 'function' else ''
    text = 'module' + module_attr + ' { tt.func public @fresh_entry(%input: !tt.ptr<f32>)' + function_attr + ' { tt.return } }'
    binding, context, module = parse(tmp_path, text)
    with pytest.raises(Exception, match='before snapshot instrumentation'):
        binding.prepare_late_observation_abi(module)


def test_multiple_public_entries_have_no_guessed_hidden_identity(tmp_path):
    binding, context, module = parse(
        tmp_path, '''module {
      tt.func public @first(%input: !tt.ptr<f32>) { tt.return }
      tt.func public @second(%input: !tt.ptr<f32>) { tt.return }
    }''')
    with pytest.raises(Exception, match='one public Triton entry'):
        binding.prepare_late_observation_abi(module)


@pytest.mark.parametrize('argument_type,index', [('!tt.ptr<f32>', 0),
                                                 ('!tt.ptr<i32>', 9)])
def test_existing_stale_hidden_identity_is_rejected(tmp_path, argument_type,
                                                    index):
    binding, context, module = parse(
        tmp_path, 'module { tt.func public @fresh_entry(%input: ' +
        argument_type + ') attributes {flagtree.debug.hidden_arg_index = ' +
        str(index) + ' : i32} { tt.return } }')
    with pytest.raises(Exception, match='hidden formal'):
        binding.prepare_late_observation_abi(module)
