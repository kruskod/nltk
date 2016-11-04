from copy import copy
from functools import reduce
from collections import Counter

import itertools

from nltk import CFG
from nltk import featstruct
from nltk.compat import unicode_repr
from nltk.grammar import FeatStructNonterminal, Production, FeatureGrammar, Nonterminal
from nltk.featstruct import CelexFeatStructReader, TYPE, unify
from nltk.topology.compassFeat import PRODUCTION_ID_FEATURE, BRANCH_FEATURE
from nltk.topology.orderedSet import OrderedSet
from nltk.topology.pgsql import build_rules
from timeit import default_timer as timer
import sys

from yaep.parse.earley import State, FeatStructNonTerm, nonterminal_to_term, Grammar, Rule, EarleyParser, NonTerm, \
    pase_tokens, PermutationEarleyParser, grammar_from_file, performance_grammar, Chart, Term
from abc import ABCMeta, abstractmethod

class LeafNode:

    def __init__(self, sybmbol, i=None, j=None):
        self._symbol = sybmbol
        self._i = i
        self._j = j

    def symbol(self):
        return self._symbol

    def set_from_index(self, i):
        self._i = i

    def from_index(self):
        return self._i

    def to_index(self):
        return self._j

    def set_to_index(self, j):
        self._j = j

    def __ne__(self, other):
        return not self.__eq__(other)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        elif self is other:
            return True
        else:
            return self._i == other._i and self._symbol.unify(other._symbol)

    def __hash__(self):
        return hash((type(self), self._i, self._symbol.key()))

    def __str__(self):
        return self._symbol

    def __repr__(self):
        return str(self)

    def pretty_print(self, level):
        return self._symbol

class Node(LeafNode):

    def __init__(self, sybmbol, i=None, j=None):
        super().__init__(sybmbol, i=i, j=j)
        self._children = []
        self._wordsmap = Counter()

    @classmethod
    def from_Node(cls, node):
        new_node = cls(node.symbol(), node.from_index(), node.to_index())
        new_node._children.extend(node.children())
        new_node._wordsmap.update(node.wordsmap())
        return new_node

    @classmethod
    def from_Node_and_child(cls, node,child):
        new_node = cls.from_Node(node)
        new_node.add_node(child)
        return new_node

    @classmethod
    def from_Node_and_children(cls, node, children):
        new_node = cls.from_Node(node)
        for child in children:
            new_node.add_node(child)
        return new_node

    def add_node(self, node):
        if isinstance(node, Node):
            self._wordsmap.update(node._wordsmap)
        else:
            self._wordsmap[node.symbol()] = 1
        self._children.append(node)

    def children(self):
        return self._children

    def wordsmap(self):
        return self._wordsmap

    def last_child_to_index(self):
        if not self._children:
            return None
        return self._children[-1].to_index()

    def pretty_print(self, level):
        padding = '\n' + '\t' * level
        children_str = " ".join(c.pretty_print(level + 1) for c in self._children)
        out = "{}([{}:{}] {} {})".format(padding, self._i, self._j, unicode_repr(self._symbol), children_str if self._children else '')
        if level == 0:
            out += '\n' + str(self._wordsmap)
        return out

    def validate_by_input(self, input_map):
        for key,val in self._wordsmap.items():
            if input_map[key] < val:
                return False
        return True

    def __str__(self):
        return "[{}:{}] {}".format(self._i, self._j, unicode_repr(self._symbol))


class ExtendedState(State):

    def __init__(self, state, j):
        State.__init__(self, state.rule(), state.from_index(), state.dot())
        self._j = j

    def to_index(self):
        return self._j

    def __str__(self):
        return "[{}:{}] {} -> {}".format(self._i, self._j, unicode_repr(self._rule.lhs()), " ".join(unicode_repr(el) for el in self._rule.rhs()))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        elif self is other:
            return True
        else:
            return self._i == other._i and self._j == other._j and self._dot == other._dot and self._rule == other._rule

    def __hash__(self):
        return hash((type(self), self._i, self._j, self._dot, self._rule))

class AbstractParseTreeGenerator:

    def __init__(self):
        self._completed = {}

    def parseTrees(self, chart_manager):
        charts = chart_manager.charts()
        for i, chart in enumerate(charts,0):
            for state in chart.states():
                if state.is_finished():
                    temp = Node(state.rule().lhs(), state.from_index(), i)
                    val = self._completed.setdefault(temp, list())
                    val.append(ExtendedState(state, i))

        return itertools.chain.from_iterable(
                    self.buildTrees(ExtendedState(st, len(chart_manager.charts()) - 1), set()) for st in
                    chart_manager.final_states())

class ParseTreeGenerator(AbstractParseTreeGenerator):

    def buildTrees(self, state, parent_states):
        root = Node(state.rule().lhs(), state.from_index(), state.to_index())
        result = [root,]
        new_result = []
        parent_states.add(state)

        for i,cs in enumerate(state.rule().rhs(), 0):
            if isinstance(cs, (FeatStructNonTerm, NonTerm)):
                type = cs.term().get(TYPE)
                to_index = None
                from_index = None

                if i == (len(state.rule()) - 1):
                    to_index = state.to_index()

                if i == 0:
                    from_index = state.from_index()

                # Generate alternatives
                for tempRoot in result:
                    if from_index is None:
                        local_from_index = tempRoot.last_child_to_index()
                    else:
                        local_from_index = from_index
                    #
                    # if local_from_index is None:
                    #     print("No from index")

                    states = tuple(st for st in self._completed.get(hash((type, local_from_index)), tuple()) if
                                   st.from_index() == local_from_index
                                   and st.to_index() <= state.to_index()
                                   and (to_index is None or to_index == st.to_index())
                                   and st not in parent_states
                                   and cs.unify(st.rule().lhs()))
                    if states:
                        children_list = itertools.chain.from_iterable(
                            self.buildTrees(st, set(parent_states)) for st in states)
                        for child in children_list:
                            new_result.append(Node.from_Node_and_child(tempRoot, child))
            else: # if isinstance Leaf
                for tempRoot in result:
                    new_result.append(Node.from_Node_and_child(tempRoot, LeafNode(cs, state.from_index(), state.to_index())))

            if new_result:
                result.clear()
                result.extend(new_result)
                new_result.clear()

        return result

class ChartTraverseParseTreeGenerator():

    def parseTrees(self, chart_manager):
        parser_charts = chart_manager.charts()
        self._charts = tuple(Chart() for i in range(len(parser_charts)))
        for i, chart in enumerate(parser_charts,0):
            filtered_chart = self._charts[i]
            for state in chart.states():
                if state.is_finished():
                    filtered_chart.add_state(ExtendedState(state, i))
        j = len(chart_manager.tokens())
        result = tuple(itertools.chain.from_iterable(self.countDown(ExtendedState(st, j), set(), j) for st in chart_manager.final_states()))
        return result

    def find_state(self, non_terminal, states):
        for st in states:
            lhs = st.rule().lhs()
            if lhs.key() == non_terminal.key() and non_terminal.unify(lhs):
                yield st

    def countDown(self, state, parent_states, start):
        parent_states.add(state)
        root = Node(state.rule().lhs(), state.from_index(), state.to_index())
        result = []
        old_result = []
        reversed_rhs = tuple(reversed(state.rule().rhs()))
        start_index = start
        for cs in reversed_rhs:
            if result:
                old_result = list(result)
                result.clear()
            else:
                result.extend((node,) for node in self.find_node(cs, set(parent_states), start_index))

            for node_rhs in old_result:
                node = node_rhs[0]
                start_index = node.from_index()
                result.extend((n,) + node_rhs for n in self.find_node(cs, set(parent_states), start_index))

        for children in result:
            yield Node.from_Node_and_children(root, children)

    def find_node(self, term, parent_states, start_index):
        if isinstance(term, Term):
            for st in self.find_state(term, reversed(self._charts[start_index].states())):
                if st not in parent_states:
                    yield from self.countDown(st, set(parent_states), start_index)
        else:
            # it is a terminal
            # current = Node(state.rule().lhs(), state.from_index(), state.to_index())
            yield LeafNode(term, start_index - 1, start_index)

class PermutationParseTreeGenerator(AbstractParseTreeGenerator):

    def __init__(self, words_map):
        super().__init__()
        self._words_map = words_map

    def buildTrees(self, state, parent_states):
        root = Node(state.rule().lhs(), state.from_index(), state.to_index())
        result = [root,]
        new_result = []
        parent_states.add(state)

        for i,cs in enumerate(state.rule().rhs(), 0):
            if isinstance(cs, (FeatStructNonTerm, NonTerm)):
                type = cs.term().get(TYPE)
                to_index = None
                from_index = None

                if i == (len(state.rule()) - 1):
                    to_index = state.to_index()

                if i == 0:
                    from_index = state.from_index()

                # Generate alternatives
                for tempRoot in result:
                    if from_index is None:
                        local_from_index = tempRoot.last_child_to_index()
                    else:
                        local_from_index = from_index

                    if local_from_index is None:
                        print("No from index")

                    states = tuple(st for st in self._completed.get(hash((type, local_from_index)), tuple()) if
                                   st.from_index() == local_from_index
                                   and st.to_index() <= state.to_index()
                                   and (to_index is None or to_index == st.to_index())
                                   and st not in parent_states
                                   and cs.unify(st.rule().lhs()))
                    if states:
                        children_list = itertools.chain.from_iterable(self.buildTrees(st, set(parent_states)) for st in states)
                        for child in children_list:
                            test_node = Node.from_Node_and_child(tempRoot, child)
                            if test_node.validate_by_input(self._words_map):
                                new_result.append(test_node)

            else: # if isinstance Leaf
                for tempRoot in result:
                    new_result.append(Node.from_Node_and_child(tempRoot, LeafNode(cs, state.from_index(), state.to_index())))

            if new_result:
                result.clear()
                result.extend(new_result)
                new_result.clear()
            #else:
                # do nothing, because there are nullable non-terminals
                #return result
        return result

def print_trees(tokens, grammar, permutations = False):
    parser = PermutationEarleyParser(grammar) if permutations else EarleyParser(grammar)
    chart_manager = parser.parse(tokens, grammar.start())
    print()
    print(chart_manager)
    print(chart_manager.out())

    tree_generator = parser.build_tree_generator()
    number_trees = 0
    for tree in tree_generator.parseTrees(chart_manager):
        print(tree.pretty_print(0))
        number_trees += 1
    print("Number of trees: {}".format(number_trees))

if __name__ == "__main__":
    # docTEST this
    import doctest
    doctest.testmod()

    tokens1 = ["Mary", "called", "Jan"]
    tokens2 = ["Mary", "called", "Jan", "from", "Frankfurt"]
    print_trees(tokens2, grammar = grammar_from_file('../test/parse/grammar.txt'), permutations=False)
    # print_trees(tokens2, grammar = grammar_from_file('../test/parse/grammar.txt'), permutations=True)
    #
    # tokens = "ich sehe".split()
    # print_trees(tokens, grammar=performance_grammar(tokens), permutations=True)
