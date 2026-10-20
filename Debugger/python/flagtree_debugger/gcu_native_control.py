"""Finite direct-control index for byte-bound GCU300 native packets.

This indexes packet edges rather than simulating packet scheduling or hardware
loops. Unknown instructions/transfers are explicit; their absence from a local
predecessor list does not prove that no external entry exists. Callers provide
complete instructions and executable packet extents from the matching ELF.
"""
import re

_CONDITIONAL = frozenset(
    ('l.beq', 'l.bne', 'l.blt.u', 'l.blt.s', 'l.bge.u', 'l.bge.s'))
_SCALAR = frozenset((
    'c.addi4spn',
    'c.nop',
    's.nop16',
    'v.nop',
    'c.li',
    'c.mv',
    'c.add',
    'c.addi',
    'c.slli',
    'c.srli',
    'c.srai',
    'c.sub',
    'c.or',
    'c.and',
    'l.ldi16.s',
    'l.ldi16.u',
    'l.ldi_lo',
    'l.ldi_hi',
    'l.ldi_hi.m1',
    'l.mov',
    'l.movs',
    'l.movs.barrier',
    'l.movs.barrier.all',
    'l.movs.barrier.memory',
    'c.movsr2spr',
    'c.movsr2spr.ext',
    'c.movs.ext',
    'l.ld.w',
    'l.ld.b',
    'l.st.w',
    'l.st.b',
    'l.st.h',
    'l.sllia',
    'l.srlia',
    'l.sraia',
    'l.slla',
    'l.srla',
    'l.anda',
    'l.ora',
    'l.xora',
    'l.adda.u',
    'l.adda.s',
    'l.addia.u',
    'l.addia.s',
    'l.addit.u',
    'l.addit.s',
    'l.suba.u',
    'l.suba.s',
    'l.subia.u',
    'l.subia.s',
    'l.subit.u',
    'l.subit.s',
    'l.mula.s',
    'l.diva.s',
    'l.rema.u',
    'l.slt.u',
    'l.slt.s',
    'l.seq.u',
    'l.seq.s',
    'l.bc.lza.u32',
    'l.idma',
    'l.wait',
    'l.wait.dec',
    'l.vclr.qa',
    'l.vclr.va',
    'l.movr2qa',
    'l.movr2va',
    'l.vldqa.w.qa',
    'l.vldqa.b.va',
    'l.tvldqa.w.qa',
    'l.vldi_tari.t0',
    'l.vldi_tari.t1',
    'l.movsr2targ.ext.t0',
    'l.movsr2targ.ext.t1',
    'c.movtar.dual',
    'v.vstda.dual.qaddr.w',
    'v.vstda.b',
    'v.tvstda.w.dual',
    'm.mid.u32',
    'm.mop.msqr.f32.qa',
    'm.mop.mdm.f32.qa',
    'm.mop.mac.f32.qa',
    'm.mop.madd.f32.qa',
    'm.mop.mseq.s32.qa',
    'm.mop.merge.b.va',
    'm.mop.madd.s32.qa',
    'm.mop.cvt.va.rz.s8f32.vsel0',
    'm.mop.cvt.qa.rz.f32s32',
    'm.mop.msne.s32.qa',
    'm.vldxda.w.dual.vsel0',
    'm.vldxda.w.dual.vsel1',
))


def _need(value, message):
    if not value:
        raise ValueError(message)


def index_direct_control(instructions, *, start_packet, end_packet):
    """Index explicit transfers and ordinary fallthrough in one ELF extent.

    Extents are half-open. Missing instruction packets must be known zero/NOP
    packets from the executable; the index does not infer that from text gaps.
    Calls, indirect transfers, hardware loops and unknown opcodes prevent a
    complete-CFG claim. Direct targets outside the extent are recorded exits.
    """
    _need(
        type(start_packet) is int and type(end_packet) is int
        and 0 <= start_packet < end_packet
        and start_packet % 16 == end_packet % 16 == 0,
        'Invalid executable packet extent')
    _need((end_packet - start_packet) // 16 <= 65536,
          'Native packet extent exceeds budget')
    _need(
        isinstance(instructions, list) and len(instructions) <= 100000,
        'Native instruction index exceeds budget')
    packets = {pc: [] for pc in range(start_packet, end_packet, 16)}
    previous = -1
    for row in instructions:
        pc = row['pc']
        _need(
            type(pc) is int and pc > previous, 'Unordered native instructions')
        previous = pc
        _need(start_packet <= pc < end_packet,
              'Instruction outside executable extent')
        packets[pc & ~15].append(row)
    edges, unknown, controls = [], [], []

    def target(operands):
        matches = re.findall(r'<0x([\da-f]+)>', operands)
        _need(len(matches) == 1, 'Missing or ambiguous direct target')
        value = int(matches[0], 16)
        _need(value % 16 == 0, 'Unaligned direct target packet')
        return value

    def edge(source, dest, kind, instruction_pc=None):
        edges.append(
            dict(source=source,
                 target=dest,
                 kind=kind,
                 instruction_pc=instruction_pc,
                 internal=start_packet <= dest < end_packet))

    for packet, rows in packets.items():
        transfers = []
        for row in rows:
            op = row['opcode']
            if op in _SCALAR:
                continue
            if op in _CONDITIONAL or op in ('l.jal', 'l.jalr', 'l.halt'):
                transfers.append(row)
            else:
                unknown.append(
                    dict(packet=packet,
                         pc=row['pc'],
                         opcode=op,
                         reason='unmodeled_control_effect'))
        _need(len(transfers) <= 1, 'Multiple control transfers in one packet')
        if not transfers:
            edge(packet, packet + 16, 'fallthrough')
            continue
        row = transfers[0]
        op, operands = row['opcode'], row['operands']
        controls.append(dict(packet=packet, **row))
        if op in _CONDITIONAL:
            edge(packet, target(operands), 'conditional_taken', row['pc'])
            edge(packet, packet + 16, 'conditional_fallthrough', row['pc'])
        elif op == 'l.jal':
            dest = operands.split(',', 1)[0].strip()
            if dest == 'r0':
                edge(packet, target(operands), 'direct_jump', row['pc'])
            else:
                unknown.append(
                    dict(packet=packet,
                         pc=row['pc'],
                         opcode=op,
                         reason='call_control_and_clobbers_unmodeled'))
        elif op == 'l.jalr':
            if re.fullmatch(r'r0,\s*lr,\s*0x0', operands):
                continue
            unknown.append(
                dict(packet=packet,
                     pc=row['pc'],
                     opcode=op,
                     reason='indirect_transfer_unmodeled'))
        # l.halt has no continuation.
    predecessors = {pc: [] for pc in packets}
    for row in edges:
        if row['internal']:
            predecessors[row['target']].append(row)
    return dict(status='direct_native_packet_edges_indexed',
                start_packet=start_packet,
                end_packet=end_packet,
                packet_count=len(packets),
                edges=edges,
                predecessors=predecessors,
                controls=controls,
                unknown_controls=unknown,
                direct_control_complete=not unknown,
                external_entries_qualified=False,
                source_region_qualified=False,
                incoming_begin_site_qualified=False)
