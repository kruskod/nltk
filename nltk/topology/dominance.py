import pickle

from nltk.draw.tree import TreeTabView, Graphview
from nltk.topology.FeatTree import FeatTree
from nltk.topology.pygraphviz.graph import draw_graph
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
        # print(*feat_tree.bfs())
        alternatives = feat_tree.split_alternatives()

        #alternatives = [alternatives[0],]

        result = []

        #alternatives = (alternatives[2],)

        for alternative in alternatives:
            print(" ".join(alternative.leaves()))
            alternative.share()
            result.extend(alternative.split_shared_topologies())


        alternatives = []
        print("\nAlternatives validaton:")
        for index, alternative in enumerate(result):
            isvalid = validate_alternative(alternative)
            print("Alternative {} {}: {} \n Word order: {}".format(index, repr(alternative.topologies), isvalid, " ".join(alternative.leaves())))
            if isvalid:
                alternatives.append(alternative)

        # result = alternatives[2]
        # result.share()
        # alternatives = []
        # alternatives.extend(result.split_shared_topologies())

        #result=alternatives

        # testee = alternatives[0]
        # testee.share()
        #
        # for edge in testee.bfs():
        #     for top in edge.topologies:
        #         print(top.shared_trace + '-' + str(top))

        # for i, alternative in enumerate(alternatives):
        #     print("Alternative: ", i)
        #     print(*alternative.bfs())



        print("Number alternatives: ", len(alternatives))
        #draw_graph(alternatives[0])
        if alternatives:
            # alternatives = (alternatives[4],)
            Graphview(*sorted(alternatives[:20], key=FeatTree.leaves))
            #TreeTabView(*alternatives[:20])
        # print(alternatives)
        # print(feat_tree)
        print(80*'#')
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
