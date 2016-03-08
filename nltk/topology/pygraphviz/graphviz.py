
#!/usr/bin/env python

# from __future__ import absolute_import
# from __future__ import unicode_literals
# from __future__ import print_function
# from __future__ import division

import pygraphviz as pgv
# strict (no parallel edges)
# digraph
# with attribute rankdir set to 'LR'
A=pgv.AGraph(directed=False,strict=True,rankdir='TD', shape='none', splines='spline',smoothing=True, outputMode='edgesfirst')
# add node 1 with color red
A.add_node(0,color='red')
#A.add_node(5,color='blue')

sg1 = A.add_subgraph(name="cluster1",
                style='filled',
                #color='lightgrey',
                label = 'main'
                )
sg1.add_node(1,label = "F1")
sg1.add_node(2, label = 'F2')
sg1.add_node(3)

sg2 = A.add_subgraph( name="cluster2",
                style='filled',
                #color='lightgrey',
                label = 'inf'
                )

sg2.add_node(4)
sg2.add_node(5)
# sg1.graph_attr['style']='filled'
# node [style=filled];
# 		b0 -> b1 -> b2 -> b3;
# 		label = "process #2";
# 		color=blue

# add some edges
#
A.add_edge(0,1)
A.add_edge(0,2)
A.add_edge(0,3)
A.add_edge(2,4, color='green')
A.add_edge(2,5)
A.add_edge(5,0)

# sg2.add_edge(5,2)

# A.add_edge(1,4,color='green')
# A.add_edge(1,3)
# A.add_edge(1,3)
# sg1.add_edge(3,4)
# A.add_edge(3,5)
# A.add_edge(3,6)
# A.add_edge(4,6)
# sg2.add_edge(6,2)
# adjust a graph parameter
#A.graph_attr['epsilon']='0.001'
# A.node_attr['shape']='none'
A.node_attr['shape']='box'
A.node_attr['style']='rounded'

# A.graph_attr['shape']='box'
print(A.string()) # print dot file to standard output
A.layout('dot') # layout with dot
A.draw('foo.ps') # write to file