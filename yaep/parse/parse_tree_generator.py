import itertools
from collections import Counter

from nltk.compat import unicode_repr
from nltk.featstruct import TYPE
from yaep.parse.earley import State, EarleyParser, PermutationEarleyParser, grammar_from_file, Chart, Term, test_unify, \
    FeatStructNonTerm, ChartManager


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

    # functions for the tree presentation

    def label(self):
        return self._symbol
    #
    # def has_consistent_children(self):
    #     return False

class Node(LeafNode):

    def __init__(self, sybmbol, i=None, j=None, init_collections=True):
        super().__init__(sybmbol, i=i, j=j)
        if init_collections:
            self._children = []
            self._wordsmap = Counter()

    @classmethod
    def from_Node(cls, node):
        new_node = cls(node.symbol(), node.from_index(), node.to_index(), init_collections=False)
        new_node._children = list(node._children)
        new_node._wordsmap = Counter(node._wordsmap)
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
            self._wordsmap[node._symbol] = 1
        self._children.append(node)

    def children(self):
        return self._children

    def wordsmap(self):
        return self._wordsmap

    def last_child_to_index(self):
        if not self._children:
            return None
        return self._children[-1]._j

    def pretty_print(self, level, print_counter=False):
        padding = '\n' + '\t' * level
        children_str = " ".join(c.pretty_print(level + 1) for c in self._children)
        out = "{}([{}:{}] {} {})".format(padding, self._i, self._j, unicode_repr(self._symbol), children_str if self._children else '')
        if print_counter:
            out += '\n' + str(self._wordsmap)
        return out

    def validate_by_input(self, input_map):
        for key,val in self._wordsmap.items():
            if input_map[key] < val:
                return False
        return True

    def has_consistent_children(self):
        if self._wordsmap:
            return sum(self._wordsmap.values()) == (self._j - self._i)
        return False

    def __str__(self):
        return "[{}:{}] {}".format(self._i, self._j, unicode_repr(self._symbol))

    # functions for the tree presentation

    def leaves(self):
        return self._wordsmap

    def label(self):
        return self._symbol._term

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

class EllipsisNode(Node):

    @classmethod
    def from_Node_and_children(cls, node, children):
        new_node = cls.from_Node(node)
        for child in children:
            new_node.add_node(child)
        return new_node


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

class EllipsisState(ExtendedState):

    def __init__(self, origin_state, tree_generator, token_index=None, j=None):
        State.__init__(self, origin_state.rule(), token_index, origin_state.dot())
        self._j = j
        self._origin_state = origin_state
        self._tree_generator = tree_generator
        # self._requested_state = requested_state

    # def __hash__(self):
    #     return hash((type(self), self._i, self._j, self._dot, self._rule, self._requested_state))

class EllipsisEarleyParser(EarleyParser):

    def build_tree_generator(self, chart_manager):
        return EllipsisParseTreeGenerator(chart_manager)

    def set_sibling_conjunct_chart_manager(self, sibling_conjunct_chart_manager):
        charts = sibling_conjunct_chart_manager.charts()
        non_ellipses_charts = tuple(Chart() for i in range(len(charts)))
        for index, chart in enumerate(charts):
            for state in chart.states():
                if not isinstance(state, EllipsisState):
                    non_ellipses_charts[index].add_state(state)
        self._tree_generator = self.build_tree_generator(ChartManager(non_ellipses_charts, sibling_conjunct_chart_manager.start_symbol(), sibling_conjunct_chart_manager.tokens()))

    def predictor(self, state, token_index):
        lhs = state.next_symbol()
        self.predictor_non_terminal(lhs, token_index)
        chart = self._charts[token_index]
        if lhs.is_nullable():
            chart.add_state(State(state.rule(), state.from_index(), state.dot() + 1))
        # iff state.lhs is S we look for the ellipses
        # find in the dependent chart manager, iff this rule was completed in an other conjunct, add that
        # completed rule to the current chart
        state_lhs = state.rule().lhs()
        if 'S' != lhs.key() and 'S' == state_lhs.key():
            for finished_state in self._tree_generator.finished_states():
                finished_state_lhs = finished_state.rule().lhs()
                # gapping need lemma identity (and to be precise contrastiveness too) =>
                if lhs.key() == finished_state_lhs.key():
                    finished_state_lhs_gapping = finished_state_lhs.term().filter_feature('number', 'person')
                    if lhs.test_unify(FeatStructNonTerm(finished_state_lhs_gapping)):
                        ellipsis_state = EllipsisState(finished_state, self._tree_generator, token_index=token_index)
                        chart.remove_state_if_present(ellipsis_state)
                        chart.add_state(ellipsis_state)

    # def scanner(self, state, token_index):
    #     if self._tokens[token_index] == state.next_symbol():
    #         self._charts[token_index + 1].add_state(State(state.rule(), state.from_index(), state.dot() + 1))
    #     else:
    #         # find in the dependent chart manager, iff this rule was completed in an other conjunct, add that
    #         # completed rule to the current chart
    #         if self._chart_manager:
    #             state_lhs = state.rule().lhs()
    #             for finished_state in self._chart_manager.finished_states():
    #                 lhs = finished_state.rule().lhs()
    #                 # gapping need lemma identity (and to be precise contrastiveness too) =>
    #                 if lhs.key() == state_lhs.key():
    #                     lhs_gapping = lhs.term().filter_feature('number', 'person')
    #                     if state_lhs.test_unify(FeatStructNonTerm(lhs_gapping)):
    #                         self._charts[token_index].add_state(EllipsisState(finished_state.rule(), finished_state.from_index(), finished_state.dot(), self._chart_manager))

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
            if isinstance(cs, Term):
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

                    states = (st for st in self._completed.get(hash((type, local_from_index)), tuple()) if
                                   st.from_index() == local_from_index
                                   and (to_index == st.to_index() or (to_index is None and st.to_index() <= state.to_index()))
                                   and st not in parent_states
                                   and test_unify(cs.term(), st.rule().lhs().term())) #  cs.unify(st.rule().lhs())

                    for child in itertools.chain.from_iterable(self.buildTrees(st, set(parent_states)) for st in states):
                        new_result.append(Node.from_Node_and_child(tempRoot, child))
                if not cs.is_nullable():
                    result.clear()

            else: # if isinstance Leaf
                for tempRoot in result:
                    new_result.append(Node.from_Node_and_child(tempRoot, LeafNode(cs, state.from_index(), state.to_index())))
                result.clear()

            if new_result:
                # This condition was replaced because of optimization reasons by two result.clear() above
                # if not isinstance(cs, Term) or not cs.is_nullable():
                #     result.clear()
                result.extend(new_result)
                new_result.clear()

        return (node for node in result if node.has_consistent_children())

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
            if isinstance(cs, Term):
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

                    states = (st for st in self._completed.get(hash((type, local_from_index)), tuple()) if
                                    st.from_index() == local_from_index
                                    and (to_index == st.to_index() or (to_index is None and st.to_index() <= state.to_index()))
                                    and st not in parent_states
                                    and test_unify(cs.term(), st.rule().lhs().term())) #cs.unify()

                    for child in itertools.chain.from_iterable(self.buildTrees(st, set(parent_states)) for st in states):
                        test_node = Node.from_Node_and_child(tempRoot, child)
                        if test_node.validate_by_input(self._words_map):
                            new_result.append(test_node)
                if not cs.is_nullable():
                    result.clear()

            else: # if isinstance Leaf
                for tempRoot in result:
                    new_result.append(Node.from_Node_and_child(tempRoot, LeafNode(cs, state.from_index(), state.to_index())))
                # clear result, because we must add new leaves anyway
                result.clear()

            if new_result:
                # This condition was replaced because of optimization reasons by two result.clear() above
                # if not isinstance(cs, Term) or not cs.is_nullable():
                #     result.clear()

                result.extend(new_result)
                new_result.clear()

        return (node for node in result if node.has_consistent_children())


class ChartTraverseParseTreeGenerator:

    def __init__(self, chart_manager):
        parser_charts = chart_manager.charts()
        self._charts = tuple(Chart() for i in range(len(parser_charts)))
        self._tokens_number = len(chart_manager.tokens())
        for i, chart in enumerate(parser_charts, 0):
            for state in chart.states():
                if state.is_finished():
                    self._charts[i].add_state(ExtendedState(state, i))

    def parseTrees(self, chart_manager):
        return itertools.chain.from_iterable(self.countdown(ExtendedState(st, self._tokens_number), set(), self._tokens_number) for st in chart_manager.final_states())

    def parseState(self, state):
        yield from self.countdown(state, set(), state.to_index())

    def find_state(self, non_terminal, states):
        for st in states:
            lhs = st.rule().lhs()
            if lhs.key() == non_terminal.key() and non_terminal.unify(lhs):
                yield st

    def countdown(self, state, parent_states, start):
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
                    yield from self.countdown(st, set(parent_states), start_index)
        else:
            # it is a terminal
            # current = Node(state.rule().lhs(), state.from_index(), state.to_index())
            yield LeafNode(term, start_index - 1, start_index)


class EllipsisParseTreeGenerator(ChartTraverseParseTreeGenerator):

    def __init__(self, chart_manager):
        self._tokens_number = len(chart_manager.tokens())
        parser_charts = chart_manager.charts()
        self._charts = tuple(Chart() for i in range(len(parser_charts)))
        for i, chart in enumerate(parser_charts, 0):
            for state in chart.states():
                if state.is_finished():
                    if isinstance(state, EllipsisState):
                        state._j = i
                        self._charts[i].add_state(state)
                    else:
                        self._charts[i].add_state(ExtendedState(state, i))

    def finished_states(self):
        for index, chart in enumerate(self._charts):
            for state in chart.states():
                yield ExtendedState(state, index)


    def countdown(self, state, parent_states, start_index):
        parent_states.add(state)

        result = []
        old_result = []
        reversed_rhs = tuple(reversed(state.rule().rhs()))
        is_ellipsis_state = isinstance(state, EllipsisState)
        root = Node(state.rule().lhs(), state.from_index(), state.to_index())
        if is_ellipsis_state:
            root = EllipsisNode.from_Node(root)

        for cs in reversed_rhs:
            if result:
                old_result = list(result)
                result.clear()
            else:
                if is_ellipsis_state:
                    ellipse_start_index = state._origin_state.to_index()
                    result.extend((EllipsisNode.from_Node(node),) if isinstance(node, Node) else (node,) for node in state._tree_generator.find_node(cs, set(parent_states), ellipse_start_index))
                else:
                    result.extend((node,) for node in self.find_node(cs, set(parent_states), start_index))

            for node_rhs in old_result:
                alternative_start_index = node_rhs[0].from_index()
                if is_ellipsis_state:
                    ellipse_start_index = state._origin_state.to_index()
                    result.extend(((EllipsisNode.from_Node(node),) if isinstance(node, Node) else (node,)) + node_rhs for node in state._tree_generator.find_node(cs, set(parent_states), alternative_start_index))
                else:
                    result.extend((node,) + node_rhs for node in self.find_node(cs, set(parent_states), alternative_start_index))
        for children in result:
            yield root.from_Node_and_children(root, children)

    # def find_nonellipsis_node(self, term, parent_states, start_index):
    #     if isinstance(term, Term):
    #         for st in self.find_state(term, reversed(tuple(state for state in self._charts[start_index].states() if not isinstance(state, EllipsisState)))):
    #             if st not in parent_states and not isinstance(st, EllipsisState):
    #                 yield from self.countdown(st, set(parent_states), start_index)
    #     else:
    #         # it is a terminal
    #         # current = Node(state.rule().lhs(), state.from_index(), state.to_index())
    #         yield LeafNode(term, start_index - 1, start_index)


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
