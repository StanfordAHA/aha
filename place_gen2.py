

fopen = open('design.place_unroll', 'r')
place_lines = fopen.readlines()
fopen.close()

fixed_lines = []

for line in place_lines:
    split_line = line.split()
    if "Block" in split_line[0]:
        continue
    if "-" in split_line[0]:
        continue
    fixed_lines.append(f'fixed_io[\"{split_line[0]}\"] = ({split_line[1]}, {split_line[2]})')
    fixed_lines.append("\n")
    fixed_lines.append(f'fixed_io[\"{split_line[0]}_2\"] = ({split_line[1]}, {str(int(split_line[2]) + 8)})')
    fixed_lines.append("\n")

fopen = open('manual_place', 'w')
fopen.writelines(fixed_lines)
fopen.close()