import copy
import pickle
from collections import Set
from timeit import default_timer as timer

import itertools

from nltk import Variable
from nltk.draw.tree import TreeTabView
from nltk.featstruct import CelexFeatStructReader, TYPE, unify
from nltk.grammar import FeatStructNonterminal, FeatureGrammar, Production
from nltk.parse.earleychart import wordPresenceVerifier, wordPresenceClauseVerifier
from nltk.parse.featurechart import FeatureTopDownChartParser, FeatureTreeEdge
from nltk.topology.FeatTree import FeatTree, STATUS, PH, GF, find_head, get_feature
from nltk.topology.compassFeat import STATUS_FEATURE, PRODUCTION_ID_FEATURE, LEMMA_FEATURE, NUMBER_FEATURE, \
    PERSON_FEATURE, GENDER_FEATURE, PROPER_NOUN_FEATURE
from nltk.topology.dominance import wordorder_alternatives
from nltk.topology.pgsql import build_rules, build_productions, build_wordform_productions
from nltk.topology.topology import build_topologies

__author__ = 'Denis Krusko: kruskod@gmail.com'

COORDINATIONS = ('und','oder')


class Ellipse:

    def __init__(self, input=None):
        self.input = input

def input_string_preprocessing(print_times=True,
                               print_grammar=False,
                               print_trees=True,
                               trace=1,
                               sent='Märkte sollen getrennt werden',
                               numparses=0):

    tokens = sent.split()

    fstruct_reader = CelexFeatStructReader(fdict_class=FeatStructNonterminal)

    token_groups = []
    group = []
    for token in tokens:
        if token not in COORDINATIONS:
            group.append(token)
        else:
            token_groups.append(group)
            group = []
    else:
        if group:
            token_groups.append(group)

    previous_dominance_structures = None
    previous_featureGrammar = None
    topologies = build_topologies()
    for group in token_groups:
        dominance_structures = []
        count_trees = 0
        featureGrammar = build_rules(group, fstruct_reader, dump=True)

        if previous_dominance_structures and previous_featureGrammar and is_gapping_possible(featureGrammar):
            wordforms, productions = gapping(previous_featureGrammar, previous_dominance_structures, fstruct_reader)
            featureGrammar = FeatureGrammar(FeatStructNonterminal("S[status='Fin']"), productions + featureGrammar.productions())
            cp = FeatureTopDownChartParser(featureGrammar, use_agenda=True, trace=trace)
            if wordforms and isinstance(wordforms[0], str):
                wordforms = (wordforms,)
            for wordform_combination in itertools.product(*wordforms):
                for tree in cp.parse(tuple(group) + wordform_combination):
                    count_trees += 1
                    if wordPresenceClauseVerifier(group, tree.leaves()):
                        try:
                            dominance_structures.append(tree)
                        except ValueError:
                            pass
                # Take 10 first sentences
                if len(dominance_structures) > 9:
                    break

        else:
            cp = FeatureTopDownChartParser(featureGrammar, use_agenda=True, trace=trace)
            for tree in cp.parse(group):
                count_trees += 1
                if wordPresenceClauseVerifier(group, tree.leaves()):
                    try:
                        dominance_structures.append(tree)
                    except ValueError:
                        pass


        if dominance_structures:
            print("####################################################")
            print("Dominance structures:")
            dominance_structures = sorted(dominance_structures, key=lambda tree: ' '.join(tree.leaves()).lower())

            wordorder_structures = []
            for tree in dominance_structures:
                wordorder_structures.extend(wordorder_alternatives(tree, topologies))
            with open('../../fsa/dominance_structures.dump', 'wb') as f:
                pickle.dump(wordorder_structures, f, pickle.HIGHEST_PROTOCOL)
        # print("####################################################")
        # print("Nr trees:", count_trees)
        # print("Nr Dominance structures:", len(dominance_structures))
        # print('Count of productions:', len(cp._grammar._productions))
        # print("Time: {:.3f}s.\n".format(end_time - t))

        # fcr(dominance_structures)

        if wordorder_structures:
            if (len(token_groups) > 1):
                previous_dominance_structures = wordorder_structures
                previous_featureGrammar = featureGrammar
            TreeTabView(*wordorder_structures[:60])

    # print(token_groups)

def fcr(dominance_structures):
    for tree in dominance_structures:
        feat_tree = FeatTree(tree)
        mc = list(feat_tree.major_constituents())
        pass

def is_gapping_possible(featureGrammar):
    productions = featureGrammar.productions()
    for production in productions:
        lhs = production.lhs()
        if lhs[TYPE] == PH.v.name and lhs.has_feature({STATUS_FEATURE:STATUS.Fin.name}):
            return False
    return True

def extract_gapping_edges(feat_tree, productions, fstruct_reader):
    major_constituents = list(feat_tree.major_constituents())
    if feat_tree.ph == PH.S:
        head = find_head(feat_tree)
        head_nt = head.label()
        prodId = get_feature(head_nt, PRODUCTION_ID_FEATURE)
        lemma = get_feature(head_nt, LEMMA_FEATURE)
        if prodId and lemma:
            # yield build_productions(lemma.pop(), prodId.pop(), fstruct_reader)
            wordforms, wordform_productions = build_wordform_productions(iter(lemma).__next__(), iter(prodId).__next__(), fstruct_reader)

            # extract all S and inherited productions for productionId
            tree_lhs = feat_tree.label()
            tree_rhs_gf = set()
            for item in feat_tree:
                tree_rhs_gf.add(item.gf.name)

            for production in productions:
                lhs = production.lhs()
                production_prodId = lhs.get_feature(PRODUCTION_ID_FEATURE)
                if production_prodId:
                    if production_prodId in prodId:
                        wordform_productions.add(production)
                elif lhs[TYPE] == PH.S.name and lhs.get_feature(LEMMA_FEATURE) in lemma and unify(tree_lhs, lhs):
                    # filter this production and add to production_list
                    production_rhs = tuple(rhs for rhs in production.rhs() if rhs[TYPE] in tree_rhs_gf)
                    if len(production_rhs) == len(tree_rhs_gf):
                        wordform_productions.add(Production(lhs, production_rhs))

            # # Generate a strict S production from a tree
            # lhs = feat_tree.label().filter_feature(NUMBER_FEATURE, PERSON_FEATURE, GENDER_FEATURE)
            # lhs.add_feature({NUMBER_FEATURE: Variable('?' + NUMBER_FEATURE) , PERSON_FEATURE:  Variable('?' + PERSON_FEATURE), GENDER_FEATURE:  Variable('?' + GENDER_FEATURE)})
            # rhs = []
            # for node in feat_tree:
            #     nt = node.label()
            #     if node.gf == GF.hd:
            #         nt = nt.filter_feature(NUMBER_FEATURE, PERSON_FEATURE, GENDER_FEATURE)
            #         nt.add_feature({NUMBER_FEATURE: Variable('?' + NUMBER_FEATURE) , PERSON_FEATURE:  Variable('?' + PERSON_FEATURE), GENDER_FEATURE:  Variable('?' + GENDER_FEATURE)})
            #         rhs.append(nt)
            #     elif node.gf == GF.subj:
            #         nt = nt.filter_feature(LEMMA_FEATURE, NUMBER_FEATURE, PERSON_FEATURE, GENDER_FEATURE,
            #                                PROPER_NOUN_FEATURE)
            #         nt.add_feature({NUMBER_FEATURE: Variable('?' + NUMBER_FEATURE) , PERSON_FEATURE:  Variable('?' + PERSON_FEATURE), GENDER_FEATURE:  Variable('?' + GENDER_FEATURE)})
            #         rhs.append(nt)
            #     else:
            #         nt = nt.filter_feature(LEMMA_FEATURE, NUMBER_FEATURE, PERSON_FEATURE, GENDER_FEATURE, PROPER_NOUN_FEATURE)
            #         # nt.add_feature({NUMBER_FEATURE: Variable('?' + NUMBER_FEATURE) , PERSON_FEATURE:  Variable('?' + PERSON_FEATURE), GENDER_FEATURE:  Variable('?' + GENDER_FEATURE)})
            #         rhs.append(nt)
            # wordform_productions.add(Production(lhs, tuple(rhs)))

            # extract hd -> v rules
            # for production in productions:
            #     lhs = production.lhs()
            #     if lhs[TYPE] == GF.hd.name and lhs.get_feature(PRODUCTION_ID_FEATURE) in prodId:
            #         wordform_productions.add(production)

            yield (wordforms, wordform_productions)

            # for production in productions:
            #     if production.lhs()[TYPE] == PH.S.name:
            #         rhs = production.rhs()
            #         for index,nt in enumerate(rhs):
            #             if nt[TYPE] == GF.hd.name: #head found
            #                 if nt.get_feature(PRODUCTION_ID_FEATURE) in prodId:
            #                     # rule found extract it
            #                     reordered_rhs = tuple((nt,) + rhs[:index] + rhs[index+1:])
            #                     pass
                                # yield FeatureTreeEdge(span=(0, len(head)), lhs=production.lhs(),
                                #                 rhs=reordered_rhs, dot=1)

    for constituent in major_constituents:
        if constituent.gf == GF.cmpr:
            break
    else:
        for constituent in major_constituents:
            if constituent.gf == GF.cmp and constituent.ph == PH.S:
            # if not constituent.ishead():
                yield from extract_gapping_edges(constituent, productions, fstruct_reader)

def gapping(previous_feature_grammar, dominance_structures, fstruct_reader):
    all_wordForms = set()
    all_productions = set()
    for tree in dominance_structures:
        feat_tree = FeatTree(tree)
        edges_iter = extract_gapping_edges(feat_tree, previous_feature_grammar.productions(), fstruct_reader)
        for gapping_edges in edges_iter:
            wordForms, productions = gapping_edges
            all_wordForms.add(tuple(wordForms))
            all_productions.update(productions)
    return sorted(all_wordForms), sorted(all_productions)

if __name__ == "__main__":
    # input_string_preprocessing("Monopole sollen geknackt und Märkte getrennt werden")
   # input_string_preprocessing(sent="Bücher liest Mary und schreibt Peter") # "Bücher liest Mari und Bücher schreibt Jüri"
   input_string_preprocessing(sent="Hans ißt Äpfel und Peter Birnen") # "Bücher liest Mari und Bücher schreibt Jüri"
   # input_string_preprocessing(sent="meine Frau will ein Auto kaufen und mein Sohn ein Motorrad") # "Bücher liest Mari und Bücher schreibt Jüri"
   # input_string_preprocessing(sent="Frau will Auto kaufen und Sohn Motorrad") # "Bücher liest Mari und Bücher schreibt Jüri"
