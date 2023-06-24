import re
# python script to take list of fixed routes remove from 17.graph

# fixed_routes = ["e2", "e5", "e6", "e2_2", "e5_2", "e6_2"]
fixed_routes = []
# read in design.route line by line
fopen = open('matmul_config1', 'r')
route_lines = fopen.readlines()
fopen.close()

for route_line in route_lines:
    if "ID" in route_line:
        break
    if "Netlist" in route_line:
        continue
    if not "I" in route_line and len(route_line.split()) > 0:
       fixed_routes.append(route_line.split()[0][:-1]) 
    
print(fixed_routes)

save_route = []

found_net = False

fopen = open('design.route_config1', 'r')
route_lines = fopen.readlines()
fopen.close()

# find extractable SB
for route_line in route_lines:
    if "Net ID" in route_line:
        found_net = any(fixed_route == route_line.split()[2] for fixed_route in fixed_routes)
    if found_net == True:
        save_route.append(route_line)


# replace routes in design.route line by line
fopen = open('SIM_DIR/design.route', 'r')
route_lines = fopen.readlines()
fopen.close()

# read new route file
new_route = []
for route_line in route_lines:
    if "Net ID" in route_line:
        found_net = any(fixed_route == route_line.split()[2] for fixed_route in fixed_routes)
    if found_net == False:
        new_route.append(route_line)


fopen = open('SIM_DIR/design.route', 'w')
fopen.writelines(new_route)
fopen.writelines(save_route)
fopen.close()               

        


            
            