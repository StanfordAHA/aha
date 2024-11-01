from canal.cyclone import *

num_tracks = 5

# Create dictionary of input nodes
input_nodes = {}
for side in SwitchBoxSide:
    input_nodes[side] = []
    for track in range(num_tracks):
        input_nodes[side].append(SwitchBoxNode(0, 0, track, 16, side, SwitchBoxIO.SB_IN))

# Create dictionary of output nodes
output_nodes = {}
for side in SwitchBoxSide:
    output_nodes[side] = []
    for track in range(num_tracks):
        output_nodes[side].append(SwitchBoxNode(0, 0, track, 16, side, SwitchBoxIO.SB_OUT))

# Wire up input nodes to output nodes
for track in range(num_tracks):
    for side_from in SwitchBoxSide:
        for side_to in SwitchBoxSide:
            if side_from == side_to:
                continue
            input_node = input_nodes[side_from][track]
            output_node = output_nodes[side_to][track]
            print(f"Wire {input_node} -> {output_node}")
            input_node.add_edge(output_node)


