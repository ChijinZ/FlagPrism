"""Valid LLVM control-flow faults for the finite selected-loop bracket rule."""
import json
from pathlib import Path
import subprocess


def check_native_loop_cases(rules, fragments, tool, output):
    output = Path(output)
    output.mkdir()
    variants = [
        ('selected_pair', '%selected', '',
         'br i1 %selected, label %finish, label %latch', True),
        ('constant_pair', 'true', '',
         'br i1 true, label %finish, label %latch', True),
        ('frozen_pair', '%stable', '%stable = freeze i1 undef',
         'br i1 %stable, label %finish, label %latch', True),
        ('different_end_guard', '%selected', '',
         'br i1 %escape, label %finish, label %latch', False),
        ('inverted_end_guard', '%selected', '',
         'br i1 %selected, label %latch, label %finish', False),
        ('exit_before_end', '%selected', '',
         'br i1 %escape, label %exit, label %finish', False),
        ('cycle_before_end', '%selected', '',
         'br i1 %escape, label %work, label %finish', False),
        ('undefined_guard', 'undef', '',
         'br i1 undef, label %finish, label %latch', False),
    ]
    functions = []
    for name, selected, setup, transfer, _ in variants:
        functions.append('''
define void @''' + name + '''(i1 %selected, i1 %escape, i32 %n) {
entry:
  ''' + setup + '''
  br label %header
header:
  %i = phi i32 [0, %entry], [%next, %latch]
  %active = icmp slt i32 %i, %n
  br i1 %active, label %choose, label %exit
choose:
  br i1 ''' + selected + ''', label %begin, label %latch
begin:
  call void asm sideeffect "begin", ""()
  br label %work
work:
  call void asm sideeffect "body", ""()
  ''' + transfer + '''
finish:
  call void asm sideeffect "end", ""()
  br label %latch
latch:
  %next = add i32 %i, 1
  br label %header
exit:
  ret void
}
''')
    functions.append('''
define i1 @float_less(float %a, float %b) {
  %c = fcmp olt float %a, %b
  ret i1 %c
}
define i1 @float_greater(float %a, float %b) {
  %c = fcmp ogt float %a, %b
  ret i1 %c
}
define i64 @atomic_add(ptr %p, i64 %x) {
  %y = atomicrmw add ptr %p, i64 %x monotonic
  ret i64 %y
}
define i64 @atomic_xor(ptr %p, i64 %x) {
  %y = atomicrmw xor ptr %p, i64 %x monotonic
  ret i64 %y
}
define void @indirect_target(ptr %f) {
  call void %f()
  ret void
}
''')
    path = output / 'loops.ll'
    path.write_text('\n'.join(functions))
    with (output /
          'graph.json').open('xb') as out, (output /
                                            'stderr.log').open('xb') as err:
        subprocess.run([str(tool), str(path)],
                       stdout=out,
                       stderr=err,
                       check=True,
                       timeout=20)
    graph = json.loads((output / 'graph.json').read_text())
    rows = []
    for name, _, _, _, expected in variants:
        function = next(f for f in graph['functions'] if f['name'] == name)
        index = fragments._Index(function)
        markers = {
            i['assembly']: i['id']
            for b in function['blocks']
            for i in b['instructions'] if 'assembly' in i
        }
        context = fragments._loop_context(index, function,
                                          [markers['begin'], markers['end']])
        result = rules.selected_loop_bracket(index,
                                             function,
                                             begin_id=markers['begin'],
                                             end_id=markers['end'],
                                             context=context)
        if (result['status'] == 'selected_llvm_bracket_within_iteration'
            ) != expected:
            raise RuntimeError('Incorrect loop bracket result: ' + name + ' ' +
                               json.dumps(result))
        rows.append(dict(name=name, expected_checked=expected, result=result))
    for name, opcode in [('float_less', 'fcmp'), ('float_greater', 'fcmp'),
                         ('atomic_add', 'atomicrmw'),
                         ('atomic_xor', 'atomicrmw'),
                         ('indirect_target', 'call')]:
        function = next(f for f in graph['functions'] if f['name'] == name)
        instruction = next(i for b in function['blocks']
                           for i in b['instructions'] if i['opcode'] == opcode)
        if fragments._signature(instruction,
                                fragments._Index(function)) is not None:
            raise RuntimeError(
                'Operation with missing indexed semantics accepted: ' + name)
        rows.append(
            dict(name=name,
                 expected_checked=False,
                 result=dict(status='opaque_operation_structure')))
    return rows
