"""
compute the mean and stddev of 100 data sets and plot mean vs stddev.
When you click on one of the mu, sigma points, plot the raw data from
the dataset that generated the mean and stddev
"""
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
#
# X = np.random.rand(100, 1000)
# xs = np.mean(X, axis=1)
# ys = np.std(X, axis=1)
#
G = nx.Graph()
#add three edges
G.add_edge('A','Bfsadfj;asdkfj;asdjfa;');
G.add_edge('B','C');
G.add_edge('C','A');

from networkx import *
import pylab as P
ax=P.subplot(111)
#G=dodecahedral_graph()
pos=spring_layout(G)
draw_networkx(G,pos,ax=ax)

# #draw the graph
# nx.draw(G, with_labels=True)
#
#
# # fig = plt.figure()
# # ax = fig.add_subplot(111)
# # ax.set_title('click on point to plot time series')
# # line, = ax.plot(xs, ys, 'o', picker=5)  # 5 points tolerance
#
# #
# # def onpick(event):
# #
# #     if event.artist!=line: return True
# #
# #     N = len(event.ind)
# #     if not N: return True
# #
# #
# #     figi = plt.figure()
# #     for subplotnum, dataind in enumerate(event.ind):
# #         ax = figi.add_subplot(N,1,subplotnum+1)
# #         ax.plot(X[dataind])
# #         ax.text(0.05, 0.9, 'mu=%1.3f\nsigma=%1.3f'%(xs[dataind], ys[dataind]),
# #                 transform=ax.transAxes, va='top')
# #         ax.set_ylim(-0.5, 1.5)
# #     figi.show()
# #     return True
# #
# # fig.canvas.mpl_connect('pick_event', onpick)

# G=nx.dodecahedral_graph()
nodes=nx.draw_networkx_nodes(G,pos=nx.spring_layout(G), node_shape='s')
plt.show()
#
#


# import networkx as nx
# import matplotlib.pyplot as plt
# G = nx.DiGraph()
#
# G.add_node("ROOT")
#
# for i in range(5):
#     G.add_node("Child_%i" % i)
#     G.add_node("Grandchild_%i" % i)
#     G.add_node("Greatgrandchild_%i" % i)
#
#     G.add_edge("ROOT", "Child_%i" % i)
#     G.add_edge("Child_%i" % i, "Grandchild_%i" % i)
#     G.add_edge("Grandchild_%i" % i, "Greatgrandchild_%i" % i)
#
# # write dot file to use with graphviz
# # run "dot -Tpng test.dot >test.png"
# # nx.write_dot(G,'test.dot')
#
# # same layout using matplotlib with no labels
# plt.title("draw_networkx")
# pos=nx.graphviz_layout(G,prog='dot')
# nx.draw(G,pos,with_labels=False,arrows=False)
# plt.show()

# import pygraphviz
# import networkx
# import networkx as nx
# G = nx.Graph()
# G.add_node("ROOT")
# for i in xrange(5):
#     G.add_node("Child_%i" % i)
#     G.add_node("Grandchild_%i" % i)
#     G.add_node("Greatgrandchild_%i" % i)
#     G.add_edge("ROOT", "Child_%i" % i)
#     G.add_edge("Child_%i" % i, "Grandchild_%i" % i)
#     G.add_edge("Grandchild_%i" % i, "Greatgrandchild_%i" % i)
#
# A = nx.to_agraph(G)
# A.layout('dot', args='-Nfontsize=10 -Nwidth=".2" -Nheight=".2" -Nmargin=0 -Gfontsize=8')
# A.draw('test.png')

#!/usr/bin/env python

"""
An example of the MultiDiGraph clas

The function chess_pgn_graph reads a collection of chess
matches stored in the specified PGN file
(PGN ="Portable Game Notation")
Here the (compressed) default file ---
 chess_masters_WCC.pgn.bz2 ---
contains all 685 World Chess Championship matches
from 1886 - 1985.
(data from http://chessproblem.my-free-games.com/chess/games/Download-PGN.php)

The chess_pgn_graph() function returns a MultiDiGraph
with multiple edges. Each node is
the last name of a chess master. Each edge is directed
from white to black and contains selected game info.

The key statement in chess_pgn_graph below is
    G.add_edge(white, black, game_info)
where game_info is a dict describing each game.

"""
#    Copyright (C) 2006-2010 by
#    Aric Hagberg <hagberg@lanl.gov>
#    Dan Schult <dschult@colgate.edu>
#    Pieter Swart <swart@lanl.gov>
#    All rights reserved.
#    BSD license.

import networkx as nx

# tag names specifying what game info should be
# # stored in the dict on each digraph edge
# game_details=["Event",
#               "Date",
#               "Result",
#               "ECO",
#               "Site"]
#
# def chess_pgn_graph(pgn_file="WCC.pgn"):
#     """Read chess games in pgn format in pgn_file.
#
#     Filenames ending in .gz or .bz2 will be uncompressed.
#
#     Return the MultiDiGraph of players connected by a chess game.
#     Edges contain game data in a dict.
#
#     """
#     # import bz2
#     G=nx.MultiDiGraph()
#     game={}
#     datafile = open("WCC.pgn", 'r') # bz2.BZ2File(pgn_file)
#     lines = (line.rstrip('\r\n') for line in datafile)
#     for line in lines:
#         if line.startswith('['):
#             tag,value=line[1:-1].split(' ',1)
#             game[str(tag)]=value.strip('"')
#         else:
#         # empty line after tag set indicates
#         # we finished reading game info
#             if game:
#                 white=game.pop('White')
#                 black=game.pop('Black')
#                 G.add_edge(white, black, **game)
#                 game={}
#     return G
#
#
# if __name__ == '__main__':
#     import networkx as nx
#
#
#     G=chess_pgn_graph()
#
#     ngames=G.number_of_edges()
#     nplayers=G.number_of_nodes()
#
#     print("Loaded %d chess games between %d players\n"\
#                    % (ngames,nplayers))
#
#     # identify connected components
#     # of the undirected version
#     Gcc=list(nx.connected_component_subgraphs(G.to_undirected()))
#     if len(Gcc)>1:
#         print("Note the disconnected component consisting of:")
#         print(Gcc[1].nodes())
#
#     # find all games with B97 opening (as described in ECO)
#     openings=set([game_info['ECO']
#                   for (white,black,game_info) in G.edges(data=True)])
#     print("\nFrom a total of %d different openings,"%len(openings))
#     print('the following games used the Sicilian opening')
#     print('with the Najdorff 7...Qb6 "Poisoned Pawn" variation.\n')
#
#     for (white,black,game_info) in G.edges(data=True):
#         if game_info['ECO']=='B97':
#            print(white,"vs",black)
#            for k,v in game_info.items():
#                print("   ",k,": ",v)
#            print("\n")
#
#
#     try:
#         import matplotlib.pyplot as plt
#     except ImportError:
#         import sys
#         print("Matplotlib needed for drawing. Skipping")
#         sys.exit(0)
#
#     # make new undirected graph H without multi-edges
#     H=nx.Graph(G)
#
#     # edge width is proportional number of games played
#     edgewidth=[]
#     for (u,v,d) in H.edges(data=True):
#         edgewidth.append(len(G.get_edge_data(u,v)))
#
#     # node size is proportional to number of games won
#     wins=dict.fromkeys(G.nodes(),0.0)
#     for (u,v,d) in G.edges(data=True):
#         r=d['Result'].split('-')
#         if r[0]=='1':
#             wins[u]+=1.0
#         elif r[0]=='1/2':
#             wins[u]+=0.5
#             wins[v]+=0.5
#         else:
#             wins[v]+=1.0
#     try:
#         pos=nx.graphviz_layout(H)
#     except:
#         pos=nx.spring_layout(H,iterations=20)
#
#     plt.rcParams['text.usetex'] = False
#     plt.figure(figsize=(8,8))
#     nx.draw_networkx_edges(H,pos,alpha=0.3,width=edgewidth, edge_color='m')
#     nodesize=[wins[v]*50 for v in H]
#     nx.draw_networkx_nodes(H,pos,node_size=nodesize,node_color='w',alpha=0.4)
#     nx.draw_networkx_edges(H,pos,alpha=0.4,node_size=0,width=1,edge_color='k')
#     nx.draw_networkx_labels(H,pos,fontsize=14)
#     font = {'fontname'   : 'Helvetica',
#             'color'      : 'k',
#             'fontweight' : 'bold',
#             'fontsize'   : 14}
#     plt.title("World Chess Championship Games: 1886 - 1985", font)
#
#     # change font and write text (using data coordinates)
#     font = {'fontname'   : 'Helvetica',
#     'color'      : 'r',
#     'fontweight' : 'bold',
#     'fontsize'   : 14}
#
#     plt.text(0.5, 0.97, "edge width = # games played",
#              horizontalalignment='center',
#              transform=plt.gca().transAxes)
#     plt.text(0.5, 0.94,  "node size = # games won",
#              horizontalalignment='center',
#              transform=plt.gca().transAxes)
#
#     plt.axis('off')
#     plt.savefig("chess_masters.png",dpi=75)
#     print("Wrote chess_masters.png")
#     plt.show() # display