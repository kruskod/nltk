import pickle

from nltk.draw.tree import Graphview
from nltk.topology.FeatTree import FeatTree
from nltk.topology.topology import process_dominance, build_topologies
from yaep.parse.parse_tree_generator import Node


def wordorder_alternatives(feat_tree, topologies):
    feat_tree.topologies.extend(process_dominance(feat_tree, topologies))
    # print(feat_tree.topologies)
    feat_tree.alternatives()
    # print(*feat_tree.bfs())
    alternatives = feat_tree.split_alternatives()

    shared_alternatives = []

    for alternative in alternatives:
        print("\t" + " ".join(alternative.leaves()))
        alternative.share()
        shared_alternatives.extend(alternative.split_shared_topologies())

    print("\nAlternatives validaton:")
    for index, alternative in enumerate(shared_alternatives):
        isvalid = validate_alternative(alternative)
        print("Alternative {} {}: {} \n Word order: {}".format(index, repr(alternative.topologies), isvalid, "\t" + " ".join(alternative.leaves())))
        if isvalid:
            yield alternative


def demo(dump_path='../../fsa/dominance_structures.dump'):
    with open(dump_path, 'rb') as f:
        dumped_trees = pickle.load(f)

    topologies = build_topologies()

    alternatives = []
    for tree in dumped_trees:
        print(tree.pretty_print(0))
        if isinstance(tree, Node):
            feat_tree = FeatTree.from_node(tree)
        else:
            feat_tree = FeatTree(tree)
        alternatives.extend(wordorder_alternatives(feat_tree, topologies))

    if alternatives:
        Graphview(*sorted(alternatives[:20], key=FeatTree.leaves))
    # ps2pdf -dEPSCrop Monopole_tree.ps

def validate_alternative(alternative):
    if not alternative.topologies:
        return False

    for edge in alternative:
        if not edge.ishead():
            if not validate_alternative(edge):
                return False
    return True

if __name__ == "__main__":
    demo()
