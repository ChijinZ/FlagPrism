"""CPU-only front-door checks using tiny synthetic source trees."""
from pathlib import Path
import subprocess
import sys

import pytest

MODULE = Path(__file__).with_name('build_from_source.py')


@pytest.mark.parametrize('source_name', ['component', 'flagtree'])
@pytest.mark.parametrize('location', ['self', 'child', 'symlink'])
def test_workdir_inside_source_rejected_before_dependencies_or_output(
        tmp_path, source_name, location):
    sources = {name: tmp_path / name for name in ('component', 'flagtree')}
    for source in sources.values():
        source.mkdir()
        (source / 'sentinel').write_text('unchanged')
    source = sources[source_name]
    work = source if location == 'self' else source / 'output'
    if location == 'symlink':
        alias = tmp_path / 'alias'
        alias.symlink_to(source, target_is_directory=True)
        work = alias / 'output'
    before = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob('*'))
    result = subprocess.run([
        sys.executable,
        str(MODULE), '--component',
        str(sources['component']), '--flagtree',
        str(sources['flagtree']), '--workdir',
        str(work), '--llvm-prefix', '/missing', '--tops-prefix', '/missing',
        '--json-include', '/missing'
    ],
                            capture_output=True,
                            text=True)
    assert result.returncode == 2
    assert f'--workdir must be outside the {source_name} source' in result.stderr
    assert 'missing required installed dependency' not in result.stderr
    assert sorted(str(p.relative_to(tmp_path))
                  for p in tmp_path.rglob('*')) == before
    assert all(
        (p / 'sentinel').read_text() == 'unchanged' for p in sources.values())
