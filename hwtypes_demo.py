from hwtypes import BitVector, SMTBitVector

def add3(a, b, c):
    return a + b + c

#'''
# Python bitvector types
x = BitVector[8](2)
y = BitVector[8](5)
z = BitVector[8](11)

print(add3(x,y,z))
#'''
'''
# SMT bitvector types
x = SMTBitVector[8](2)
y = SMTBitVector[8](5)
z = SMTBitVector[8](11)

print(add3(x,y,z))
'''
'''
# SMT symbolic bitvector types
x = SMTBitVector[8](name="a")
y = SMTBitVector[8](name="b")
z = SMTBitVector[8](name="c")

print(add3(x,y,z))
'''

