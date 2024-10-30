import magma as m
import fault as f
import hwtypes as ht

import operator


class SimplePE(m.Generator2):
    def __init__(self, addr):
        self.io = io = m.IO(
            a=m.In(m.UInt[16]),
            b=m.In(m.UInt[16]),
            c=m.Out(m.UInt[16]),
            config_addr=m.In(m.Bits[8]),
            config_data=m.In(m.Bits[2]),
            config_en=m.In(m.Enable)
        ) + m.ClockIO(has_reset=True)

        opcode = m.Register(m.Bits[2], has_enable=True, reset_type=m.Reset)()(
            io.config_data, CE=io.config_en & (io.config_addr == addr)
        )
        io.c @= m.mux(
            [io.a + io.b, io.a - io.b, io.a * io.b, io.b ^ io.a],
            opcode
        )


class ResetTester:
    def __init__(self, circuit):
        for port in circuit.interface.ports.values():
            if isinstance(port, m.Reset):
                self.reset_port = port
                break

    def reset(self):
        self.poke(self.reset_port, 1)
        self.step(2)
        self.poke(self.reset_port, 0)
        self.step(2)


class ConfigurationTester:
    def __init__(self, circuit, config_addr_port, config_data_port,
                 config_en_port):
        self.config_addr_port = config_addr_port
        self.config_data_port = config_data_port
        self.config_en_port = config_en_port

    def configure(self, addr, data):
        self.poke(self.clock, 0)
        self.poke(self.config_addr_port, addr)
        self.poke(self.config_data_port, data)
        self.poke(self.config_en_port, 1)
        self.step(2)
        self.poke(self.config_en_port, 0)


class PETester(
    f.SynchronousTester, ResetTester, ConfigurationTester
):
    def __init__(self, circuit, clock, config_addr_port, config_data_port,
                 config_en_port):
        # Note the explicit calls to `__init__` to manage the multiple
        # inheritance, rather than the standard use of `super`
        f.SynchronousTester.__init__(self, circuit, clock)
        ResetTester.__init__(self, circuit)
        ConfigurationTester.__init__(self, circuit, config_addr_port,
                                     config_data_port, config_en_port)

    def check_op(self, addr, instr, op):
        tester.configure(addr, instr)
        tester.circuit.a = a = ht.BitVector.random(16)
        tester.circuit.b = b = ht.BitVector.random(16)
        tester.step(2)
        tester.circuit.c.expect(op(a, b))


ops = [operator.add, operator.sub, operator.mul, operator.xor]
addr = 0xDE
PE = SimplePE(addr)
tester = PETester(
    PE, PE.CLK, PE.config_addr, PE.config_data, PE.config_en
)
for i, op in enumerate(ops):
    tester.check_op(addr, i, op)
tester.reset()
tester.check_op(addr, 0, ops[0])


tester.compile_and_run("verilator", flags=["-Wno-fatal"],
                       directory="build")
