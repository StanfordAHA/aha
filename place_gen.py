# python script to generate fixed placement
import re

def natural_sort(l): 
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(l, key=alphanum_key)

fopen = open('design.packed_initial', 'r')
packed_lines = fopen.readlines()
fopen.close()

inputs = []
outputs = []
fixed_set = set()

for pack in packed_lines:
    pack = pack.split()
    print(pack)
    if len(pack) == 0:
        break
    if "Netlist" in pack[0]:
        continue
    if pack[1][1] == "I":
        inputs.append(pack[1][1:-1])
    if pack[3][1] == "I":
        outputs.append(pack[3][1:-1])
    fixed_set.add(pack[1][1:-1])
    fixed_set.add(pack[3][1:-1])

print(inputs)
print(outputs)
print(fixed_set)

fixed_list = natural_sort(fixed_set)

print(fixed_list)

# TODO wont work if large num of pes and mems

fixed_lines = []
in_io = 0
out_io = 1
mem = 0
pe = 0

for tile in fixed_list:
    if "I" in tile:
        if tile in inputs:
            fixed_lines.append(f'fixed_io[\"{tile}\"] = ({in_io}, 0)')
            fixed_lines.append("\n")
            in_io += 2
        else: 
            fixed_lines.append(f'fixed_io[\"{tile}\"] = ({out_io}, 0)')
            fixed_lines.append("\n")
            out_io += 2

for tile in fixed_list:
    if "I" in tile:
        if tile in inputs:
            fixed_lines.append(f'fixed_io[\"{tile}_2\"] = ({in_io}, 0)')
            fixed_lines.append("\n")
            in_io += 2
        else: 
            fixed_lines.append(f'fixed_io[\"{tile}_2\"] = ({out_io}, 0)')
            fixed_lines.append("\n")
            out_io += 2

for tile in fixed_list:
    if "p" in tile:
        pe_x = pe // 8
        if pe_x >= 3:
            pe_x += 1
        if pe_x >= 7:
            pe_x += 1
        pe_y = (pe % 8) + 1
        fixed_lines.append(f'fixed_io[\"{tile}\"] = ({pe_x}, {pe_y})')
        fixed_lines.append("\n")
        pe += 2

pe = 0

for tile in fixed_list:
    if "p" in tile:
        pe_x = pe // 8 
        if pe_x >= 3:
            pe_x += 1
        if pe_x >= 7:
            pe_x += 1
        pe_y = (pe % 8) + 9
        fixed_lines.append(f'fixed_io[\"{tile}_2\"] = ({pe_x}, {pe_y})')
        fixed_lines.append("\n")
        pe += 2

for tile in fixed_list:
    if "m" in tile:
        mem_x = (mem // 8)*4+3
        mem_y = (mem % 8) + 1
        fixed_lines.append(f'fixed_io[\"{tile}\"] = ({mem_x}, {mem_y})')
        fixed_lines.append("\n")
        mem += 1

mem = 0

for tile in fixed_list:
    if "m" in tile:
        mem_x = (mem // 8)*4+11
        mem_y = (mem % 8) + 9
        fixed_lines.append(f'fixed_io[\"{tile}_2\"] = ({mem_x}, {mem_y})')
        fixed_lines.append("\n")
        mem += 1



fopen = open('manual_place', 'w')
fopen.writelines(fixed_lines)
fopen.close()


