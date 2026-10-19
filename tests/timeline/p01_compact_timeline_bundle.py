"""Use a real retained bundle to check compact HTML without replay or data loss."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from flagtree.profiler import _report
from flagtree.profiler.execution_view import write_view
from flagtree.profiler.export_refs import restore


def run(bundle, output):
    output.mkdir(parents=True, exist_ok=False)
    report = json.loads((bundle / 'report/report.json').read_text())
    original = json.loads((bundle / 'ai/observations.json').read_text())
    records = restore(
        json.loads((bundle / 'ai/fine_grained.json').read_text()),
        original)['records']
    def machine_files(root):
        return {
            str(p.relative_to(root)):
            hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*')
            if p.is_file() and p.suffix in ('.json', '.jsonl')
        }

    retained = output / 'retained'
    shutil.copytree(bundle, retained)
    before = machine_files(retained)
    write_view(retained, records, compact_html=True)
    _report.write_timeline_page(retained)
    if before != machine_files(retained):
        raise RuntimeError(
            'Timeline navigation changed saved machine-readable evidence')
    _report.write_manifest(retained, report)
    manifest = json.loads((retained / 'manifest.json').read_text())
    old_manifest = json.loads((bundle / 'manifest.json').read_text())
    for name, row in old_manifest['files'].items():
        if name not in ('report/index.html', 'report/execution.html'):
            if manifest['files'].get(name) != row:
                raise RuntimeError(
                    'Compact navigation changed retained evidence: ' + name)
    original_bytes = sum(p.stat().st_size for p in bundle.rglob('*')
                         if p.is_file())
    retained_bytes = sum(p.stat().st_size for p in retained.rglob('*')
                         if p.is_file())
    if retained_bytes >= original_bytes or retained_bytes > 64 * 1024 * 1024:
        raise RuntimeError(
            'Complete retained bundle still exceeds its fixed budget')
    (output / 'result.json').write_text(
        json.dumps(dict(
            status=
            'real_retained_compact_HTML_preserves_machine_data_and_fits_complete_bundle_budget',
            original_bytes=original_bytes,
            compact_bytes=retained_bytes,
            machine_files_compared=len(before),
            application_replayed=False,
            limitations=[
                'HTML-only retained-data check; does not certify a new device capture.'
            ]),
                   indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.bundle, args.output)
