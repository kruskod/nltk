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

from yaep.parse.earley import State, FeatStructNonTerm


class Node:

    def __init__(self, sybmbol, i=None, j=None):
        self._symbol = sybmbol
        self._i = i
        self._j = j
        self._children = []
        self._wordsmap = {}

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

    def children(self):
        return self._children

    def wordsmap(self):
        return self._wordsmap

    def last_child_to_index(self):
        if not self._children:
            return None
        return self._children[-1].to_index()

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
        for i,chart in enumerate(charts,0):
            for state in chart.states():
                if state.is_finished():
                    temp = Node(state.rule().lhs(), state.from_index(), i)
                    val = self._completed.setdefault(temp, default=[])
                    val.append(ExtendedState(state, i))

        return None

class ParseTreeGenerator(AbstractParseTreeGenerator):

    def buildTrees(self, state, parent_states):
        root = Node(state.rule().lhs(), state.from_index(), state.to_index())

        for i,cs in enumerate(state.rule().rhs(), 0):
            if isinstance(cs, FeatStructNonTerm):
                temp = Node(cs)

                if i == (len(state.rule().lhs()) - 1):
                    temp.set_to_index(state.to_index())

                if i == 0:
                    temp.set_from_index(state.from_index())






