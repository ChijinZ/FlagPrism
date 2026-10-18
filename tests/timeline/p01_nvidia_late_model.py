"""Actual retained-byte analysis and corruption rejection; no device replay."""
import argparse, hashlib, importlib.util, json, struct, subprocess, sys
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--output', type=Path, required=True)
p.add_argument('--input-root', type=Path, required=True)
p.add_argument('--model-module', type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True)
source = a.model_module
spec = importlib.util.spec_from_file_location('late_byte_model', source)
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)
root = a.input_root
if json.loads((root.parent / 'terminal.json').read_text())['returncode'] != 0:
    raise RuntimeError('Actual native math did not pass')
files = {
    p: hashlib.sha256(p.read_bytes()).hexdigest()
    for p in root.rglob('*') if p.is_file()
}
summaries = []
for name, tiles in [('runtime', 3), ('runtime', 7), ('constant', 3)]:
    folder = root / name
    manifest = json.loads((folder / 'sites.json').read_text())
    metadata = json.loads(
        (folder / ('allocation-' + str(tiles) + '-metadata.json')).read_text())
    raw = (folder / ('allocation-' + str(tiles) + '.bin')).read_bytes()
    decoded = model.decode_probe(manifest, metadata, raw)
    proof = model.analyze_probe(decoded)
    (a.output / (name + '-' + str(tiles) + '-model.json')).write_text(
        json.dumps(proof, indent=2))
    summaries.append(
        dict(case=name,
             tiles=tiles,
             programs=len(proof['programs']),
             commit_groups=[p['commit_groups'] for p in proof['programs']],
             consumer_edges=sum(
                 len(p['consumer_edges']) for p in proof['programs']),
             reuse_edges=sum(len(p['reuse']) for p in proof['programs']),
             raw_sha256=proof['raw_sha256']))
    if name == 'runtime' and tiles == 7:
        words = list(struct.unpack('<' + str(len(raw) // 8) + 'Q', raw))
        guard = metadata['guard_words']
        actors = manifest['actors']
        header = manifest['header_words']
        sites = {x['site_id']: x for x in manifest['sites']}
        sequence = [
            sites[x['site_id']]['kind']
            for x in decoded['programs'][0]['actors'][0]
        ]
        matrix_id = next(x['site_id'] for x in manifest['sites']
                         if x['kind'] == 'matrix_issue_bracket')
        wait = sequence.index('wait_bracket')
        barrier = next(i for i in range(wait + 1, len(sequence))
                       if sequence[i] == 'cta_barrier_after')
        copy = next(i for i, x in enumerate(sequence)
                    if x == 'copy_submit_after')
        rejects = []

        def reject(name, mutate):
            bad = list(words)
            mutate(bad)
            payload = struct.pack('<' + str(len(bad)) + 'Q', *bad)
            try:
                model.analyze_probe(
                    model.decode_probe(manifest, metadata, payload))
            except model.LateModelError as error:
                rejects.append(dict(case=name, reason=str(error)))
                return
            raise RuntimeError('Corrupt real capture accepted: ' + name)

        def set_site(bad, which, site):
            for actor in range(actors):
                bad[guard + (header + 4 * which) * actors + actor] = site

        reject('missing_actor', lambda b: b.__setitem__(guard + 127, 0))
        reject('mixed_actor_identity',
               lambda b: b.__setitem__(guard + 5 * actors + 127, 126))
        reject(
            'invalid_native_wait',
            lambda b: b.__setitem__(guard +
                                    (header + 4 * wait + 3) * actors, 9))
        reject('missing_completion_observation',
               lambda b: set_site(b, wait, matrix_id))
        reject('missing_publication_cut',
               lambda b: set_site(b, barrier, matrix_id))
        base = decoded['programs'][0]['shared_base']
        reject(
            'copy_outside_actual_allocation',
            lambda b: b.__setitem__(guard + (header + 4 * copy + 3) * actors,
                                    (16 << 32) |
                                    (base + metadata['shared_bytes'] + 16)))
        reject(
            'copy_source_bytes_exceed_destination',
            lambda b: b.__setitem__(guard + (header + 4 * copy + 3) * actors,
                                    (17 << 32) | base))
        matrix = sequence.index('matrix_issue_bracket')
        reuse_barrier = next(i for i in range(matrix + 1, len(sequence))
                             if sequence[i] == 'cta_barrier_after')
        reject('missing_consumer_retirement_cut',
               lambda b: set_site(b, reuse_barrier, matrix_id))
        if any('members' in row and row['kind'] == 'shared_load_issue_bracket'
               for row in manifest['sites']):
            bad_manifest = json.loads(json.dumps(manifest))
            row = next(row for row in bad_manifest['sites']
                       if row['kind'] == 'shared_load_issue_bracket')
            row['members'][0][
                'native_operation'] = 'llvm.nvvm.ldmatrix.sync.aligned.m8n8.x1.b16.p3'
            try:
                model.decode_probe(bad_manifest, metadata, raw)
            except model.LateModelError as error:
                rejects.append(
                    dict(case='forged_consumer_geometry', reason=str(error)))
            else:
                raise RuntimeError('Unmodeled ldmatrix geometry was accepted')
        (a.output / 'corruption-rejections.json').write_text(
            json.dumps(rejects, indent=2))
for path, sha in files.items():
    if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
        raise RuntimeError('Original actual capture changed')
(a.output / 'result.json').write_text(
    json.dumps(dict(
        status='actual_retained_byte_model_and_corruption_rejections_passed',
        cases=summaries,
        original_files_unchanged=len(files),
        source_overlay=True,
        machine_site_binding_verified=False,
        time_flows_qualified=False),
               indent=2))
