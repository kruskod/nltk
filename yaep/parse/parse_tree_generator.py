from functools import reduce
from collections import Counter

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

from yaep.parse.earley import State, FeatStructNonTerm, nonterminal_to_term, Grammar, Rule, EarleyParser, NonTerm
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
            return self._i == other._i and self._symbol == other._symbol

    def __hash__(self):
        return hash((type(self), self._i, self._symbol))

    def __str__(self):
        return self._symbol

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
        return "{}([{}:{}] {} {})".format(padding, self._i, self._j, self._symbol, children_str if self._children else '')

    def __str__(self):
        return "[{}:{}] {}".format(self._i, self._j, self._symbol)


class ExtendedState(State):

    def __init__(self, state, j):
        State.__init__(self, state.rule(), state.from_index(), state.dot())
        self._j = j

    def to_index(self):
        return self._j

    def __str__(self):
        return "[{}:{}] {} -> {}".format(self._i, self._j, unicode_repr(self._rule.lhs()), " ".join(unicode_repr(el) for el in self._rule.rhs()))

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

        return reduce(lambda x,y: x+y, (self.buildTrees(ExtendedState(st, len(chart_manager.charts()) - 1), set()) for st in chart_manager.final_states()))

class ParseTreeGenerator(AbstractParseTreeGenerator):

    def buildTrees(self, state, parent_states):
        root = Node(state.rule().lhs(), state.from_index(), state.to_index())
        result = [root,]
        new_result = []
        parent_states.add(state)

        for i,cs in enumerate(state.rule().rhs(), 0):
            if isinstance(cs, (FeatStructNonTerm, NonTerm)):
                temp = Node(cs)

                if i == (len(state.rule()) - 1):
                    temp.set_to_index(state.to_index())

                different_last_node_index = False

                if i == 0:
                    temp.set_from_index(state.from_index())
                else:
                    result_iter = iter(result)
                    last_node_index = next(result_iter).last_child_to_index()
                    for tempRoot in result_iter:
                        if last_node_index != tempRoot.last_child_to_index():
                            different_last_node_index = True
                            break
                    else:
                        temp.set_from_index(last_node_index)

                # Generate alternatives

                if not different_last_node_index:
                    states = self._completed.get(temp, None)
                    if states:
                        children_lists = (self.buildTrees(st, set(parent_states)) for st in states if (st not in parent_states) and (
                            temp.from_index() == None or st.from_index() == temp.from_index()) and (
                                              temp.to_index() == None or temp.to_index() == st.to_index()))
                        children_list = reduce(lambda x,y: x+y, children_lists)
                        for tempRoot in result:
                            for child in children_list:
                                new_result.append(Node.from_Node_and_child(tempRoot, child))
                else:
                    for tempRoot in result:
                        temp.set_from_index(tempRoot.last_child_to_index())
                        states = self._completed.get(temp, None)
                        if states:
                            children_lists = (self.buildTrees(st, set(parent_states)) for st in states if
                                              (st not in parent_states) and (
                                                  temp.from_index() == None or st.from_index() == temp.from_index()) and (
                                                  temp.to_index() == None or temp.to_index() == st.to_index()))
                            children_list = reduce(lambda x, y: x + y, children_lists)
                            for child in children_list:
                                new_result.append(Node.from_Node_and_child(tempRoot, child))
            else: # if isinstance Leaf
                for tempRoot in result:
                    new_result.append(Node.from_Node_and_child(tempRoot, LeafNode(cs, state.from_index(), state.to_index())))

            result.clear()
            if new_result:
                result.extend(new_result)
                new_result.clear()
            else:
                return result
        return result

if __name__ == "__main__":
    # docTEST this
    import doctest
    doctest.testmod()

        # Perform set up actions (if any)
    tokens1 = ["Mary", "called", "Jan"]
    tokens2 = ["Mary", "called", "Jan", "from", "Frankfurt"]
    grammar = None
    with open("../test/parse/grammar.txt") as f:
        grammar = CFG.fromstring(f.readlines())

    start_nonterminal = nonterminal_to_term(grammar.start())

    earley_grammar = Grammar((Rule(nonterminal_to_term(production.lhs()),
                                   (nonterminal_to_term(fs) for fs in production.rhs())) for production
                              in grammar.productions()), None)
    parser = EarleyParser(earley_grammar)
    chartManager = parser.parse(tokens1, start_nonterminal)

    print(chartManager.pretty_print(" ".join(tokens1)))
    print("Final states:")
    final_states = tuple(chartManager.final_states())
    if final_states:
        for state in final_states:
            print(state.str(len(chartManager.charts()) - 1))

    tree_generator = ParseTreeGenerator()
    trees = tree_generator.parseTrees(chartManager)
    tree_output = ''
    for tree in trees:
        tree_output += tree.pretty_print(0) + '\n'
    tree_output += "Number of trees: {}".format(len(trees))
    print(tree_output)
