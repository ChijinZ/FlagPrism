"""CPU replay of retained public bundles, plus adversarial evidence mutations.

Run inside the assigned server Docker, never as a device/math qualification:
python source_census_public_regression.py BACKEND PUBLIC_EVIDENCE.tgz [...]
"""
import ast
import copy
import json
from pathlib import Path
import sys
import shutil
import tarfile
import tempfile

from collections import Counter
from source_census_assertions import read_view, validate_bundle, validate_document


def rejected(document, backend, mutate):
    changed = copy.deepcopy(document)
    mutate(changed)
    try:
        validate_document(changed, backend)
    except (AssertionError, ValueError, KeyError, IndexError):
        return
    raise AssertionError('corrupted public evidence was accepted')


def driver_wrappers(bundle, backend, document, fine):
    """Run the real pure driver validator on each retained capture projection.

    Projection filters the actual capture/rows after reference restoration;
    it does not invent bytes, counts, identities, or source metadata.
    """
    if backend == 'ascend':
        return 0  # Ascend main uses the shared validator directly.
    directory = 'nvidia' if backend == 'nvidia' else 'enflame'
    source = Path(__file__).parent / directory / 'automatic_hardware.py'
    name = 'validate_bundle' if backend == 'nvidia' else 'check'
    node = next(n for n in ast.parse(source.read_text()).body
                if isinstance(n, ast.FunctionDef) and n.name == name)
    namespace = dict(json=json,
                     Counter=Counter,
                     read_view=read_view,
                     validate_census_bundle=validate_bundle)
    exec(
        compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'),
        namespace)
    plan = read_view(bundle, 'observation_plan.json', document)
    for capture in document['captures']:
        cid = capture['capture_id']
        projected = dict(document,
                         captures=[capture],
                         observations=[
                             row for row in document['observations']
                             if row['capture_id'] == cid
                         ])
        projected_fine = dict(fine,
                              records=[
                                  row for row in fine['records']
                                  if row['capture_id'] == cid
                              ])
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            (target / 'ai').mkdir()
            (target / 'report').mkdir()
            for filename, value in [('observations.json', projected),
                                    ('fine_grained.json', projected_fine),
                                    ('observation_plan.json', plan)]:
                (target / 'ai' / filename).write_text(json.dumps(value))
            shutil.copyfile(bundle / 'report/fine_grained.html',
                            target / 'report/fine_grained.html')
            if (bundle / 'ai/export_timing.json').exists():
                shutil.copyfile(bundle / 'ai/export_timing.json',
                                target / 'ai/export_timing.json')
            namespace[name](target)
    return len(document['captures'])


def main():
    backend = sys.argv[1]
    results = []
    negatives = 0
    wrappers = 0
    for archive in sys.argv[2:]:
        with tempfile.TemporaryDirectory() as tmp:
            with tarfile.open(archive) as tar:
                tar.extractall(tmp, filter='data')
            for path in sorted(Path(tmp).rglob('ai/observations.json')):
                document = json.loads(path.read_text())
                # Explicit manual/interval bundles retain their separate tests.
                if not document['captures'] or not all(
                        'source_census' in c.get('raw_encoding', '')
                        for c in document['captures']):
                    continue
                bundle = path.parent.parent
                document, cells, summaries, fine = validate_bundle(
                    bundle, backend)
                wrappers += driver_wrappers(bundle, backend, document, fine)
                assert document['observations']
                row = document['observations'][0]
                cases = [
                    lambda d: d['observations'][0].update(count=row['count'] +
                                                          1),
                    lambda d: d['observations'][0].update(program=row['program'
                                                                      ] + 1),
                    lambda d: d['observations'][0].update(invocation_id=
                                                          'wrong-launch'),
                    lambda d: d['observations'][0].update(
                        clock={'domain': 'fabricated'}),
                    lambda d: d['observations'].append(
                        copy.deepcopy(d['observations'][0])),
                    lambda d: d['observations'].pop(0),
                    lambda d: d['captures'][0].update(raw_sha256='0' * 64),
                    lambda d: d['observations'][0]['compiler_site'].update(
                        origin={}),
                ]
                for mutate in cases:
                    rejected(document, backend, mutate)
                    negatives += 1
                results.append(
                    dict(archive=Path(archive).name,
                         bundle=str(bundle.relative_to(tmp)),
                         captures=summaries,
                         cells=len(cells)))
    assert results, 'no actual public census bundles found'
    print(
        json.dumps(dict(
            status='pass',
            backend=backend,
            bundles=results,
            mutation_rejections=negatives,
            driver_capture_projections=wrappers,
            scope='CPU public evidence replay; no device or math execution'),
                   indent=2))


if __name__ == '__main__':
    main()
