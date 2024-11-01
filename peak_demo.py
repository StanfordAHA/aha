from peak import Peak
import hwtypes as ht


class Opcode(ht.Enum):
    Add = 0
    Sub = 1
    Neg = 2

Word = ht.BitVector[8]

class ALU(Peak):
    def __call__(self, inst: Opcode, i0: Word, i1: Word) -> Word:
        if inst == Opcode.Add:
            return i0 + i1
        elif inst == Opcode.Sub:
            return i0 - i1
        else:
            return -i0

alu = ALU()

i0 = Word(54) 
i1 = Word(88)

out = alu(Opcode.Add, i0, i1)

assert out == i0 + i1

'''
import pysmt
from pysmt import shortcuts as sc

with sc.Solver('z3') as s:
    s.add_assertion((out != i0 + i1).value)
    if s.solve():
        print("Counter example found")
    else:
        print("Verified add")
'''
