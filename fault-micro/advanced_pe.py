import magma as m
import fault as f
import hwtypes as ht

import operator


class AdvancedPE(m.Generator2):
    def __init__(self, addr, instr_op_map):
        n_cfg_bits = max(x.bit_length() for x in instr_op_map.keys())
        self.io = io = m.IO(
            a=m.In(m.UInt[16]),
            b=m.In(m.UInt[16]),
            c=m.Out(m.UInt[16]),
            config_addr=m.In(m.Bits[8]),
            config_data=m.In(m.Bits[n_cfg_bits]),
            config_en=m.In(m.Enable)
        ) + m.ClockIO(has_reset=True)

        opcode = m.Register(
            m.Bits[n_cfg_bits], has_enable=True, reset_type=m.Reset
        )()(io.config_data, CE=io.config_en & (io.config_addr == addr))
        curr = None
        for instr, op in instr_op_map.items():
            next = op(self.io.a, self.io.b)
            if curr is not None:
                next = m.mux([curr, next], opcode == instr)
            curr = next
        self.io.c @= curr


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


addr = 0xDE
ops = m.common.ParamDict({
    0xDE: operator.add,
    0xAD: operator.sub,
    0xBE: operator.mul,
    0xEF: operator.xor
})
PE = AdvancedPE(addr, ops)
tester = PETester(
    PE, PE.CLK, PE.config_addr, PE.config_data, PE.config_en
)
tester.circuit.RESET = 0
for inst, op in ops.items():
    tester.check_op(addr, inst, op)

tester.reset()
tester.check_op(addr, 0xDE, ops[0xDE])

tester.compile_and_run("verilator", flags=["-Wno-fatal"],
                       directory="build")
