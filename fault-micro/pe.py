import magma as m
import fault as f
import hwtypes as ht

import operator


class PE(m.Generator2):
    def __init__(self, instr_op_map: dict):
        n_cfg_bits = max(x.bit_length() for x in instr_op_map.keys())
        self.io = m.IO(
            a=m.In(m.UInt[16]), b=m.In(m.UInt[16]), c=m.Out(m.UInt[16]),
            config_data=m.In(m.Bits[n_cfg_bits]), config_en=m.In(m.Enable)
        ) + m.ClockIO()

        opcode = m.Register(m.Bits[n_cfg_bits], has_enable=True)()(
            self.io.config_data, CE=self.io.config_en
        )
        curr = None
        for instr, op in instr_op_map.items():
            next = op(self.io.a, self.io.b)
            if curr is not None:
                next = m.mux([curr, next], opcode == instr)
            curr = next
        self.io.c @= curr


ops = m.common.ParamDict({
    0xDE: operator.add,
    0xAD: operator.sub,
    0xBE: operator.mul,
    0xEF: operator.xor
})
tester = f.SynchronousTester(PE(ops))
tester.circuit.config_en = 1
for inst, op in ops.items():
    tester.circuit.config_data = inst
    tester.circuit.a = a = ht.BitVector.random(16)
    tester.circuit.b = b = ht.BitVector.random(16)
    tester.step(2)
    tester.circuit.c.expect(op(a, b))

tester.compile_and_run("verilator", flags=["-Wno-fatal"],
                       directory="build")

