from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division

from nltk.grammar import FeatStructNonterminal
from nltk.topology import FeatTree

from pygraphviz import *

__author__ = 'Denis Krusko: kruskod@gmail.com'

def add_cluster(Graph, index, root, topologies):
    index *= 10

    if topologies:
        topology = topologies[0]

        cluster_title = "{}({})".format(topology.ph, topology.tag)
        

        sg = Graph.add_subgraph( name="cluster" + str(index),
                        #style='filled',
                        #color='lightgrey',
                        label = topology.tag,
                        labeljust='r',
                        #rankdir='LR',
                        # rank='same',
                        # ordering='out'
                        )

        prevEdge = None
        for field, field_edges in topology.items():
            for edge in field_edges:
                if edge.shared:
                    sg.add_node(edge.gorn,label = "{{{}{} | {}}}".format(field.ft , str(field.mod) if field.mod else '', edge_label(edge)), color='red',)
                else:
                    sg.add_node(edge.gorn,label = "{{{}{} | {}}}".format(field.ft , str(field.mod) if field.mod else '', edge_label(edge)))
                if prevEdge:
                    #sg.add_edge(prevEdge.gorn, edge.gorn, style='invis')
                    pass
                prevEdge = edge



        for edge in root:
            index += 1
            add_cluster(Graph, index, edge, edge.topologies)
            Graph.add_edge(root.gorn, edge.gorn)

    else:
        # root is Head
         for edge in root:
            # add leaf
            Graph.add_node(edge, shape = 'plaintext')
            Graph.add_edge(root.gorn, edge)



def edge_label(edge):
    if isinstance(edge, FeatTree.FeatTree):
        label = edge.label()
        if isinstance(label, FeatStructNonterminal):
            label = label.pprint()
        prefix = str(edge.gf) if edge.gf else ""
        return prefix + label
    return edge

def draw_graph(graph):

    G = AGraph(directed=True,strict=False, rankdir='TB', smoothing=True,
    # clusterrank='local',
    # splines='line',
    # compound = True,
    # concentrate= True, # enables an edging merge technique
    #ratio='compress', # ratio=1
    #size='7.5,10'
    )

    #clusterrank = 'global'
    # ranksep='equally',
    # G.node_attr['shape']='box'
    G.node_attr['shape']='Mrecord'
    #G.node_attr['style']='rounded'
    G.node_attr['label_scheme']='3'
    G.node_attr['fontsize']=16

    #G.node_attr['pack']=0.1
    #G.node_attr['margin']=0.01


    #G.edge_attr['len']=0.1
    #G.edge_attr['minlen']=0

    # shape=record

    subgraph_index = 1

    G.add_node(graph.gorn, label = edge_label(graph))

    add_cluster(G, subgraph_index, graph, graph.topologies)

    print(G.string()) # print dot file to standard output
    # 'unflatten -l 3 | dot
    # use console to provide better layout for a dot file $:cat graph.dot | unflatten -l 1 | dot -Tpdf > graph.pdf
    G.layout(prog='dot') # layout with dot

    # G.layout('neato') # layout with dot
    return G.draw(format='png')


if __name__ == "__main__":
    pass
    #demo_simplifier()
    #unify_demo()
    # demo()