"""Faults applied to a real selected actor fragment; server-Docker only."""
import copy
import json
from pathlib import Path
import subprocess


def check_fragment_faults(rules, original, adapted, **options):
    result = rules.bind_fragment_paths(original, adapted, **options)
    checked = [
        r for r in result['regions']
        if r['status'] == 'llvm_observed_fragment_operations_bound'
    ]
    witness = next(r for r in checked if any(
        m.get('callee') for m in r['members']))
    site_id = witness['site_id']
    rows = []

    def run(name, before=None, after=None, changed_options=None):
        try:
            report = rules.bind_fragment_paths(
                original if before is None else before,
                adapted if after is None else after,
                **(options if changed_options is None else changed_options))
            region = next(r for r in report['regions']
                          if r['site_id'] == site_id)
            if region['status'] != 'unverified':
                raise RuntimeError('Incorrect fragment accepted: ' + name)
            reason = region['reason']
        except ValueError as error:
            reason = str(error)
        rows.append(dict(name=name, rejected=True, reason=reason))

    changed = dict(options, original_input_sha256='0' * 64)
    run('different_original_input', changed_options=changed)
    changed = dict(options, adapted_input_sha256='0' * 64)
    run('different_adapted_input', changed_options=changed)
    changed = dict(options, selected_source_ids=[])
    run('source_not_selected', changed_options=changed)

    changed = copy.deepcopy(adapted)
    actor = next(f for f in changed['functions']
                 if f['name'] == options['function'])
    member = next(m for m in witness['members'] if m.get('callee'))
    instruction = next(i for b in actor['blocks'] for i in b['instructions']
                       if i['id'] == member['adapted_id'])
    instruction['callee'] = 'different_actual_callee'
    run('different_actual_call', after=changed)

    changed = copy.deepcopy(adapted)
    actor = next(f for f in changed['functions']
                 if f['name'] == options['function'])
    carrier = next(i for b in actor['blocks'] for i in b['instructions']
                   if i['id'] == witness['adapted_carrier_id'])
    carrier['assembly'] = '/* unrelated source carrier */'
    run('missing_actual_source_carrier', after=changed)

    changed = copy.deepcopy(adapted)
    actor = next(f for f in changed['functions']
                 if f['name'] == options['function'])
    blocks = {i['id']: b for b in actor['blocks'] for i in b['instructions']}
    begin_block = blocks[witness['begin_id']]
    end_block = blocks[witness['end_id']]
    begin_block['successors'].append(end_block['id'])
    run('bypass_source_body_between_endpoints', after=changed)

    changed = copy.deepcopy(options)
    site = next(s for s in changed['manifest']['dynamic_sites']
                if s['site_id'] == site_id)
    site['original_instruction_count'] += 1
    run('different_declared_body_extent', changed_options=changed)
    return rows


def check_native_fragment_edges(rules, tool, output):
    """Use verified LLVM inputs for irreducible CFG and opaque-type faults."""
    output = Path(output)
    output.mkdir()
    many = ', '.join(['i64'] * 128)
    arguments = ', '.join(['i64 %x'] * 128)
    source = '''
declare void @many(''' + many + ''')
define void @cycle(i1 %entry, i1 %exit) {
E:
  br i1 %entry, label %B, label %X
B:
  call void asm sideeffect "begin", ""()
  br label %M
M:
  call void asm sideeffect "body", ""()
  br label %C
C:
  call void asm sideeffect "carrier", ""()
  br i1 %exit, label %Z, label %X
X:
  br label %M
Z:
  call void asm sideeffect "end", ""()
  ret void
}
define <4 x i32> @vector4(<4 x i32> %a, <4 x i32> %b) {
  %c = add <4 x i32> %a, %b
  ret <4 x i32> %c
}
define <8 x i16> @vector8(<8 x i16> %a, <8 x i16> %b) {
  %c = add <8 x i16> %a, %b
  ret <8 x i16> %c
}
define ptr @gep_vector(ptr %p, i64 %i) {
  %q = getelementptr <4 x i32>, ptr %p, i64 %i
  ret ptr %q
}
define void @arity(i64 %x) {
  call void @many(''' + arguments + ''')
  ret void
}
'''
    path = output / 'faults.ll'
    path.write_text(source)
    with (output /
          'graph.json').open('xb') as out, (output /
                                            'stderr.log').open('xb') as err:
        subprocess.run([str(tool), str(path)],
                       stdout=out,
                       stderr=err,
                       check=True,
                       timeout=20)
    graph = json.loads((output / 'graph.json').read_text())
    cycle = next(f for f in graph['functions'] if f['name'] == 'cycle')
    index = rules._Index(cycle)
    paths = rules._Paths(index, cycle)
    ids = {
        i['assembly']: i['id']
        for b in cycle['blocks']
        for i in b['instructions'] if 'assembly' in i
    }
    if cycle['loops'] or not paths.mandatory(ids['begin'], ids['end'],
                                             ids['body']):
        raise RuntimeError(
            'Native fixture does not reproduce irreducible endpoint path')
    if paths.mandatory(ids['carrier'], ids['end'], ids['body']):
        raise RuntimeError('Carrier-after-member irreducible path accepted')
    vectors = [
        f for f in graph['functions'] if f['name'] in ('vector4', 'vector8')
    ]
    for function in vectors:
        operation = next(i for b in function['blocks']
                         for i in b['instructions'] if i['opcode'] == 'add')
        if rules._signature(operation, rules._Index(function)) is not None:
            raise RuntimeError('Opaque vector type treated as complete')
    function = next(f for f in graph['functions'] if f['name'] == 'gep_vector')
    operation = next(i for b in function['blocks'] for i in b['instructions']
                     if i['opcode'] == 'getelementptr')
    if rules._signature(operation, rules._Index(function)) is not None:
        raise RuntimeError('Opaque GEP element type treated as complete')
    arity = next(f for f in graph['functions'] if f['name'] == 'arity')
    index = rules._Index(arity)
    call = next(i for b in arity['blocks'] for i in b['instructions']
                if i.get('callee') == 'many')
    index.work = 999990
    try:
        rules._signature(call, index)
    except ValueError as error:
        if 'budget' not in str(error):
            raise
    else:
        raise RuntimeError(
            'High-arity signature bypassed remaining work budget')
    return [
        dict(name='irreducible_carrier_after_body', rejected=True),
        dict(name='opaque_vector_shape_and_element_type', rejected=True),
        dict(name='opaque_gep_element_type', rejected=True),
        dict(name='high_arity_signature_work', rejected=True)
    ]
