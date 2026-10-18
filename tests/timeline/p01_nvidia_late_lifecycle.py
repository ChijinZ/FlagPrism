"""Actual-raw lifecycle-to-event attribution plus an exact partial-reuse fixture."""
import argparse
import hashlib
import json
from pathlib import Path


def need(value, message):
    if not value:
        raise RuntimeError(message)


def run(timeline, output, *, model, async_model, adapter, raw_decoder):
    output.mkdir(parents=True)
    original = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in timeline.rglob('*') if p.is_file()
    }
    reports = []
    for item in json.loads((timeline / 'index.json').read_text())['captures']:
        cap = json.loads((timeline / item['capture_file']).read_text())
        plan, layout = cap['owner']['plan'], cap['owner']['layout']
        raw = (timeline / cap['raw_file']).read_bytes()
        decoded = raw_decoder.decode_late_raw(plan, raw, slots=layout['slots'])
        report = async_model.derive_late_async(
            decoded,
            plan,
            shared_bytes=cap['metadata']['compiler_metadata']['shared'])
        need(report['status'] == 'dynamic_byte_model_consistent',
             'Actual model failed')
        native = {s['site_id']: s for s in plan['sites']}
        programs = {p['program_id']: p for p in decoded['programs']}
        generations, reused = 0, 0
        for p in report['programs']:
            events = programs[p['program']]['observers'][0]['events']
            commits = [
                i for i, event in enumerate(events)
                if native[event['site_id']]['kind'] == 'commit_after'
            ]
            for g in p['generations']:
                generations += 1
                need(
                    sum(length for _, length in g['shared_ranges']) ==
                    g['footprint_bytes'], 'Physical range byte count mismatch')
                need(
                    all(0 <= start < start + length <= p['shared_bytes']
                        for start, length in g['shared_ranges']),
                    'Range outside actual allocation')
                if g['kind'] == 'async':
                    commit = g['commit_sequence']
                    need(
                        commit in commits
                        and all(i < commit for i in g['submit_sequences']),
                        'Commit is not after original submissions')
                    rank = commits.index(commit)
                    completed = next(
                        i for i, e in enumerate(events)
                        if native[e['site_id']]['kind'] == 'wait_bracket'
                        and sum(c < i for c in commits) - e['payload'] > rank)
                    need(g['completion_observed_sequence'] == completed,
                         'Completion was not first covering actual wait')
                    need(
                        g['completion_observation_kind'] ==
                        'native_wait_return',
                        'Completion incorrectly claims an engine instant')
                else:
                    completed = next(
                        i for i, e in enumerate(events)
                        if i > max(g['submit_sequences']) and native[
                            e['site_id']]['kind'] == 'cta_barrier_after')
                    need(g['completion_observed_sequence'] == completed,
                         'Sync completion mismatch')
                publication = next(
                    i for i, e in enumerate(events) if i >= completed
                    and native[e['site_id']]['kind'] == 'cta_barrier_after')
                need(g['publication_barrier_sequence'] == publication,
                     'First publication was overwritten')
                need(all(i > publication for i in g['consumer_sequences']),
                     'Consumer precedes publication')
            for edge in p['reuse']:
                reused += 1
                need(
                    sum(length
                        for _, length in edge['overlapping_shared_ranges']) ==
                    edge['overlapping_bytes'],
                    'Reuse range byte count mismatch')
            need(p['reuse'],
                 'Actual test did not exercise physical byte reuse')
        canonical = adapter.canonicalize_late_capture(raw,
                                                      owner=cap['owner'],
                                                      metadata=cap['metadata'])
        roles = async_model.lifecycle_roles(report)
        observers = {o['id']: o for o in canonical['observers']}
        annotated = 0
        for event in canonical['events']:
            observer = observers[event['observer_id']]
            key = (observer['attributes']['nvidia.logical_program'],
                   event['coverage']['nvidia.raw_ordinal'])
            actual = event['coverage'].get('nvidia.dynamic_dependencies', [])
            need(actual == roles.get(key, []),
                 'Lifecycle attached to another raw ordinal/program')
            annotated += bool(actual)
        need(annotated > 0,
             'No actual lifecycle metadata reaches common time events')
        need(
            not report['time_flows_qualified']
            and not report['clock_comparison_qualified'],
            'Lifecycle falsely grants temporal rights')
        reports.append(
            dict(invocation=cap['owner']['invocation_id'],
                 generations=generations,
                 physical_reuse_edges=reused,
                 annotated_events=annotated))
    # Synthetic CPU regression: the third producer covers four physical bytes,
    # split between two current owners. Historical footprints must not count six.
    base = 4096
    sites = {
        1: dict(kind='shared_store_after', destination_bytes=4),
        2: dict(kind='cta_barrier_after'),
        3: dict(kind='shared_store_after', destination_bytes=2),
        4: dict(kind='shared_load_native_bracket', destination_bytes=4)
    }
    for site_id, site in sites.items():
        site['site_id'] = site_id
    sequence = [(1, base | (4 << 32)), (2, 0), (3, base | (2 << 32)), (2, 0),
                (1, base | (4 << 32)), (2, 0), (2, 0), (4, base | (4 << 32))]
    fixture = model.analyze_probe(
        dict(programs=[
            dict(program=0,
                 shared_base=base,
                 actors=[[
                     dict(site_id=site, payload=payload)
                     for site, payload in sequence
                 ]])
        ],
             sites=sites,
             shared_bytes=16,
             raw_sha256='0' * 64))
    p = fixture['programs'][0]
    reused = [e for e in p['reuse'] if e['sequence'] == 4]
    need(
        sorted(e['overlapping_bytes'] for e in reused) == [2, 2],
        'Partial overwrite counted stale historical ownership')
    need(p['consumer_edges'][0]['publication_barrier'] == 5,
         'Later unrelated barrier replaced the first publication')
    # Two submissions in one real mechanism group must retain their own
    # physical ranges as well as the group's aggregate range. CPU fixture only.
    async_sites = {
        1: dict(site_id=1, kind='copy_submit_after', destination_bytes=16),
        2: dict(site_id=2, kind='commit_after'),
        3: dict(site_id=3, kind='wait_bracket'),
        4: dict(site_id=4, kind='cta_barrier_after')
    }
    actor = [
        dict(site_id=1, payload=base | (16 << 32)),
        dict(site_id=1, payload=(base + 16) | (16 << 32)),
        dict(site_id=2, payload=0),
        dict(site_id=3, payload=0),
        dict(site_id=4, payload=0)
    ]
    multi = model.analyze_probe(
        dict(programs=[dict(program=0, shared_base=base, actors=[actor])],
             sites=async_sites,
             shared_bytes=64,
             raw_sha256='0' * 64))
    multi[
        'status'] = 'dynamic_byte_model_consistent'  # explicit CPU model fixture
    role = async_model.lifecycle_roles(multi)
    need(
        role[(0, 0)][0]['shared_ranges'] == [[0, 16]]
        and role[(0, 1)][0]['shared_ranges'] == [[16, 16]]
        and role[(0, 0)][0]['generation_shared_ranges'] == [[0, 32]],
        'Individual submission incorrectly uses whole-group footprint')
    for filename, digest in original.items():
        need(
            hashlib.sha256(Path(filename).read_bytes()).hexdigest() == digest,
            'Original capture changed')
    result = dict(
        status=
        'actual_dynamic_lifecycle_raw_event_attribution_and_partial_reuse_fixture_passed_no_time_flows',
        actual=reports,
        cpu_fixture_only=dict(
            reused_bytes=[e['overlapping_bytes'] for e in reused],
            first_publication=p['consumer_edges'][0]['publication_barrier'],
            separate_submission_ranges=True),
        original_files_unchanged=len(original),
        application_replayed=False)
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--timeline', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    from flagtree.profiler import timeline_nvidia_late_model as model
    from flagtree.profiler import timeline_nvidia_late_async as async_model
    from flagtree.profiler import timeline_events_nvidia_late as adapter
    from flagtree.profiler import timeline_nvidia_late_raw as raw_decoder
    run(a.timeline,
        a.output,
        model=model,
        async_model=async_model,
        adapter=adapter,
        raw_decoder=raw_decoder)


if __name__ == '__main__':
    main()
