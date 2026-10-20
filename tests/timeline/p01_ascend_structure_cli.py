"""Native actor indexing checks; execute with an explicitly built LLVM15 tool."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


parser = argparse.ArgumentParser()
parser.add_argument('--tool', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)

source = r'''
define i64 @actor(i64 %K, ptr addrspace(1) %record) {
entry:
  br label %body
body:
  %iteration = phi i64 [0, %entry], [%next, %body]
  %begin = call i64 asm sideeffect "MOV $0, SYS_CNT", "=l"()
  %calculation = add nsw i64 %iteration, 7
  %end = call i64 asm sideeffect "MOV $0, SYS_CNT", "=l"()
  %start_slot = getelementptr i64, ptr addrspace(1) %record, i64 2
  store volatile i64 %begin, ptr addrspace(1) %start_slot
  %end_slot = getelementptr i64, ptr addrspace(1) %record, i64 3
  store volatile i64 %end, ptr addrspace(1) %end_slot
  %next = add i64 %iteration, 1
  %again = icmp ult i64 %next, %K
  br i1 %again, label %body, label %exit
exit:
  ret i64 %calculation
}
'''


def invoke(name, text):
    path = args.output / (name + '.ll')
    path.write_text(text)
    result = subprocess.run([str(args.tool), str(path)],
                            stdin=subprocess.DEVNULL,
                            capture_output=True,
                            timeout=10)
    (args.output / (name + '.stdout')).write_bytes(result.stdout)
    (args.output / (name + '.stderr')).write_bytes(result.stderr)
    return path, result


path, result = invoke('loop-record', source)
need(result.returncode == 0, 'Valid actor indexing failed')
graph = json.loads(result.stdout)
need(graph['input_sha256'] == hashlib.sha256(path.read_bytes()).hexdigest(),
     'Index does not identify the exact input')
function = graph['functions'][0]
need(len(function['loops']) == 1, 'Real loop was not retained')
instructions = [i for b in function['blocks'] for i in b['instructions']]
clocks = [i for i in instructions if i.get('assembly') == 'MOV $0, SYS_CNT']
need(len(clocks) == 2 and all(i['side_effects'] for i in clocks),
     'Actual clock definitions were not preserved')
stores = [i for i in instructions if i['opcode'] == 'store']
need([i['operands'][0]['id'] for i in stores] == [i['id'] for i in clocks],
     'Stored endpoints lost their actual SSA identities')
need(all(i['volatile'] and not i['atomic'] for i in stores),
     'Record memory semantics were lost')
need(any(i['opcode'] == 'add' and i['nsw'] for i in instructions),
     'Overflow flags were not retained')

# A syntactically parseable module can still have a wrong predecessor/phi
# relation. Reject it before invoking LLVM dominator/loop analysis.
_, invalid = invoke('invalid-phi', source.replace('[%next, %body]',
                                                  '[%next, %exit]'))
need(invalid.returncode != 0 and b'failed verification' in invalid.stderr,
     'Invalid CFG/phi was treated as authoritative structure')

# Undefined values must not acquire a literal integer representation that
# a later loop/record rule could mistake for a real endpoint or bound.
_, poison = invoke('poison', 'define i64 @actor() { ret i64 poison }\n')
need(poison.returncode == 0, 'Poison diagnostic module failed to index')
operand = json.loads(poison.stdout)['functions'][0]['blocks'][0][
    'instructions'][0]['operands'][0]
need(operand.get('constant_status') == 'undefined_or_poison'
     and 'integer_hex' not in operand, 'Poison became a literal')

_, indirect = invoke('indirect', '''
define i64 @actor(ptr %callee) {
  %result = call i64 %callee()
  ret i64 %result
}
''')
need(indirect.returncode == 0, 'Indirect diagnostic module failed to index')
call = json.loads(indirect.stdout)['functions'][0]['blocks'][0][
    'instructions'][0]
need(call.get('indirect_call') is True and 'callee' not in call,
     'Indirect call was assigned a guessed callee')
_, long_triple = invoke('oversized-triple',
                       'target triple = "' + 'a' * 4097 + '"\n'
                       'define void @actor() { ret void }\n')
need(long_triple.returncode != 0
     and b'text budget exceeded' in long_triple.stderr,
     'Target triple bypassed the text budget')
print(json.dumps(dict(checks=5, status='passed', native_schedule_qualified=False)))
