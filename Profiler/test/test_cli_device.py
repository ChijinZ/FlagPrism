"""Runtime device selection precedes collection and survives child launchers."""
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import pytest


@pytest.fixture
def cli(monkeypatch):
    package = ModuleType('_cli_device_test')
    package.__path__ = [
        str(Path(__file__).parents[1] / 'python/flagtree_profiler')
    ]
    monkeypatch.setitem(sys.modules, package.__name__, package)
    definitions = {
        'profile':
        dict(start=lambda *a, **k: None,
             finalize=lambda: None,
             _select_backend=lambda: 'cann',
             _automatic_backend=lambda value: value),
        'flags':
        dict(set_command_line=lambda: None),
        'mthreads':
        dict(DEFAULT_MCU_SECTIONS=(),
             MCU_INTEGRATION_ENABLED=False,
             merge_mcu_vendor_artifact=lambda *a: None,
             run_mcu_profile=lambda *a: None),
        'tianshu':
        dict(merge_ixkn_vendor_artifact=lambda *a: None,
             run_ixkn_profile=lambda *a: None),
    }
    for name, values in definitions.items():
        module = ModuleType(package.__name__ + '.' + name)
        module.__dict__.update(values)
        monkeypatch.setitem(sys.modules, module.__name__, module)
    return importlib.import_module(package.__name__ + '.cli')


def arguments(cli, monkeypatch, *flags):
    monkeypatch.setattr(sys, 'argv',
                        ['profiler', *flags, 'ordinary.py', '--user-arg'])
    return cli.parse_arguments()


@pytest.mark.parametrize('backend,extension,runtime,device',
                         [('cann', 'torch_npu', 'npu', 4),
                          ('enflame', 'torch_gcu', 'gcu', 0),
                          ('instrumentation', None, 'cuda', 2)])
def test_device_is_set_before_collector_and_application(
        cli, monkeypatch, backend, extension, runtime, device):
    events = []
    fake = ModuleType('torch')
    setattr(
        fake, runtime,
        SimpleNamespace(
            set_device=lambda value: events.append(('device', value))))
    monkeypatch.setitem(sys.modules, 'torch', fake)
    if extension:
        monkeypatch.setitem(sys.modules, extension, ModuleType(extension))
    monkeypatch.setenv('FLAGPRISM_CAPTURE_INTERNAL', '1')
    monkeypatch.setattr(cli, 'start', lambda *a, **k: events.append(
        ('start', k['backend'])))
    monkeypatch.setattr(cli, 'do_setup_and_execute',
                        lambda target: events.append(('application', target)))
    monkeypatch.setattr(cli, 'finalize', lambda: events.append(
        ('finalize', None)))
    args, target = arguments(cli, monkeypatch, '--backend', backend,
                             '--device', str(device), '--detail', 'auto')
    cli.run_profiling(args, target)
    assert events == [('device', device), ('start', backend),
                      ('application', ['ordinary.py', '--user-arg']),
                      ('finalize', None)]


def test_invalid_and_unsupported_devices_fail_explicitly(cli, monkeypatch):
    with pytest.raises(SystemExit):
        arguments(cli, monkeypatch, '--device', '-1')
    with pytest.raises(ValueError, match='unavailable'):
        cli._set_runtime_device('mthreads', 0)
    with pytest.raises(ValueError, match='nonnegative'):
        cli._set_runtime_device('cann', True)


def test_counter_child_receives_runtime_device(cli, monkeypatch, tmp_path):
    capture = importlib.import_module(cli.__package__ + '._capture')
    calls = []

    def collect(command, output, **kwargs):
        calls.append((command, kwargs['env']))
        return {}

    monkeypatch.setattr(capture, 'capture_backend',
                        lambda name: SimpleNamespace(collect_counters=collect))
    monkeypatch.setattr(capture, 'export_capture', lambda *a: None)
    args, target = arguments(cli, monkeypatch, '--backend', 'cann', '--device',
                             '4', '--detail', 'auto')
    args.name = str(tmp_path / 'bundle')
    args.counters = True
    capture.run_capture(
        args, target,
        lambda *a: pytest.fail('outer launcher executed user app'))
    command, env = calls.pop()
    index = command.index('--device')
    assert command[index + 1] == '4'
    assert command[-2:] == ['ordinary.py', '--user-arg']
    assert env[capture.INTERNAL_ENV] == '1'


@pytest.mark.parametrize('exit_code', ['0', 'None'])
def test_successful_application_exit_finishes_collection(
        cli, monkeypatch, tmp_path, exit_code):
    script = tmp_path / 'ordinary.py'
    script.write_text('import sys\nraise SystemExit(' + exit_code + ')\n')
    monkeypatch.setenv('FLAGPRISM_CAPTURE_INTERNAL', '1')
    events = []
    monkeypatch.setattr(cli, 'finalize', lambda: events.append('finalized'))
    args, _ = arguments(cli, monkeypatch, '--backend', 'cann')
    cli.run_profiling(args, [str(script)])
    assert events == ['finalized']


def test_application_error_preserves_traceback_and_finalization_error(
        cli, monkeypatch, tmp_path, capsys):
    script = tmp_path / 'ordinary.py'
    script.write_text(
        'try:\n    raise KeyError("cause")\nexcept KeyError as error:\n    raise ValueError("original application failure") from error\n'
    )
    monkeypatch.setenv('FLAGPRISM_CAPTURE_INTERNAL', '1')

    def fail_finalize():
        raise RuntimeError('collector flush failed')

    monkeypatch.setattr(cli, 'finalize', fail_finalize)
    args, _ = arguments(cli, monkeypatch, '--backend', 'cann')
    original_argv = sys.argv
    with pytest.raises(ValueError,
                       match='original application failure') as caught:
        cli.run_profiling(args, [str(script)])
    assert isinstance(caught.value.__cause__, KeyError)
    assert any(frame.path == script for frame in caught.traceback)
    message = 'Profiling finalization also failed: collector flush failed'
    if hasattr(caught.value, 'add_note'):
        assert message in caught.value.__notes__
    else:
        assert message in capsys.readouterr().err
    assert sys.argv is original_argv


def test_nonzero_application_exit_is_preserved(cli, tmp_path):
    script = tmp_path / 'ordinary.py'
    script.write_text('raise SystemExit(7)\n')
    with pytest.raises(SystemExit) as caught:
        cli.execute_as_main(str(script), [])
    assert caught.value.code == 7
