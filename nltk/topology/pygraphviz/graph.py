from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division

import operator

from nltk.grammar import FeatStructNonterminal
from nltk.topology import FeatTree

from pygraphviz import *

__author__ = 'Denis Krusko: kruskod@gmail.com'

def add_cluster(Graph, parent_index, root, topologies):
    index =  10 * len(str(root.gorn)) + root.gorn

    if topologies:
        topology = topologies[0]

        cluster_title = "{}({})".format(topology.ph, topology.tag)
        cluster_labels = []
        cluster_edges = []


        # for field, field_edges in topology.items():
        #     for edge in field_edges:
        #         cluster_edges.append("{{{}{} | <{}> {}}}".format(field.ft , str(field.mod) if field.mod else '', str(field.ft)+ (field.mod if field.mod else ''), edge_label(edge)))
        #
        # Graph.add_node(root.gorn,label =  '{{ {} |{{ {} }} }}'.format(cluster_title, '|'.join(cluster_edges)))


        for field, field_edges in topology.items():
            for edge in field_edges:
                field_label = field.short_str()
                cluster_labels.append('<TD>{}</TD>'.format(field_label))
                cluster_edges.append('<TD PORT="{}">{}</TD>'.format(edge.gorn, edge_label(edge, delim='<br />')))

                add_cluster(Graph, index, edge, edge.topologies)
                if edge in root:
                    Graph.add_edge(parent_index, index, headport=edge.gorn, tailport=(root.gorn if root.gorn else 's'))
                else:
                    # find and add a link to this edge
                    pass


        html_label = '< <TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4"><tr><td COLSPAN="{}">{}</td></tr><tr>{}</tr><tr>{}</tr></TABLE>>'.format(len(cluster_edges), cluster_title, ''.join(cluster_labels), ''.join(cluster_edges))


        Graph.add_node(str(index),label=html_label, shape='plaintext')


        # sg = Graph.add_subgraph( name="cluster" + str(index),
        #                 #style='filled',
        #                 #color='lightgrey',
        #                 label = topology.tag,
        #                 labeljust='r',
        #                 #rankdir='LR',
        #                 rank='same',
        #                 ordering='out'
        #                 )
        #
        # prevEdge = None
        # for field, field_edges in topology.items():
        #     for edge in field_edges:
        #         if edge.shared:
        #             sg.add_node(edge.gorn,label = "{{{}{} | {}}}".format(field.ft , str(field.mod) if field.mod else '', edge_label(edge)), color='red', rank='same', group=index)
        #         else:
        #             sg.add_node(edge.gorn,label = "{{{}{} | {}}}".format(field.ft , str(field.mod) if field.mod else '', edge_label(edge)), rank='same', group=index)
        #         if prevEdge:
        #             #sg.add_edge(prevEdge.gorn, edge.gorn, style='invis', rank='same')
        #             pass
        #         prevEdge = edge

    else:
        # root is Head
         for edge in root:
            # add leaf
            Graph.add_node(edge, shape = 'plaintext')
            # parent_gorn = str(root.gorn)[:-1]
            # if parent_gorn:
            #     parent_gorn = int(parent_gorn)
            # else:
            #     parent_gorn = 0
            # parent_index = 'n' +  str(10 * len(str(parent_gorn)) + parent_gorn)
            Graph.add_edge(parent_index, edge, tailport=root.gorn)



def edge_label(edge, delim = '\n'):
    if isinstance(edge, FeatTree.FeatTree):
        label = edge.label()
        if isinstance(label, FeatStructNonterminal):
            label = label.pprint(delim=delim)
        prefix = str(edge.gf) if edge.gf else ""
        return prefix + label
    return edge

def draw_graph(graph):

    G = AGraph(directed=True, strict=False, rankdir='TB', smoothing=True,
    # clusterrank='local',
    # splines='line',
    # compound = True,
    # concentrate= True, # enables an edging merge technique
    #ratio='compress', # ratio=1
    size='7.5,10'
    )

    #clusterrank = 'global'
    # ranksep='equally',
    # G.node_attr['shape']='box'
    # G.node_attr['shape']='Mrecord'
    #G.node_attr['shape']='plaintext'
    G.node_attr['style']='rounded'
    #G.node_attr['label_scheme']='3'
    G.node_attr['fontsize']=16

    #G.node_attr['pack']=0.1
    #G.node_attr['margin']=0.01


    #G.edge_attr['len']=0.1
    #G.edge_attr['minlen']=0

    # shape=record

    G.add_node(graph.gorn, label = edge_label(graph))

    add_cluster(G, 0, graph, graph.topologies)

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