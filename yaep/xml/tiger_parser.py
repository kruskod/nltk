import csv
import xml.etree.ElementTree as ET
from operator import itemgetter

from nltk import TYPE
from nltk.grammar import FeatStructNonterminal, Production
from nltk.topology.pgsql import get_word_inf, get_lemma, get_wordform


def get_wordforms(path, file_name):
    tree = ET.parse(path + file_name)
    root = tree.getroot()

    terminals = root.findall('body/s/graph/terminals/t')
    missing_lemmas = set()
    for child in terminals:
        # word = child.get('word', default=None)
        lemma = child.get('lemma', default=None)
        if lemma != '--':
            lemma_inf = get_lemma(lemma)
            if next(lemma_inf, None) is None:
                lemma_atr = child.attrib
                pos = lemma_atr['pos']
                morph = lemma_atr['morph']
                # missing_lemmas.add((None if pos == '--' else pos, lemma, None if morph == '--' else morph))
                missing_lemmas.add((pos, lemma, morph))

    if missing_lemmas:
        with open(path + 'missing_lemmas.csv', "w") as f:
            csv_writer = csv.writer(f, delimiter=';', quotechar='|', quoting=csv.QUOTE_ALL)
            for lemma_inf in sorted(missing_lemmas, key=itemgetter(0,1)):
                csv_writer.writerow(lemma_inf)

def extract_grammar(path, file_name):
    tree = ET.parse(path + file_name)
    root = tree.getroot()

    for graph in root.findall('body/s/graph'):
        root = graph.get('root', default=None)
        discontinuous = graph.get('discontinuous', default='').lower() == 'true'
        if discontinuous:
            terminals = dict()
            nonterminals = dict()
            tree_hierarchy = dict()

            for item in graph:
                if 'terminals' == item.tag:
                    for term in iter(item):
                        terminals[term.get('id')] = term
                        # print(term.tag + ' ' + str(term.attrib))
                        # check if terminal has a secondary edge
                        for secedge in term:
                           # print(secedge.tag + ' ' + str(secedge.attrib))
                           idref = secedge.get('idref') # Modified idref of secedge to convert it to the 'normal' edge
                           secedge.set('idref', term.get('id'))
                           tree_hierarchy.setdefault(idref, list()).append(secedge)
                elif 'nonterminals' == item.tag:
                    for nt in iter(item):
                        nt_id = nt.get('id')
                        nonterminals[nt_id] = nt
                        container = tree_hierarchy.setdefault(nt_id, list())
                        for edge in nt:
                            if edge.tag == 'edge':
                                container.append(edge)
                            elif edge.tag == 'secedge':
                                idref = edge.get('idref')   # Modified idref of secedge to convert it to the 'normal' edge
                                edge.set('idref', nt_id)
                                tree_hierarchy.setdefault(idref, list()).append(edge)
        # print(graph.tag + ' ' + str(graph.attrib))
        # print tree
        productions = list(generate_CFG(tree_hierarchy, nonterminals, terminals, root))
        # productions = list(flat_generate_CFG(tree_hierarchy, nonterminals, terminals))
        print("\n".join(str(prod) for prod in productions))
        break


def generate_CFG(tree_hierarchy, nonterminals, terminals, node_id, parent=None):
    root = nonterminals.get(node_id, None)

    if root:
        lhs_features = dict(root.attrib)
        lhs_features[TYPE] = lhs_features['cat']
        lhs = FeatStructNonterminal({key:val for key,val in lhs_features.items() if key not in ('cat',)})  # 'id' filter cat and id features here because they are not more needed
        rhs = []
        for edge in tree_hierarchy[node_id]:
            idref = edge.attrib.get('idref')
            nt_features = dict(edge.attrib)
            nt_features[TYPE] = nt_features.get('label')
            nt_features['id'] = idref
            # ref_edge = nonterminals.get(idref, None)
            # if ref_edge:    # our edge is a terminal
            #     nt_features[TYPE] = ref_edge.attrib['cat']
            # else:
            #     ref_edge = terminals.get(idref, None)
            #     nt_features[TYPE] = ref_edge.attrib['pos']
            # nt_features.update(ref_edge.attrib)
            nt = FeatStructNonterminal({key: val for key, val in nt_features.items() if key not in ('idref', 'label')})
            if edge.tag != 'secedge':
                yield from generate_CFG(tree_hierarchy, nonterminals, terminals, idref, parent=edge)
            rhs.append(nt)  # playing with this row we can put or not secondary edges to the production
            # else: # the node with secondary edges => add all secondary edges to rhs
            #
            #     return
        yield Production(lhs, tuple(rhs))
    else:
        root = terminals.get(node_id)
        parent_features = dict(parent.attrib)
        parent_features[TYPE] = root.attrib.get('pos')
        parent_features.update(root.attrib)
        lhs = FeatStructNonterminal({key: val for key, val in parent_features.items() if key not in ('idref', 'pos', 'word')})  # filter cat and id features here because they are not more needed
        yield Production(lhs, (root.attrib.get('word'),))

    if parent != None:
        nt_features = dict(parent.attrib)
        nt_features[TYPE] = nt_features.get('label')
        nt_features['id'] = root.attrib.get('id')
        # nt_features.update(root.attrib)
        # ref_edge = nonterminals.get(idref, None)
        # if ref_edge:    # our edge is a terminal
        #     nt_features[TYPE] = ref_edge.attrib['cat']
        # else:
        #     ref_edge = terminals.get(idref, None)
        #     nt_features[TYPE] = ref_edge.attrib['pos']
        # nt_features.update(ref_edge.attrib)
        parent_node = FeatStructNonterminal({key: val for key, val in nt_features.items() if key not in ('idref', 'label')})
        yield Production(parent_node, (FeatStructNonterminal({key: val for key, val in lhs.items() if key in ('id', TYPE)}),))









if __name__ == "__main__":
    # docTEST this
    import doctest
    doctest.testmod()

    # '/home/kunz/workspace/nltk/fsa/gapping1.xml'
    #get_wordforms('../../fsa/', 'tiger_grammar.xml')

    extract_grammar('../../fsa/', 'gapping_vmfin.xml')


    # tokens1 = ["Mary", "called", "Jan"]
    # tokens2 = ["Mary", "called", "Jan", "from", "Frankfurt"]
    # print_trees(tokens2, grammar = grammar_from_file('../test/parse/grammar.txt'), permutations=False)
    # print_trees(tokens2, grammar = grammar_from_file('../test/parse/grammar.txt'), permutations=True)
    #
    # tokens = "ich sehe".split()
    # print_trees(tokens, grammar=performance_grammar(tokens), permutations=True)
