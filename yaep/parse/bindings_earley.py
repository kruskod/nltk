# -*- coding: utf-8 -*-
import itertools
import multiprocessing
import pickle
from collections import Counter

import pathos as pathos
from timeit import default_timer

from nltk import Variable
from nltk.compat import unicode_repr
from nltk.draw.tree import TreeTabView
from nltk.featstruct import CelexFeatStructReader, substitute_bindings, TYPE
from nltk.grammar import FeatStructNonterminal
from nltk.topology.pgsql import build_rules
from yaep.parse.earley import State, Grammar, Rule, EarleyParser, AbstractEarley, Chart, \
    feat_struct_nonterminal_to_term, is_nonterminal, FeatStructNonTerm
from yaep.parse.parse_tree_generator import PermutationParseTreeGenerator, ExtendedState, \
    ChartTraverseParseTreeGenerator, ParseTreeGenerator

class BindingsRule(Rule):

    def __init__(self, lhs, rhs):
        super().__init__(lhs,rhs)
        self._bindings = {}

    def bindings(self):
        return self._bindings

    @classmethod
    def from_Rule(cls, rule, bindings):
        new_node = cls(rule.lhs(), rule.rhs())
        new_node._bindings = bindings
        return new_node

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        elif self is other:
            return True
        else:
            return self._lhs == other._lhs and self._rhs == other._rhs and self._bindings == other._bindings

    def str(self, dot):
        if dot == 0:
            return '{} -> * {}'.format(unicode_repr(substitute_bindings(self._lhs.term(), self._bindings)), " ".join(unicode_repr(el) for el in self._rhs))
        elif dot == len(self):
            return '{} -> {} *'.format(unicode_repr(substitute_bindings(self._lhs.term(), self._bindings)), " ".join(unicode_repr(substitute_bindings(el.term(), self._bindings)) if is_nonterminal(el) else unicode_repr(el) for el in self._rhs))
        elif 0 < dot < len(self):
            # substitute bindings only for non_terminals before dot, because we don't know how the bindings will modify further
            before_dot = " ".join(unicode_repr(substitute_bindings(el.term(), self._bindings)) for el in self._rhs[:dot])
            after_dot = " ".join(unicode_repr(el) for el in self._rhs[dot:])
            return '{} -> {} * {}'.format(unicode_repr(substitute_bindings(self._lhs.term(), self._bindings)), before_dot, after_dot)
        else:
            raise ValueError("dot: {} is not fit for {}".format(dot, self))

    def __str__(self):
        """
        Return a verbose string representation of the ``Rule``.

        :rtype: str
        """
        result = '%s -> ' % unicode_repr(substitute_bindings(self._lhs, self._bindings, fs_class='default'))
        result += " ".join(unicode_repr(substitute_bindings(el, self._bindings, fs_class='default')) for el in self._rhs)
        return result

    def __hash__(self):
        return hash((type(self), self._lhs, self._rhs, frozenset(self._bindings.values())))

class BindingsGrammar(Grammar):

    def find_rule(self, non_terminal, bindings=None):
        if bindings is None:
            _bindings = {}
        else:
            _bindings = bindings.copy()
        rules = self._rules.get(non_terminal.key())
        if rules:
            for rule in rules:
                lhs = rule.lhs()
                result = non_terminal.unify(lhs, _bindings)
                if result:
                    extracted_bindings = extract_bindings(lhs.term(), result)
                    yield BindingsRule.from_Rule(rule,extracted_bindings)

class BindingsEarleyParser(AbstractEarley):

    def init(self, tokens):
        self._tokens = tokens
        self._charts = tuple(Chart() for i in range(len(tokens) + 1))

    def build_tree_generator(self):
        return BindingsParseTreeGenerator()

    def predictor_non_terminal(self, lhs, token_index, bindings=None):
        for rule in self._grammar.find_rule(lhs, bindings):
            self._charts[token_index].add_state(State(rule, token_index, 0))

    def predictor(self, state, token_index):
        lhs = state.next_symbol()
        self.predictor_non_terminal(lhs, token_index, state.rule().bindings())
        if lhs.is_nullable():
            self._charts[token_index].add_state(State(state.rule(), state.from_index(), state.dot() + 1))

    def scanner(self, state, token_index):
        if self._tokens[token_index] == state.next_symbol():
            self._charts[token_index + 1].add_state(State(state.rule(), state.from_index(), state.dot() + 1))

    def completer(self, origin_state, token_index):
        origin_rule = origin_state.rule()
        lhs = origin_rule.lhs()
        current_chart = self._charts[token_index]
        for temp_state in self._charts[origin_state.from_index()].states():
            if (not temp_state.is_finished()) and is_nonterminal(temp_state.next_symbol()):
                common_bindings = dict_intersection(temp_state.rule().bindings(), origin_rule.bindings())
                if common_bindings is None:
                    continue
                result = lhs.unify(temp_state.next_symbol(), common_bindings)
                if result:
                    extracted_bindings = extract_bindings(temp_state.next_symbol().term(), result)
                    rule_bindings = dict_intersection(temp_state.rule().bindings(), extracted_bindings)
                    if rule_bindings is None:
                        raise ValueError(rule_bindings)

                    # extracted_bindings = merge_bindings(temp_state.rule().bindings(), extract_bindings(lhs.term(), result))
                    current_chart.add_state(State(BindingsRule.from_Rule(temp_state.rule(),rule_bindings), temp_state.from_index(), temp_state.dot() + 1))

class BindingsPermutationEarleyParser(AbstractEarley):

    def init(self, tokens):
        self._tokens = tokens
        self._words_map = Counter(tokens)
        self._charts = tuple(Chart() for i in range(len(tokens) + 1))

    def build_tree_generator(self):
        return BindingsPermutationParseTreeGenerator(self._words_map)
        # return BindingsPermutationTraverseParseTreeGenerator()

    def predictor_non_terminal(self, lhs, token_index, bindings=None):
        for rule in self._grammar.find_rule(lhs, bindings):
            self._charts[token_index].add_state(State(rule, token_index, 0))

    def predictor(self, state, token_index):
        lhs = state.next_symbol()
        self.predictor_non_terminal(lhs, token_index, state.rule().bindings())
        if lhs.is_nullable():
            self._charts[token_index].add_state(State(state.rule(), state.from_index(), state.dot() + 1))

    def scanner(self, state, token_index):
        if state.next_symbol() in self._words_map:
            self._charts[token_index + 1].add_state(State(state.rule(), state.from_index(), state.dot() + 1))

    def completer(self, origin_state, token_index):
        origin_rule = origin_state.rule()
        lhs = origin_rule.lhs()
        current_chart = self._charts[token_index]
        for temp_state in self._charts[origin_state.from_index()].states():
            if (not temp_state.is_finished()) and is_nonterminal(temp_state.next_symbol()):
                common_bindings = dict_intersection(temp_state.rule().bindings(), origin_rule.bindings())
                if common_bindings is None:
                    continue
                result = lhs.unify(temp_state.next_symbol(), common_bindings)
                if result:
                    extracted_bindings = extract_bindings(temp_state.next_symbol().term(), result)
                    rule_bindings = dict_intersection(temp_state.rule().bindings(), extracted_bindings)
                    if rule_bindings is None:
                        raise ValueError(rule_bindings)

                    # extracted_bindings = merge_bindings(temp_state.rule().bindings(), extract_bindings(lhs.term(), result))
                    current_chart.add_state(State(BindingsRule.from_Rule(temp_state.rule(),rule_bindings), temp_state.from_index(), temp_state.dot() + 1))

    def words_map(self):
        return self._words_map

def extract_bindings(nt_with_variables, unification_result):
    dict_variables = {key:val for key, val in nt_with_variables.items() if isinstance(val, Variable)}
    if dict_variables:
        dict_unification_result = unification_result.items()
        result = {dict_variables[key]: val for key, val in dict_unification_result if
                          key in dict_variables and not isinstance(val, Variable)}
        return result
    return {}

def dict_intersection(dict1, dict2):
    if not dict1:
        return dict2.copy()
    elif not dict2 or dict1 == dict2:
        return dict1.copy()

    intersection = dict1.keys() & dict2.keys()
    result = dict1.copy()
    if not intersection:
        result.update(dict2)
    else:
        common_dict = {}
        for key in intersection:
            val1 = dict1[key]
            val2 = dict2[key]
            if val1 == val2:
                continue
            elif isinstance(val1, tuple) or isinstance(val2, tuple):
                if isinstance(val1, tuple) and val2 in val1:
                    common_dict[key] = val2
                    continue
                elif isinstance(val2, tuple) and val1 in val2:
                    common_dict[key] = val1
                    continue
                elif isinstance(val1, tuple) and isinstance(val2, tuple):
                    val1_set = set(val1)
                    val2_set = set(val2)
                    if val1_set.issubset(val2_set) or val2_set.issubset(val1_set):
                        common_dict[key] = tuple(val1_set & val2_set)
                        continue
            return None
        result.update(dict2)
        result.update(common_dict)
    return result

class BindingsParseTreeGenerator(ParseTreeGenerator):
    # pass

    def parseTrees(self, chart_manager):
        '''
         In this implementation all NonTerm variables will be replaced by their bindings
        :param chart_manager: recognized chart
        :return: collection of parse trees
        '''

        charts = chart_manager.charts()
        for i, chart in enumerate(charts, 0):
            for state in chart.states():
                if state.is_finished():
                    rule = substitute_rule(state.rule())
                    temp = hash((rule.lhs().term().get(TYPE), state.from_index()))
                    val = self._completed.setdefault(temp, list())
                    val.append(ExtendedState(State(rule, state.from_index(), state.dot()), i))

        # final_state = tuple(chart_manager.final_states())[0]
        # return itertools.chain.from_iterable(self.buildTrees(
        #     ExtendedState(State(substitute_rule(final_state.rule()), final_state.from_index(), final_state.dot()),
        #                   len(chart_manager.charts()) - 1), set()))

        return itertools.chain.from_iterable(self.buildTrees(ExtendedState(State(substitute_rule(st.rule()), st.from_index(), st.dot()), len(chart_manager.charts()) - 1), set()) for st in
                      chart_manager.final_states())


class BindingsPermutationParseTreeGenerator(PermutationParseTreeGenerator):
    # pass

    def parseTrees(self, chart_manager):
        '''
         In this implementation all NonTerm variables will be replaced by their bindings
        :param chart_manager: recognized chart
        :return: collection of parse trees
        '''

        charts = chart_manager.charts()
        for i, chart in enumerate(charts, 0):
            for state in chart.states():
                if state.is_finished():
                    rule = substitute_rule(state.rule())
                    temp = hash((rule.lhs().term().get(TYPE), state.from_index()))
                    val = self._completed.setdefault(temp, list())
                    val.append(ExtendedState(State(rule, state.from_index(), state.dot()), i))

        # final_state = tuple(chart_manager.final_states())[0]
        # return itertools.chain.from_iterable(self.buildTrees(
        #     ExtendedState(State(substitute_rule(final_state.rule()), final_state.from_index(), final_state.dot()),
        #                   len(chart_manager.charts()) - 1), set()))

        return itertools.chain.from_iterable(self.buildTrees(ExtendedState(State(substitute_rule(st.rule()), st.from_index(), st.dot()), len(chart_manager.charts()) - 1), set()) for st in
                      chart_manager.final_states())

class BindingsPermutationTraverseParseTreeGenerator(ChartTraverseParseTreeGenerator):

    def parseTrees(self, chart_manager):
        parser_charts = chart_manager.charts()
        self._charts = tuple(Chart() for i in range(len(parser_charts)))
        for i, chart in enumerate(parser_charts,0):
            filtered_chart = self._charts[i]
            for state in chart.states():
                if state.is_finished():
                    filtered_chart.add_state(ExtendedState(State(substitute_rule(state.rule()), state.from_index(), state.dot()), i))
        j = len(chart_manager.tokens())
        result = tuple(itertools.chain.from_iterable(
            self.countDown(ExtendedState(State(substitute_rule(st.rule()), st.from_index(), st.dot()), j), set(), j) for st in chart_manager.final_states()))
        return result


def substitute_rule(rule):
    bindings = rule.bindings()
    lhs = FeatStructNonTerm(substitute_bindings(rule.lhs().term(), bindings), rule.lhs().is_nullable())
    rhs = (FeatStructNonTerm(substitute_bindings(el.term(), bindings), el.is_nullable()) if is_nonterminal(el) else el for el in rule.rhs())
    return Rule(lhs, rhs)


def bindings_performance_grammar(tokens):
    fstruct_reader = CelexFeatStructReader(fdict_class=FeatStructNonterminal)
    grammar = build_rules(tokens, fstruct_reader)
    productions = grammar.productions()
    start_nonterminal = feat_struct_nonterminal_to_term(grammar.start())

    return BindingsGrammar((Rule(feat_struct_nonterminal_to_term(production.lhs()),
                  (feat_struct_nonterminal_to_term(fs) for fs in production.rhs())) for production in productions),
            None, start_nonterminal)


def print_trees(tokens, grammar, permutations=False):
    parser = BindingsPermutationEarleyParser(grammar) if permutations else EarleyParser(grammar)
    start_time = default_timer()
    chart_manager = parser.parse(tokens, grammar.start())
    print()
    print(chart_manager)
    print(chart_manager.pretty_print_filtered(" ".join(tokens)))
    print(chart_manager.out())

    tree_generator = parser.build_tree_generator()
    trees = tree_generator.parseTrees(chart_manager)
    number_trees = 0
    number_derivation_trees = 0
    dominance_structures=[]
    verifier = Counter(tokens)
    end_time = default_timer()
    if trees:
        tree_output = ''
        for tree in trees:
            number_derivation_trees += 1
            if tree.wordsmap() == verifier:
                number_trees += 1
                dominance_structures.append(tree)
            tree_output += tree.pretty_print(0) + '\n'
        tree_output += "Number of derivation trees: {}".format(number_derivation_trees)
        print(tree_output)
        print("Number of dominance structures: {}".format(number_trees))
        print("Time: {:.3f}s.\n".format(end_time - start_time))
        if dominance_structures:
            with open('../../fsa/dominance_structures.dump', 'wb') as f:
                pickle.dump(dominance_structures, f, pickle.HIGHEST_PROTOCOL)
            TreeTabView(*dominance_structures[:20])


def parse_tokens(tokens, grammar, parser, verifier):
    chart_manager = parser.parse(tokens, grammar.start())

    if next(chart_manager.final_states(), None):
        print("Successful recognition: " + " ".join(tokens))
        # print()
        # print(chart_manager)
        # # print(chart_manager.pretty_print_filtered(" ".join(tokens)))
        # print(chart_manager.out())

        return tuple(tree for tree in parser.build_tree_generator().parseTrees(chart_manager) if
                    verifier == tree.wordsmap())
    return tuple()


class TreeGenerator(object):
    def __init__(self, grammar, parser, verifier):
        self._grammar = grammar
        self._parser = parser
        self._verifier = verifier

    def __call__(self, tokens):
        return parse_tokens(tokens, self._grammar, self._parser, self._verifier)


def permutation_parse_trees_builder(tokens, grammar, parser):
    verifier = Counter(tokens)
    pool = pathos.multiprocessing.Pool(multiprocessing.cpu_count())
    return itertools.chain(*pool.map(lambda t: parse_tokens(t, grammar, parser, verifier), itertools.permutations(tokens)))


def print_nw_trees(tokens, grammar, permutations=False):
    parser = BindingsEarleyParser(grammar) if permutations else EarleyParser(grammar)
    start_time = default_timer()
    dominance_structures = tuple(permutation_parse_trees_builder(tokens, grammar, parser))
    end_time = default_timer()
    number_trees = 0
    tree_output = ''
    if dominance_structures:
        for tree in dominance_structures:
            number_trees += 1
            tree_output += tree.pretty_print(0) + '\n'

        print(tree_output)
        print("Number of dominance structures: {}".format(number_trees))
        print("Time: {:.3f}s.\n".format(end_time - start_time))
        # with open('../../fsa/dominance_structures.dump', 'wb') as f:
        #     pickle.dump(dominance_structures, f, pickle.HIGHEST_PROTOCOL)
        # TreeTabView(*dominance_structures[:20])

if __name__ == "__main__":
    # docTEST this
    import doctest
    doctest.testmod()

    # tokens1 = ["Mary", "called", "Jan"]
    # tokens2 = ["Mary", "called", "Jan", "from", "Frankfurt"]
    # print_trees(tokens1, grammar = grammar_from_file('../test/parse/grammar.txt'), permutations=True)
    # print_trees(tokens2, grammar = grammar_from_file('../test/parse/grammar.txt'), permutations=True)
    #
    # tokens = "Monopole sollen geknackt werden und Märkte getrennt werden".split()
    # tokens = "ich darf Kaffee trinken".split()
    # tokens = "meine Frau will ein Auto kaufen".split()
    # tokens = "ich sehe den Mann mit dem Hund in dem Wald".split()
    # tokens = "ich sehe den Mann mit dem Hund".split()
    tokens = "ich gebe ihr".split()
    # tokens = "ich sehe den Mann mit dem Hund".split()

    # print_nw_trees(tokens, grammar=bindings_performance_grammar(tokens), permutations=True)
    print_trees(tokens, grammar=bindings_performance_grammar(tokens), permutations=True)