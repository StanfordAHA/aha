# python script to take list of fixed routes remove from 17.graph

fixed_routes = ["e2", "e5", "e6", "e2_2", "e5_2", "e6_2"]

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
    net = {}
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

# replace routes in design.route line by line
fopen = open('SIM_DIR/design.route', 'r')
route_lines = fopen.readlines()
fopen.close()

# read new route file
num_lines = len(route_lines)
i = 0
found_net = False
new_route = []
while i < num_lines:
    net = {}
    if "Net ID" in route_lines[i]:
        for fixed_route in fixed_routes:
            if fixed_route == route_lines[i].split()[2]:
                print(route_lines[i])
                found_net = True
                break
            else:
                found_net = False
    if found_net == False:
        new_route.append(route_lines[i])

    i += 1

print(save_route)

fopen = open('SIM_DIR/design.route', 'w')
fopen.writelines(new_route)
fopen.writelines(save_route)
fopen.close()               

        


            
            