import sys 
import re

# determine fixed routes from design.packed
with open(sys.argv[1], 'r') as fopen:
    packed_lines = fopen.readlines()

fixed_routes = []
not_fixed_routes = []

for packed_line in packed_lines:
    if "ID" in packed_line:
        break
    if "Netlist" in packed_line:
        continue
    if "e" in packed_line:
        split_line = packed_line.split()
        pe_num1 = split_line[1][1:-1]
        pe_num2 = split_line[3][1:-1]
        _pe_num1 = "_" in pe_num1
        _pe_num2 = "_" in pe_num2
        int_pe_num1 = int(pe_num1[1:]) >= 100
        int_pe_num2 = int(pe_num2[1:]) >= 100
        # grab edge name from packed lines in graphs or to glb
        # what about p100 tied to p100
        if not("I" in packed_line or re.search("p1\d\d", packed_line)):
            print(packed_line)
            fixed_routes.append(packed_line.split()[0][:-1])


# read in design.route line by line
with open(sys.argv[2], 'r') as fopen:
    route_lines = fopen.readlines()

sb_to_remove = []
save_route = []
found_net = False

# find extractable SB
for route_line in route_lines:
    if "Net ID" in route_line:
        for fixed_route in fixed_routes:
            # compare edge names
            if fixed_route == route_line.split()[2]:
                found_net = True
                break
        else:
            found_net = False
    if found_net:
        if "SB" in route_line:
            sb_to_remove.append(route_line)
        save_route.append(route_line)

# sb_to_remove_2 = sb_to_remove
# sb_to_remove = []

# print("save these sbs")
# for sb in sb_to_remove_2:
#     split_sb = sb.split()
#     if not ("0" in split_sb[1] and "1," == split_sb[3]):
#         sb_to_remove.append(sb)
#     else: 
#         print(sb)

# remove SB from 17.graph
with open('/aha/SIM_DIR/17.graph', 'r') as fopen:
    graph_lines = fopen.readlines()

new_graph_lines = []
found_sb = False

for graph_line in graph_lines:
    if "SB" in graph_line:
        for sb in sb_to_remove:
            if sb in graph_line:
                found_sb = True
                break
        else:
            found_sb = False
    if "END" in graph_line:
        found_sb = False
    if not found_sb:
        new_graph_lines.append(graph_line)

# write remaining graph lines to new 17_new.graph
with open('/aha/SIM_DIR/17.graph', 'w') as fopen:
    fopen.writelines(new_graph_lines)
