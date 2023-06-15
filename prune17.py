# python script to take list of fixed routes remove from 17.graph

# determine fixed routes from design.packed
fopen = open('design.packed_config1', 'r')
packed_lines = fopen.readlines()
fopen.close()
# fixed_routes = ["e2", "e5", "e6", "e2_2", "e5_2", "e6_2"]

fixed_route = []

for packed_line in packed_lines:
    if "Bus" in packed_line:
        break
    if "Netlist" in packed_line:
        continue
    if "e" in packed_line and not "I" in packed_line:
        fixed_route.append(packed_line.split()[0][:-1])

print(fixed_route)
    
            


# read in design.route line by line
fopen = open('design.route_config1', 'r')
route_lines = fopen.readlines()
fopen.close()

sb_to_remove = []

# find extractable SB
num_lines = len(route_lines)
i = 0
found_net = False
save_route = []
while i < num_lines:
    if "Net ID" in route_lines[i]:
        for fixed_route in fixed_routes:
            if fixed_route == route_lines[i].split()[2]:
                print(route_lines[i])
                found_net = True
                break
            else:
                found_net = False
    if found_net == True:
        if "SB" in route_lines[i]:
            sb_to_remove.append(route_lines[i])
        save_route.append(route_lines[i])

    i += 1

print(save_route)

# remove SB from 17.graph
fopen = open('17.graph', 'r')
graph_lines = fopen.readlines()
fopen.close()

num_lines = len(graph_lines)
i = 0
new_graph_lines = []
found_sb = False
while i < num_lines:
    if "SB" in graph_lines[i]:
        for sb in sb_to_remove:
            if sb in graph_lines[i]:
                found_sb = True
                break
            else:
                found_sb = False
    if found_sb == False:
        new_graph_lines.append(graph_lines[i])

    i += 1

# write remaining graph lines in new 17_new.graph
fopen = open('SIM_DIR/17.graph', 'w')
fopen.writelines(new_graph_lines)
fopen.close()



            
            