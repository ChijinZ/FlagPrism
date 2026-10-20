"""Finite pre-observer Triton State-pointer use check.

Use real parsed MLIR values, never textual SSA names. This is a qualification
helper, not an arbitrary-kernel alias analysis. Unknown pointer uses fail.
The caller must bind this module to the captured compilation and independently
check the actual GCU before/after preservation certificate. Neither check alone
qualifies a lowered State writer, a native timing boundary, or allocation sizes.
"""


def check_state_source_uses(module, *, function_name, state_index):

    def need(ok, message):
        if not ok:
            raise ValueError(message)

    operations = []
    module.walk(operations.append)
    need(0 < len(operations) <= 20000, 'State source operation bound')
    functions = [op for op in operations if op.get_name() == 'tt.func']
    need(len(functions) == 1, 'State source requires one Triton function')
    function = module.get_function(function_name)
    need(function is not None, 'State source function missing')
    need(
        type(state_index) is int
        and 0 <= state_index < function.get_num_args(), 'State source index')
    state = function.args(state_index)
    need(str(state.get_type()) == '!tt.ptr<i32>', 'State source type')
    pointers = {state.id()}
    propagators = {
        'tt.splat', 'tt.addptr', 'tt.broadcast', 'tt.expand_dims', 'tt.trans',
        'tt.reshape'
    }
    # MLIR walk order need not be dominance order. No region argument is
    # admitted: unknown loop/branch pointer forwarding is deliberately refused.
    users = {}
    for op in operations:
        if op.get_name() in propagators and op.get_num_operands():
            users.setdefault(op.get_operand(0).id(), []).append(op)
    pending = [state.id()]
    while pending:
        for op in users.get(pending.pop(), ()):
            for i in range(op.get_num_results()):
                value = op.get_result(i).id()
                if value not in pointers:
                    pointers.add(value)
                    pending.append(value)
    uses = []
    for op in operations:
        positions = [
            i for i in range(op.get_num_operands())
            if op.get_operand(i).id() in pointers
        ]
        if not positions:
            continue
        name = op.get_name()
        need(positions == [0], 'State source address escapes: ' + name)
        if name in propagators:
            need(
                op.get_num_results() == 1
                and '!tt.ptr<' in str(op.get_result(0).get_type()),
                'State source pointer propagation type')
        elif name == 'tt.load':
            need(
                op.get_num_results() == 1
                and '!tt.ptr<' not in str(op.get_result(0).get_type()),
                'State source pointer load')
        elif name == 'tt.store':
            need(
                op.get_num_operands() >= 2
                and '!tt.ptr<' not in str(op.get_operand(1).get_type())
                and op.get_num_results() == 0, 'State source pointer store')
        else:
            raise ValueError('State source address escapes: ' + name)
        uses.append(name)
    need('tt.store' in uses, 'State source has no direct store')
    return dict(schema_version=1,
                state_index=state_index,
                function_name=function_name,
                state_address_noescape=True,
                pointer_values=len(pointers),
                pointer_uses=uses,
                lowered_writer_qualified=False,
                native_timing_boundary_qualified=False)
