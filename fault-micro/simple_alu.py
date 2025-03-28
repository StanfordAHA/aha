import operator

import magma as m
import fault as f
import hwtypes as ht

class SimpleALU(m.Circuit):
    io = m.IO(
        a=m.In(m.UInt[16]),
        b=m.In(m.UInt[16]),
        c=m.Out(m.UInt[16]),
        opcode=m.In(m.Bits[2])
    )

    io.c @= m.mux(
        [io.a + io.b, io.a - io.b, io.a * io.b, io.b ^ io.a],
        io.opcode
    )

ops = [operator.add, operator.sub, operator.mul, operator.xor]
tester = f.Tester(SimpleALU)
for i, op in enumerate(ops):
    tester.circuit.opcode = i
    tester.circuit.a = a = ht.BitVector.random(16)
    tester.circuit.b = b = ht.BitVector.random(16)
    tester.eval()
    tester.circuit.c.expect(op(a, b))

tester.compile_and_run("verilator", flags=["-Wno-fatal"],
                       directory="build")

