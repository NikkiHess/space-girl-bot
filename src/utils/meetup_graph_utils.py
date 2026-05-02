# built-in modules
from typing import List, Set

# pip modules
import networkx as nx # to create the graph
import matplotlib.pyplot as plt # to draw the graph

# create the meetup graph (undirected)
meetup_graph = nx.Graph()

with open("meetup_graph_smug.txt") as file:
    nodes: Set[str] = set()
    edges: List[tuple] = []

    # read each line in the file, converting to tuples to feed into the graph as edges
    for line in file.readlines():
        # get the first 2 elements, in case there are somehow more
        pair = line.strip().split(" ")[:2]
        # convert the list of 2 into a tuple
        pair = tuple(pair)

        # add the names to the set (if not present)
        nodes.update(pair)
        # append the tuple as an edge
        edges.append(pair)

    # add the tuples to the graph, creating nodes as necessary
    meetup_graph.add_edges_from(edges)

# for a consistent, seeded layout
layout = nx.spring_layout(
    meetup_graph,
    k=0.1,
    iterations=150,
    seed=42069
)
# draw the meetup graph
nx.draw(
    meetup_graph,
    pos = layout,
    with_labels = True
)
plt.savefig("meetup_graph.png")