import sys
import re

# read in design.route line by line
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
        int_pe_num1 = int(pe_num1[1:]) >= 1000
        int_pe_num2 = int(pe_num2[1:]) >= 1000
        # grab edge name from packed lines in graphs or to glb
        # what about p1000 tied to p1000
        if int_pe_num1 and int_pe_num2:
            print(packed_line)
            fixed_routes.append(packed_line.split()[0][:-1])
        elif not("I" in packed_line or re.search("p1\d\d\d", packed_line)):
            print(packed_line)
            fixed_routes.append(packed_line.split()[0][:-1])

print("fixed_routes2")
print(fixed_routes)
print("not fixed_routes2")
print(not_fixed_routes)
        

save_route = []

found_net = False

with open(sys.argv[2], 'r') as fopen:
    route_lines = fopen.readlines()

# find extractable SB
for route_line in route_lines:
    if "Net ID" in route_line:
        found_net = any(fixed_route == route_line.split()[2] for fixed_route in fixed_routes)
    if found_net == True:
        save_route.append(route_line)


# replace routes in design.route line by line
fopen = open('/aha/SIM_DIR/design.route', 'r')
route_lines = fopen.readlines()
fopen.close()

# read new route file
new_route = []
for route_line in route_lines:
    if "Net ID" in route_line:
        found_net = any(fixed_route == route_line.split()[2] for fixed_route in fixed_routes)
    if found_net == False:
        new_route.append(route_line)


fopen = open('/aha/SIM_DIR/design.route', 'w')
fopen.writelines(new_route)
fopen.writelines(save_route)
fopen.close()               

        


            
            