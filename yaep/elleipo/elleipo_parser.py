import os
import re
from collections import Counter
from itertools import product
from timeit import default_timer

from nltk import TYPE
from nltk.draw.tree import TreeTabView
from nltk.featstruct import CelexFeatStructReader
from nltk.grammar import FeatStructNonterminal, Production, FeatureGrammar
from nltk.parse.featurechart import celex_preprocessing
from yaep.parse.earley import EarleyParser, Grammar, Rule, feat_struct_nonterminal_to_term,  FeatStructNonTerm
from yaep.parse.parse_tree_generator import Node, LeafNode, EllipsisEarleyParser

COORDINATIONS = ('und', 'oder')

class ElleipoNode:

    def __init__(self, features=None, gf=None, pos=None, ref = None):
        self._features = features
        self._ref = ref
        self._gf = gf
        self._pos = pos
        self._children = []

    def add_node(self, node):
        # if isinstance(node, Node):
        #     self._wordsmap.update(node._wordsmap)
        # else:
        #     self._wordsmap[node._symbol] = 1
        self._children.append(node)

    def children(self):
        return self._children

    def leaves(self):
        leaves = []
        for child in self._children:
            if child._gf == 'lex':
                leaves.append(child._pos)
            else:
                leaves.extend(child.leaves())
        return leaves

    def as_features(self):
        node_features = dict()
        if self._features:
            features = self._features.split(',')
            for feat in features:
                if '=' in feat:
                    key, val = feat.split('=')
                    if '{' in val or '}' in val: # or '~' in val:
                        val = re.sub(r'[{}]','', val)
                    node_features[key.strip()] = val.strip()


        if self._pos:
            node_features[TYPE] = self._pos
        if self._gf:
            node_features['gf'] = self._gf
        if self._ref:
            node_features['ref'] = self._ref # re.sub(r'[{}~]','', self._ref)

        return node_features

    def to_attribute_grammar(self):
        rules = []
        lhs = FeatStructNonterminal(self.as_features())
        rhs = []
        for child in self._children:
            if child._gf == 'lex':
                lhs.update({k:v for k,v in child.as_features().items() if k not in (TYPE,'gf')} )
                rhs.append(child._pos)
            else:
                rules.extend(child.to_attribute_grammar())
                nt = FeatStructNonterminal(child.as_features())
                rhs.append(nt)
        rules.insert(0, repr(Production(lhs, rhs)))
        return rules

    # def pretty_print(self, level):
    #     padding = '\n' + '\t' * level
    #     children_str = " ".join(c.pretty_print(level + 1) for c in self._children)
    #     out = "{}([{}:{}] {} {})".format(padding, self._i, self._j, unicode_repr(self._symbol), children_str if self._children else '')
    #     if level == 0:
    #         out += '\n' + str(self._wordsmap)
    #     return out

    def __str__(self):
        return "{} {} [{}]".format('' if not self._gf else self._gf,
                                      '' if not self._pos else self._pos,
                                      '' if not self._features else self._features)

    def __repr__(self):
        return "{} {} {}[{}]".format('' if not self._gf else self._gf,
                                     '' if not self._pos else self._pos,
                                     '' if not self._ref else self._ref,
                                     '' if not self._features else self._features)

    def __len__(self):
        return len(self._children)

    # ////////////////////////////////////////////////////////////
    # Indexing (with support for tree positions)
    # ////////////////////////////////////////////////////////////
    def __getitem__(self, index):
        return self._children[index]

    def __setitem__(self, index, value):
        self._children[index] = value

    def __delitem__(self, index):
        return NotImplemented

    def gf(self):
        return self._gf

    def pos(self):
        return self._pos


def parse_syntax_trees(trees_str, start_with):

    sentence = ''
    brackets_stack = []
    sentences_stack = []
    nodes_stack = []
    children = []
    n = start_with
    while n < len(trees_str):
        c = trees_str[n]
        n += 1
        if c == '(':
            child, new_index = parse_syntax_trees(trees_str, n)
            n = new_index
            children.append(child)
            if sentence:
                sentences_stack.append(sentence)
                sentence = ''
        elif c == '[':
            brackets_stack.append(c)
            if sentence:
                sentences_stack.append(sentence)
                sentence = ''
            else:
                raise ValueError("Empty nonterminal: " + sentence + c)
        elif c == ')':
            if sentences_stack:
                if nodes_stack:
                    node = nodes_stack.pop()
                else:
                    node = ElleipoNode()

                node_attr = sentences_stack.pop().split(' ')

                if len(node_attr) == 2:
                    gf, pos = node_attr
                    ref = None
                elif len(node_attr) == 3:
                    gf, pos, ref = node_attr
                else:
                    raise ValueError(
                        "Unknown node attributes: {} in {}".format(node_attr, trees_str[start_with: n + 1]))

                node._gf = gf
                node._ref = ref
                node._pos = pos
                node._children = children
                return node, n
            else:
                raise ValueError("Sentence stack is empty for unclear reason: ".format(trees_str[start_with: n + 1]))
        elif c == ']':
            if not brackets_stack or brackets_stack[-1] != '[':
                raise ValueError("Unbalanced: ] ...{}".format(trees_str[start_with: n+1]))
            else:
                brackets_stack.pop()
                nodes_stack.append(ElleipoNode(features=sentence))
                # it should be not necessary to clear sentence here. Only to be sure
                sentence = ''
        else:
            sentence += c
    # here we return the sentences
    return children, n

def extract_grammar(path, file_name):

    grammar = []
    with open(path + file_name, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('//'):  #skip comments
                continue
            grammar.append(line)

    #replace multiple whitespaces:
    grammar = re.sub('\s+', ' ', ''.join(grammar)).strip()

    nodes, n = parse_syntax_trees(grammar, 0)

    assert len(grammar) == n, "{} was not processed entirely".format(path + file_name)

    # create directory for the grammar files
    grammar_path = path + '/grammars'
    os.makedirs(grammar_path, exist_ok=True)

    for node in nodes:
        node_file = '_'.join(node.leaves()) + '.cf'
        with open(grammar_path + '/' + node_file, 'w') as grammar_file:
            grammar_file.write('\r\n'.join((node.to_attribute_grammar())))


def load_grammar(path, filename):
    assert filename, "Grammar filename should be specified"

    fstruct_reader = CelexFeatStructReader(fdict_class=FeatStructNonterminal)
    grammar = FeatureGrammar.fromstring(celex_preprocessing(path + filename), logic_parser=None, fstruct_reader=fstruct_reader, encoding=None)

    # filter features
    FEATURES_TO_FILTER = ('ref','subject', 'head')
    filtered_productions = []
    for rule in grammar.productions():
        lhs = rule.lhs().filter_feature(*FEATURES_TO_FILTER)
        if rule.is_nonlexical():
            rhs = (nt.filter_feature(*FEATURES_TO_FILTER) for nt in rule.rhs())
        else:
            rhs = rule.rhs()
        filtered_productions.append(Production(lhs,rhs))

    # return FeatureGrammar(grammar.start().filter_feature(*FEATURES_TO_FILTER), filtered_productions)
    # start_nonterminal = feat_struct_nonterminal_to_term(grammar.start().filter_feature(*FEATURES_TO_FILTER))
    start_nonterminal = feat_struct_nonterminal_to_term(FeatStructNonterminal("S[gf = 'conj']"))
    return Grammar((Rule(feat_struct_nonterminal_to_term(production.lhs()),
                                       (feat_struct_nonterminal_to_term(fs) for fs in production.rhs())) for production
                                  in filtered_productions), None, start_nonterminal)

# if __name__ == "__main__":
#     # docTEST this
#     import doctest
#     doctest.testmod()
#
#     extract_grammar('../../fsa/elleipo/', 'german-sent-struc_utf.txt')
#     # filename = 'Ich_schlafe_und_du_schläfst'
#     # filename = 'Gestern_bist_du_gegangen_und_gestern_hast_du_mich_nicht_gewarnt'
#     filename = 'Hans_ißt_Äpfel_und_Peter_ißt_Birnen'
#     # filename = 'Mit_Bier_und_mit_Würstchen_und_mit_Kartoffelsalat_grillt_Hans_mit_Maria_vor_dem_Haus_und_neben_dem_Haus_und_hinter_dem_Haus'
#     tokens = tuple(token.lower() for token in filename.split('_'))
#     grammar = load_grammar('../../fsa/elleipo/grammars/', filename + '.cf')
#
#     load_grammar_timer = default_timer()
#
#     earley_parser = EarleyParser(grammar)
#
#     manager = earley_parser.parse(tokens, grammar.start())
#     end_time = default_timer()
#     print(manager.pretty_print(filename))
#     print("Final states:")
#     final_states = tuple(manager.final_states())
#     if final_states:
#         for state in final_states:
#             print(state.str(state.dot() - 1))
#     else:
#         print(None)
#     print("Recognition time: {:.3f}s.".format(end_time - load_grammar_timer))
#
#     print(manager)
#     print(manager.out())
#
#     tree_generator = earley_parser.build_tree_generator()
#     trees = tree_generator.parseTrees(manager)
#     # for tree in tree_generator.parseTrees(manager):
#     #     print(tree.pretty_print(0))
#     #     number_trees += 1
#     # print("Number of trees: {}".format(number_trees))
#     number_trees = 0
#     number_derivation_trees = 0
#     dominance_structures = []
#     verifier = Counter(tokens)
#     end_time = default_timer()
#     if trees:
#         tree_output = ''
#         for tree in trees:
#             number_derivation_trees += 1
#             if tree.wordsmap() == verifier:
#                 number_trees += 1
#                 dominance_structures.append(tree)
#             tree_output += tree.pretty_print(0) + '\n'
#         tree_output += "Number of derivation trees: {}".format(number_derivation_trees)
#         print(tree_output)
#         print("Number of dominance structures: {}".format(number_trees))
#         print("Time: {:.3f}s.\n".format(end_time - load_grammar_timer))
#         if dominance_structures:
#             # with open('../../fsa/dominance_structures.dump', 'wb') as f:
#             #     pickle.dump(dominance_structures, f, pickle.HIGHEST_PROTOCOL)
#             TreeTabView(*dominance_structures[:40])


def parse_conjunct(grammar, tokens,  sibling_conjunct_chart_manager=None):
        if sibling_conjunct_chart_manager:
            earley_parser = EllipsisEarleyParser(grammar)
            earley_parser.set_sibling_conjunct_chart_manager(sibling_conjunct_chart_manager)
        else:
            earley_parser = EarleyParser(grammar)
        manager = earley_parser.parse(tokens, grammar.start())

        tree_generator = earley_parser.build_tree_generator(manager)
        trees = tree_generator.parseTrees(manager)

        number_verified_trees = 0
        number_derivation_trees = 0
        dominance_structures = []
        verifier = Counter(tokens)
        if trees:
            tree_output = ''
            for tree in trees:
                number_derivation_trees += 1
                if all(item in tree.wordsmap().items() for item in verifier.items()):
                    number_verified_trees += 1
                    dominance_structures.append(tree)
                tree_output += tree.pretty_print(0) + '\n'

            tree_output += "Number of derivation trees: {}".format(number_derivation_trees)
            print(tree_output)
            print("Number of dominance structures: {}".format(number_verified_trees))
        return manager, dominance_structures

def parse_ellipses(grammar, tokens):
    sentence_coordinations = []
    group = []
    token_groups = []
    for token in tokens:
        if token not in COORDINATIONS:
            group.append(token)
        else:
            sentence_coordinations.append(token)
            token_groups.append(group)
            group = []
    else:
        if group:
            token_groups.append(group)

    parsing_results = []
    for group in token_groups:
        chart_manager, dominance_structures = parse_conjunct(grammar, group, parsing_results[-1][0] if parsing_results else None)
        print(chart_manager)
        print(chart_manager.out())
        parsing_results.append((chart_manager, dominance_structures))

    for index, (manager, dominance_structures) in enumerate(parsing_results):
        if not dominance_structures and index < (len(parsing_results) - 1):
            new_manager, new_dominanace_structures = parse_conjunct(grammar, token_groups[index], parsing_results[-1][0] if parsing_results else None)
            print(new_manager)
            print(new_manager.out())
            if new_dominanace_structures:
                parsing_results[index] = (new_manager, new_dominanace_structures)


    if all(dominance_structures for manager, dominance_structures in parsing_results):
        for prod in product(*(dominance_structures for manager, dominance_structures in parsing_results), repeat=1):
            root = Node(FeatStructNonTerm(FeatStructNonterminal("S[gf='expr']"))) # "S[gf='expr']"
            for index, node in enumerate(prod):
                root.add_node(node)
                if index < len(sentence_coordinations):
                    coord = Node(FeatStructNonTerm(FeatStructNonterminal("C[gf='coord']")))
                    coord.add_node(LeafNode(sentence_coordinations[index]))
                    root.add_node(coord)
            yield root

if __name__ == "__main__":
    # docTEST this
    import doctest
    doctest.testmod()

    # uncomment this line extract grammar from the syntactic trees
    # extract_grammar('../../fsa/elleipo/', 'german-sent-struc_utf.txt')

    # filename = 'Ich_schlafe_und_du_schläfst'
    # input = "Ich schlafe und du" # auch

    # filename = 'Hans_ißt_Äpfel_und_Peter_ißt_Birnen'
    # input = 'Hans ißt Äpfel und Peter Birnen'
    # input = 'Hans ißt Äpfel und Peter' # auch

    # filename = 'Gestern_bist_du_gegangen_und_gestern_hast_du_mich_nicht_gewarnt'
    # filename = 'Mit_Bier_und_mit_Würstchen_und_mit_Kartoffelsalat_grillt_Hans_mit_Maria_vor_dem_Haus_und_neben_dem_Haus_und_hinter_dem_Haus'

    # filename = 'Hans_schläft_und_Peter_schläft'
    # input = "Hans schläft und Peter"  # auch

    # filename = "Hans_will_schlafen_und_Peter_will_schlafen"
    # input = "Hans will schlafen und Peter"  # auch

    # All elisions         : Meine Frau will_1 ein Auto kaufen_1-b_2 und mein Sohn will-g_1 ein Motorrad kaufen-gl_1_2
    # Reduced sentence     : Meine Frau will_1 ein Auto kaufen_1 und mein Sohn ---g_1 ein Motorrad ---g_1
    # BCR-Alternative      : Meine Frau will_1 ein Auto ---_2 und mein Sohn ---_1 ein Motorrad kaufen_2"""
    # filename = "Meine_Frau_will_ein_Auto_kaufen_und_mein_Sohn_will_ein_Motorrad_kaufen"
    # input = "Meine Frau will ein Auto kaufen und mein Sohn ein Motorrad"
    # input = "Meine Frau will ein Auto und mein Sohn ein Motorrad kaufen"

    # All elisions         : Der Fahrer wurde_1 getötet und die Passagiere wurden-g_1 ernsthaft verletzt
    # filename = "Der_Fahrer_wurde_getötet_und_die_Passagiere_wurden_ernsthaft_verletzt"
    # input = "Der Fahrer wurde getötet und die Passagiere ernsthaft verletzt"

    # All elisions         : Hans_1_2 kann_1_2 schlafen und Hans-g_1-f_2 kann-g_1-f_2 träumen
    # filename = "Hans_kann_schlafen_und_Hans_kann_träumen"
    # input = " Hans kann schlafen und träumen"

    # Original sentence   7: Ich sehe Hans der schläft im Auto und ich sehe Hans der schläft im Bus
    # All elisions         : Ich_1_2 sehe_1_2 Hans_1_2 der_1_2 schläft_1_2 im Auto und ich-g_1-f_2 sehe-g_1-f_2 Hans-g_1-f_2 der-g_1-f_2 schläft-g_1-f_2 im Bus

    # TODO: This example doesn't work because using NP Coord instead of S coord S
    # Original sentence  43: Ich sehe Hans der im Auto schläft und Hans der im Bus schläft
    # All elisions         : Ich sehe Hans_1 der im Auto schläft-b_2 und Hans-f_1 der im Bus schläft_2
    # Reduced sentence     : Ich sehe Hans_1 der im Auto ---b_2 und ---f_1 der im Bus schläft_2
    # (expr S(subj NP 20~[{40},ref=7](head PersPron 21~[{40},ref=7](lex Ich 40~[stem=I,case=1,person=1,number=sg])))(head V 5~[{6},ref=9](lex sehe 26~[stem=see,tense=present,person=1,number=sg,mode=active]))(dobj NP 2~[{4},ref=6](conj NP 33~[subject={10},ref=19,head={11}](head PropN 3~[{4},ref=6](lex Hans 4~[stem=Hans,case=1,person=3,number=sg,gender=masc]))(mod S 7~[subject={10},mod-type=rel,ref=21,head={11}](subj NP 8~[{10},ref=2](head RelP 9~[{10},ref=2](lex der 10~[stem=who,case=1,person=3,number=sg,gender=masc])))(mod PP 12~[{14},mod-type=loc,ref=6](head Prep 5~[{6},ref=13](lex im 6~[stem=in-the]))(obj NP 2~[{4},ref=11](head N 3~[{4}t,ref=11](lex Auto 4~[stem=car,case=3,person=3,number=sg,gender=neuter]))))(head V 5~[{6},ref=11](lex schläft 6~[stem=sleep,tense=present,person=3,number=sg,mode=active]))))(coord C 13~[{12}](lex und 12~[stem=and]))(conj NP 30~[subject={10},ref=20,head={11}](head PropN 3~[{4},ref=6](lex Hans 4~[stem=Hans,case=1,person=3,number=sg,gender=masc]))(mod S 7~[subject={10},mod-type=rel,ref=22,head={11}](subj NP 8~[{10},ref=2](head RelP 9~[{10},ref=2](lex der 10~[stem=who,case=1,person=3,number=sg,gender=masc])))(mod PP 12~[{14},mod-type=loc,ref=36](head Prep 5~[{6},ref=13](lex im 6~[stem=in-the]))(obj NP 2~[{4},ref=31](head N 3~[{4},ref=31](lex Bus 4~[stem=bus,case=3,person=3,number=sg,gender=neuter]))))(head V 5~[{6},ref=11](lex schläft 6~[stem=sleep,tense=present,person=3,number=sg,mode=active]))))))
    # filename = "Ich_sehe_Hans_der_im_Auto_schläft_und_Hans_der_im_Bus_schläft"
    # input = "Ich sehe Hans der im Auto schläft und und Hans der im Bus schläft"

    # Original sentence  45: Ich will hoffen dass Hans schläft und du willst hoffen dass Peter schläft
    # All elisions         : Ich will_1 hoffen_1 dass Hans schläft-b_2 und du willst-g_1 hoffen-g_1 dass Peter schläft_2
    # Reduced sentence     : Ich will_1 hoffen_1 dass Hans ---b_2 und du ---g_1 ---g_1 dass Peter schläft_2
    filename = "Ich_will_hoffen_dass_Hans_schläft_und_du_willst_hoffen_dass_Peter_schläft"
    input = "Ich will hoffen dass Hans und du dass Peter schläft"

    grammar = load_grammar('../../fsa/elleipo/grammars/', filename + '.cf')

    # tokens = tuple(token for token in filename.split('_'))
    # # tokens = tokens[0:4]
    # # tokens = tokens[0:5] + tokens[6:]
    # print(" ".join(tokens))

    ellipses = tuple(parse_ellipses(grammar, input.split()))
    print("Number of trees: {}".format(len(ellipses)))
    if ellipses:
        TreeTabView(*ellipses[:40])