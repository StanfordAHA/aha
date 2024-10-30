import magma as m
import fault as f
import hwtypes as ht

import operator


class ConfigALU(m.Circuit):
    io = m.IO(
        a=m.In(m.UInt[16]),
        b=m.In(m.UInt[16]),
        c=m.Out(m.UInt[16]),
        config_data=m.In(m.Bits[2]),
        config_en=m.In(m.Enable)
    ) + m.ClockIO()

    opcode = m.Register(m.Bits[2], has_enable=True)()(
        io.config_data, CE=io.config_en
    )
    io.c @= m.mux(
        [io.a + io.b, io.a - io.b, io.a * io.b, io.b ^ io.a],
        opcode
    )

ops = [operator.add, operator.sub, operator.mul, operator.xor]
tester = f.SynchronousTester(ConfigALU)
tester.circuit.config_en = 1
for i, op in enumerate(ops):
    tester.circuit.config_data = i
    tester.circuit.a = a = ht.BitVector.random(16)
    tester.circuit.b = b = ht.BitVector.random(16)
    tester.step(2)
    tester.circuit.c.expect(op(a, b))

tester.compile_and_run("verilator", flags=["-Wno-fatal"],
                       directory="build")

