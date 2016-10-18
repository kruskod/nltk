from functools import reduce
from collections import Counter

from nltk import CFG
from nltk import featstruct
from nltk.compat import unicode_repr
from nltk.grammar import FeatStructNonterminal, Production, FeatureGrammar, Nonterminal
from nltk.featstruct import CelexFeatStructReader, TYPE, unify, retract_bindings
from nltk.topology.compassFeat import PRODUCTION_ID_FEATURE, BRANCH_FEATURE
from nltk.topology.orderedSet import OrderedSet
from nltk.topology.pgsql import build_rules
from timeit import default_timer as timer
import sys

from yaep.parse.earley import State, FeatStructNonTerm, nonterminal_to_term, Grammar, Rule, EarleyParser, NonTerm, \
    pase_tokens, PermutationEarleyParser, grammar_from_file, performance_grammar, AbstractEarley, Chart, \
    feat_struct_nonterminal_to_term, is_nonterminal
from abc import ABCMeta, abstractmethod


class BindingsRule(Rule):

    def __init__(self, lhs, rhs):
        super().__init__(lhs,rhs)
        self._bindings = {}

    def bindings(self):
        return self._bindings

class BindingsGrammar(Grammar):

    def find_rule(self, non_terminal, bindings=None):
        if bindings is None:
            bindings = {}
        rules = self._rules.get(non_terminal.key())
        if rules:
            for rule in rules:
                result = non_terminal.unify(rule.lhs(), bindings)
                if result:
                    rule._bindings = retract_bindings(result, bindings)
                    yield rule

class BindingsPermutationEarleyParser(AbstractEarley):

    def init(self, tokens):
        self._tokens = tokens
        self._words_map = Counter(tokens)
        self._charts = tuple(Chart() for i in range(len(tokens) + 1))

    def build_tree_generator(self):
        from yaep.parse.parse_tree_generator import PermutationParseTreeGenerator
        return PermutationParseTreeGenerator(self._words_map)

    def predictor_non_terminal(self, lhs, token_index):
        for rule in self._grammar.find_rule(lhs):
            self._charts[token_index].add_state(State(rule, token_index, 0))

    def predictor(self, state, token_index):
        lhs = state.next_symbol()
        self.predictor_non_terminal(lhs, token_index)
        if lhs.is_nullable():
            self._charts[token_index].add_state(State(state.rule(), state.from_index(), state.dot() + 1))

    def scanner(self, state, token_index):
        if state.next_symbol() in self._words_map:
            self._charts[token_index + 1].add_state(State(state.rule(), state.from_index(), state.dot() + 1))

    def completer(self, origin_state, token_index):
        lhs = origin_state.rule().lhs()
        current_chart = self._charts[token_index]
        for temp_state in self._charts[origin_state.from_index()].states():
            if (not temp_state.is_finished()) and is_nonterminal(temp_state.next_symbol()) and lhs.unify(temp_state.next_symbol()):
                current_chart.add_state(State(temp_state.rule(), temp_state.from_index(), temp_state.dot() + 1))

    def words_map(self):
        return self._words_map

def bindings_performance_grammar(tokens):
    fstruct_reader = CelexFeatStructReader(fdict_class=FeatStructNonterminal)
    grammar =  build_rules(tokens, fstruct_reader)
    productions = grammar.productions()
    start_nonterminal = feat_struct_nonterminal_to_term(grammar.start())

    return BindingsGrammar((BindingsRule(feat_struct_nonterminal_to_term(production.lhs()),
                  (feat_struct_nonterminal_to_term(fs) for fs in production.rhs())) for production in productions),
            None, start_nonterminal)

def print_trees(tokens, grammar, permutations = False):
    parser = BindingsPermutationEarleyParser(grammar) if permutations else  EarleyParser(grammar)
    chart_manager = parser.parse(tokens, grammar.start())
    print()
    print(chart_manager)
    print(chart_manager.out())

    tree_generator = parser.build_tree_generator()
    trees = tree_generator.parseTrees(chart_manager)
    tree_output = ''
    for tree in trees:
        tree_output += tree.pretty_print(0) + '\n'
    tree_output += "Number of trees: {}".format(len(trees))
    print(tree_output)


if __name__ == "__main__":
    # docTEST this
    import doctest
    doctest.testmod()

    # tokens1 = ["Mary", "called", "Jan"]
    # tokens2 = ["Mary", "called", "Jan", "from", "Frankfurt"]
    # print_trees(tokens1, grammar = grammar_from_file('../test/parse/grammar.txt'), permutations=True)
    # print_trees(tokens2, grammar = grammar_from_file('../test/parse/grammar.txt'), permutations=True)
    #
    tokens = "ich sehe".split()
    print_trees(tokens, grammar=bindings_performance_grammar(tokens), permutations=True)