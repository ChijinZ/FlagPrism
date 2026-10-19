"""Reject malformed cached late manifests before any kernel allocation/launch.

Actual successful capture's compiler files are used; function handles below are
CPU contract placeholders, never submitted to a device.
"""
import argparse
import copy
import json
from pathlib import Path
from flagtree.profiler.hooks.timeline_late import LateTimelineHook


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--timeline', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    row = json.loads((a.timeline / 'index.json').read_text())['captures'][0]
    from flagtree.profiler.timeline_capture_store import load_capture_file
    capture = load_capture_file(a.timeline / row['capture_file'])
    metadata = capture['metadata']
    group = metadata['late_metadata_group']
    key = next(key for key in group if key.endswith('json'))
    original = json.loads(Path(group[key]).read_text())
    hook = LateTimelineHook(None,
                            observation_plan=dict(
                                automatic=True,
                                timeline=True,
                                max_sites=8,
                                output_selection={'programs': None}),
                            staging_base=a.output / 'capture')
    hook.init_handle(None, 123, metadata['late_name'], group,
                     metadata['binary_id'])
    rejects = []
    for case in ('smaller_actors', 'smaller_capacity', 'missing_ordinary',
                 'wrong_tool'):
        changed = copy.deepcopy(original)
        plan = changed['flagprism_late_manifest']
        if case == 'smaller_actors':
            plan['actors'] = 2
            plan['segment_words'] //= 2
            changed['profile_scratch_size'] //= 2
        elif case == 'smaller_capacity':
            plan['capacity_per_program'] //= 2
            plan['segment_words'] = plan['actors'] * (
                6 + 4 * plan['capacity_per_program'])
            changed['profile_scratch_size'] = plan['segment_words'] * 8
        elif case == 'missing_ordinary':
            del changed['flagprism_late_ordinary_llvm_zlib_b64']
        else:
            plan['compiler_binding']['tool_sha256'] = '0' * 64
        file = a.output / (case + '.json')
        file.write_text(json.dumps(changed))
        forged_group = dict(group)
        forged_group[key] = str(file)
        try:
            hook.init_handle(None, 124, metadata['late_name'], forged_group,
                             metadata['binary_id'])
        except (ValueError, RuntimeError) as error:
            rejects.append(dict(case=case, reason=str(error)))
        else:
            raise RuntimeError('Malformed cached producer admitted: ' + case)
        if hook.timeline_pool.invocation_ids or hook.timeline_pool.pending_bytes:
            raise RuntimeError('Malformed manifest created a device owner')
    hook.timeline_pool.close()
    (a.output / 'result.json').write_text(
        json.dumps(dict(
            status=
            'actual_compiler_cache_malformed_layout_rejected_before_allocation_no_device_work',
            rejects=rejects),
                   indent=2))


if __name__ == '__main__':
    main()
