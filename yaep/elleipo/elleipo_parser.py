import csv
import os
import re
import xml.etree.ElementTree as ET
from copy import copy
from operator import itemgetter
from timeit import default_timer

from nltk import TYPE
from nltk.featstruct import CelexFeatStructReader
from nltk.grammar import FeatStructNonterminal, Production, FeatureGrammar
from nltk.parse.featurechart import celex_preprocessing
from nltk.topology.orderedSet import OrderedSet
from nltk.topology.pgsql import get_word_inf, get_lemma, get_wordform
from yaep.parse.earley import EarleyParser, grammar_from_file, Grammar, Rule, nonterminal_to_term, \
    feat_struct_nonterminal_to_term


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
                rhs.append(child._pos.lower())
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
    FEATURES_TO_FILTER = ('ref',)
    filtered_productions = []
    for rule in grammar.productions():
        lhs = rule.lhs().filter_feature(*FEATURES_TO_FILTER)
        if rule.is_nonlexical():
            rhs = (nt.filter_feature(*FEATURES_TO_FILTER) for nt in rule.rhs())
        else:
            rhs = rule.rhs()
        filtered_productions.append(Production(lhs,rhs))

    # return FeatureGrammar(grammar.start().filter_feature(*FEATURES_TO_FILTER), filtered_productions)
    start_nonterminal = feat_struct_nonterminal_to_term(grammar.start().filter_feature(*FEATURES_TO_FILTER))
    return Grammar((Rule(feat_struct_nonterminal_to_term(production.lhs()),
                                       (feat_struct_nonterminal_to_term(fs) for fs in production.rhs())) for production
                                  in filtered_productions), None, start_nonterminal)

if __name__ == "__main__":
    # docTEST this
    import doctest
    doctest.testmod()

    extract_grammar('../../fsa/elleipo/', 'german-sent-struc_utf.txt')
    # filename = 'Ich_schlafe_und_du_schläfst'
    filename = 'Gestern_bist_du_gegangen_und_gestern_hast_du_mich_nicht_gewarnt'
    # filename = 'Mit_Bier_und_mit_Würstchen_und_mit_Kartoffelsalat_grillt_Hans_mit_Maria_vor_dem_Haus_und_neben_dem_Haus_und_hinter_dem_Haus'
    tokens = tuple(token.lower() for token in filename.split('_'))
    grammar = load_grammar('../../fsa/elleipo/grammars/', filename + '.cf')

    load_grammar_timer = default_timer()

    earley_parser = EarleyParser(grammar)

    manager = earley_parser.parse(tokens, grammar.start())
    end_time = default_timer()
    print(manager.pretty_print(filename))
    print("Final states:")
    final_states = tuple(manager.final_states())
    if final_states:
        for state in final_states:
            print(state.str(state.dot() - 1))
    else:
        print(None)
    print("Recognition time: {:.3f}s.".format(end_time - load_grammar_timer))

    print(manager)
    print(manager.out())

    tree_generator = earley_parser.build_tree_generator()
    number_trees = 0
    for tree in tree_generator.parseTrees(manager):
        print(tree.pretty_print(0))
        number_trees += 1
    print("Number of trees: {}".format(number_trees))
