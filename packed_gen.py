import re
# python script to generate different configurations

# determine fixed routes from design.packed
fopen = open('design.packed_initial', 'r')
packed_lines = fopen.readlines()
fopen.close()

fixed_route = []

# TODO: should count outputs automatically
# matmul has 3 outputs
num_pes = 3
pe_list = []
for pe in range(num_pes):
    pe_num = 100+pe
    pe_list.append(f'p{pe_num}')

inputs = []
outputs = []

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

print(inputs)
print(outputs)

def dup(lines_to_copy):
    new_packed = []
    new_packed2 = []
    for line in lines_to_copy:
        new_packed.append(line)
        split_line = line.split()
        new_line = []
        search_string = ".*\d"
        for item in split_line:
            if item[0] in ("e", "I", "m", "p"):
                # don't replace Name in ID to Names
                if item[-1] == ":":
                    res = re.search(search_string, item)
                    end = res.end()
                    new_line.append(item[0:end] + "_2" + item[end])
                else:
                    new_line.append(item)
            # There is a '('
            elif item[1] in ("I", "m", "p"):
                res = re.search(search_string, item)
                end = res.end()
                new_line.append(item[0:end] + "_2" + item[end])
            else:
                new_line.append(item)
        new_line = " ".join(new_line)
        new_packed2.append(new_line + "\n")
    return new_packed, new_packed2


# create doubled netlist
new_packed = []
lines_to_copy = []
for packed_line in packed_lines:
    if "Netlists:" in packed_line:
        lines_to_copy = []
    elif "ID to Names:" in packed_line:
        new_packed = new_packed + ["Netlists:\n"]
        p1, p2 = dup(lines_to_copy)
        new_packed = new_packed + p1[:-1] + p2[:-1]
        # extra edges (4 ports)
        e = 1
        for pe in pe_list:
            new_packed.append(f'e{e}000_3: ({inputs[0]}_2, io2f_17) ({pe}, PE_input_width_17_num_2)\n')
            new_packed.append(f'e{e}001_3: ({inputs[1]}_2, io2f_17) ({pe}, PE_input_width_17_num_0)\n')
            new_packed.append(f'e{e}002_3: ({inputs[1]}_2, io2f_17) ({pe}, PE_input_width_17_num_1)\n')
            new_packed.append(f'e{e}003_3: ({inputs[1]}_2, io2f_17) ({pe}, PE_input_width_17_num_3)\n')
            e+=1
        lines_to_copy = []
        new_packed = new_packed + ["\n"]
    elif "Netlist Bus:" in packed_line:
        new_packed = new_packed + ["ID to Names:\n"]
        p1, p2 = dup(lines_to_copy)
        tiles1, tiles2 = p1, p2
        new_packed = new_packed + p1[:-1] + p2[:-1]
        for pe in pe_list:
            new_packed.append(pe + ": " + pe + "\n")
        new_packed.append("\n")
        lines_to_copy = []
    else: 
        lines_to_copy.append(packed_line)


new_packed = new_packed + ["Netlist Bus:\n"]
p1, p2 = dup(lines_to_copy)
new_packed = new_packed + p1 + p2
e = 1
for pe in pe_list:
    new_packed.append(f'e{e}000_3: 17\n')
    new_packed.append(f'e{e}001_3: 17\n')
    new_packed.append(f'e{e}002_3: 17\n')
    new_packed.append(f'e{e}003_3: 17\n')
    e+=1


# remove I._2 for config1
config1 = []
to_remove = []
for packed_line in new_packed:
    if re.search("\(I\d*_2", packed_line):
        edge =  packed_line.split()[0][:-1]
        # keep edges for ready=0 intersects
        if "_3" not in edge: 
            to_remove.append(edge)
        else:
            config1.append(packed_line)
    else:
        # Don't add if edge has I_2
        if not any([x in packed_line for x in to_remove]):
            config1.append(packed_line)


fopen = open('config1', 'w')
fopen.writelines(config1)
fopen.close()

# swap I input for config2
config2 = []
to_remove = []
pe_idx = 0
for packed_line in new_packed:
    split_line = packed_line.split()
    # ready=0 intersect case
    if "_3:" in packed_line:
        if "00_3" in packed_line:
            continue
        else:
            config2.append(packed_line)
            continue
    if len(split_line) > 4 and split_line[1][1] == "I":
        if "_2" in split_line[1]:
            split_line[1] = split_line[1].replace("_2","")
        else:
            split_line[1] = split_line[1][:-1] + "_2" + split_line[1][-1]
        config2.append(" ".join(split_line) + "\n")
    elif len(split_line) > 4 and split_line[3][1] == "I":
        if "_2" in split_line[3]:
            split_line[3] = "(" + pe_list[pe_idx] + ","
            pe_idx = (pe_idx + 1)
            split_line[4] = "PE_input_width_17_num_2)"
        config2.append(" ".join(split_line) + "\n")
    else:
        config2.append(packed_line)


fopen = open('config2', 'w')
fopen.writelines(config2)
fopen.close()

pe_idx= 0
# swap I input for config3
config3 = []
to_remove = []
for packed_line in new_packed:
    split_line = packed_line.split()
    # ready=0 intersect case
    if "_3:" in packed_line:
        if "00_3" in packed_line:
            continue
        else:
            config3.append(packed_line)
            continue
    if len(split_line) > 3 and split_line[3][1] == "I":
        if "_2" in split_line[3]:
            split_line[3] = split_line[3].replace("_2","")
        else:
            split_line[3] = "(" + pe_list[pe_idx] + ","
            pe_idx = (pe_idx + 1)
            split_line[4] = "PE_input_width_17_num_2)"
        config3.append(" ".join(split_line) + "\n")
    elif len(split_line) > 3 and split_line[1][1] == "I":
        if "_2" in split_line[1]:
            split_line[1] = split_line[1].replace("_2","")
        else:
            split_line[1] = split_line[1][:-1] + "_2" + split_line[1][-1]
        config3.append(" ".join(split_line) + "\n")
    else:
        config3.append(packed_line)


fopen = open('config3', 'w')
fopen.writelines(config3)
fopen.close()

