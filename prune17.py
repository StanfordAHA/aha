# determine fixed routes from design.packed
with open('/aha/design.packed_config1', 'r') as fopen:
    packed_lines = fopen.readlines()

fixed_routes = []

for packed_line in packed_lines:
    if "Bus" in packed_line:
        break
    if "Netlist" in packed_line:
        continue
    if "e" in packed_line and "I" not in packed_line:
        # grab edge name from packed lines not interfacing with glb
        fixed_routes.append(packed_line.split()[0][:-1])


# read in design.route line by line
with open('/aha/design.route_config1', 'r') as fopen:
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

print(sb_to_remove)

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
