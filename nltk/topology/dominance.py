import copy
import pickle

from nltk.topology.FeatTree import FeatTree
from nltk.topology.topology import process_dominance, build_topologies


def demo(dump_path='../../fsa/dominance_structures.dump'):

    with open(dump_path, 'rb') as f:
        dumped_trees = pickle.load(f)

    topologies = build_topologies()
    # top_dict = dict()
    # for topology in topologies:
    #     top_dict[topology.tag] = copy.copy(topology)
    for tree in dumped_trees:
        print(tree)
        feat_tree = FeatTree(tree)
        feat_tree.topologies.extend(process_dominance(feat_tree, topologies))
        # print(feat_tree.topologies)
        feat_tree.alternatives()
        print(*feat_tree.bfs())
        # print(feat_tree)
        print(80*'#')

if __name__ == "__main__":
    demo()
