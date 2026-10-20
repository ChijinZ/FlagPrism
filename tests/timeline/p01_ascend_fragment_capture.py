"""Exercise installed automatic and offline analysis on a real retained capture."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--capture', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True)
    clone = args.output / 'timeline'
    shutil.copytree(args.directory, clone)
    from flagtree.profiler.timeline_capture_store import load_capture
    from flagtree.profiler.timeline_ascend_fragment_store import (
        inspect_capture_fragments, load_fragment_paths)
    capture = load_capture(clone, args.capture)
    raw_file = clone / capture['raw_file']
    raw_sha = hashlib.sha256(raw_file.read_bytes()).hexdigest()
    result = inspect_capture_fragments(clone,
                                       capture,
                                       deadline=time.monotonic() + 60)
    if result['status'] != 'fragment_paths_recomputed' or result[
            'checked_regions'] < 2:
        raise RuntimeError('Installed automatic analysis failed: ' +
                           json.dumps(result))
    first = json.loads((clone / result['report_file']).read_text())
    if not any(
            member.get('callee') for actor in first['actors']
            for region in actor['regions']
            for member in region.get('members', [])):
        raise RuntimeError('Actual report contains no source-associated call')
    # Cached capture annotations are deliberately not authoritative. A pure
    # offline replay must neither invoke a tool nor access an SDK/cache.
    capture['source_fragment_paths'] = dict(status='forged_cached_success')
    original_popen = subprocess.Popen

    def forbidden(*unused, **kwargs):
        raise RuntimeError('Offline analysis attempted to execute a tool')

    subprocess.Popen = forbidden
    retained = []
    try:
        offline = load_fragment_paths(
            clone, capture, retain=lambda name, **kw: retained.append(name))
    finally:
        subprocess.Popen = original_popen
    if offline != result or not retained:
        raise RuntimeError(
            'Offline reconstruction differs or has no input closure')
    prefix = clone / 'analysis/ascend-fragments' / capture['owner']['binary_id']
    graph = prefix / '0.original.stdout'
    before = graph.read_bytes()
    graph.write_bytes(before + b' ')
    try:
        load_fragment_paths(clone, capture)
    except ValueError:
        changed_graph_rejected = True
    else:
        raise RuntimeError('Changed graph accepted')
    finally:
        graph.write_bytes(before)
    changed = copy.deepcopy(capture)
    changed['metadata']['compiler_metadata']['hash'] = '0' * 64
    try:
        load_fragment_paths(clone, changed)
    except ValueError:
        changed_compiler_rejected = True
    else:
        raise RuntimeError('Different compiler input accepted')
    if hashlib.sha256(raw_file.read_bytes()).hexdigest() != raw_sha:
        raise RuntimeError('Analysis changed retained raw')
    (args.output / 'result.json').write_text(
        json.dumps(dict(
            status='installed_automatic_and_offline_fragment_analysis_passed',
            automatic=result,
            input_closure_members=len(retained),
            offline_tool_execution=False,
            ignored_cached_status=True,
            changed_graph_rejected=changed_graph_rejected,
            changed_compiler_rejected=changed_compiler_rejected,
            raw_unchanged=True,
            device_executed=False,
            native_schedule_qualified=False),
                   indent=2))


if __name__ == '__main__':
    main()
