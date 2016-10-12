from nltk import CFG
from nltk import featstruct
from nltk.compat import unicode_repr
from nltk.grammar import FeatStructNonterminal, Production, FeatureGrammar, is_nonterminal, is_terminal
from nltk.featstruct import CelexFeatStructReader, TYPE, unify
from nltk.topology.compassFeat import PRODUCTION_ID_FEATURE, BRANCH_FEATURE
from nltk.topology.orderedSet import OrderedSet
from nltk.topology.pgsql import build_rules
from timeit import default_timer as timer
import sys

class Rule:
    """
    Base container for CFG rules

    >>> production = CFG.fromstring("S -> A 'b'").productions()[0]
    >>> rule = Rule(production.lhs(), production.rhs())
    >>> str(rule)
    "S -> A 'b'"
    """

    def __init__(self, lhs, rhs):
        self._lhs = lhs
        self._rhs = tuple(rhs)
        self._hash = hash((type(self), self._lhs, self._rhs))

    def __len__(self):
        """
        Return the length of the right-hand side.
        :rtype: int
        """
        return len(self._rhs)

    def lhs(self):
        return self._lhs

    def rhs(self):
        return self._rhs

    def is_terminal(self, index):
        return is_terminal(self._rhs[index])

    def is_nonterminal(self, index):
        return is_nonterminal(self._rhs[index])

    def get_symbol(self, index):
        return self._rhs[index]

    def __str__(self):
        """
        Return a verbose string representation of the ``Rule``.

        :rtype: str
        """
        result = '%s -> ' % unicode_repr(self._lhs)
        result += " ".join(unicode_repr(el) for el in self._rhs)
        return result

    def __ne__(self, other):
        return not self.__eq__(other)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        elif self is other:
            return True
        else:
            return self._lhs == other._lhs and self._rhs == other._rhs

    def __hash__(self):
        return self._hash

class State:

    def __init__(self, rule, i , dot):
        self._rule = rule
        self._i = i
        self._dot = dot

    def is_next_symbol_nonterminal(self):
        return self._rule.is_nonterminal(self._dot)

    def next_symbol(self):
        return self._rule.get_symbol(self._dot)

    def is_finished(self):
        return len(self._rule) == self._dot

    def rule(self):
        return self._rule

    def dot(self):
        return self._dot

    def from_index(self):
        return self._i

    def __str__(self):
        return self.str('..')

    def str(self, j):
        rhs = self._rule.rhs()
        before_dot = " ".join(unicode_repr(el) for el in rhs[:self._dot])
        after_dot = " ".join(unicode_repr(el) for el in rhs[self._dot:])
        rhs_with_dot = before_dot + " * " + after_dot
        return "[{}:{}] {} -> {}".format(self._i, j,  unicode_repr(self._rule.lhs()), rhs_with_dot)

    def __repr__(self):
        return self.__str__()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        elif self is other:
            return True
        else:
            return self._i == other._i and self._dot == other._dot and self._rule == other._rule

    def __hash__(self):
        return hash((type(self), self._i, self._dot, self._rule))

class Chart:

    def __init__(self):
        self._states = OrderedSet()

    def add_state(self, state):
        # if state not in self._states:
        self._states.add(state)

    def get_state(self, i):
        return self._states[i]

    def states(self):
        return self._states

    def __len__(self):
        return len(self._states)

    def __str__(self):
        return self.str('..')

    def str(self, j):
        out = ""
        for state  in self._states:
            out += state.str(j) + '\n'
        return out

class ChartManager:

    def __init__(self, charts, start_symbol, tokens):
        self._charts = tuple(charts)
        self._start_symbol = start_symbol
        self._tokens = tokens

    def initial_states(self):
        if self._charts and self._start_symbol:
            return (state for state in self._charts[0].states() if state.dot() == 0 and state.from_index() == 0 and featstruct.unify(self._start_symbol, state.rule().lhs(), treatBool = False))

    def final_states(self):
        if self._charts and (len(self._charts) == len(self._tokens) + 1) and self._start_symbol:
            return (state for state in self._charts[-1].states() if state.from_index() == 0 and state.is_finished() and featstruct.unify(self._start_symbol, state.rule().lhs(), treatBool = False))

    def is_recognized(self):
        return next(self.final_states(), None) is not None

    def charts(self):
        return self._charts

    def pretty_print(self, input):
        out = "Charts produced by the sentence: " + input + "\n"
        for i,chart in enumerate(self._charts, 0):
            out += "Chart {index}:\n{chart}\n".format_map({'index':i, 'chart':chart.str(i)})
        return out

class Grammar:

    def __init__(self, rules, terminals):
        rules_dict = {}
        for rule in rules:
            lhs = rule.lhs()
            lhs_type = lhs.get(TYPE,None)
            if not lhs_type:
                sys.exit("A nonterminal has no type:" + rule)
            if lhs_type not in rules_dict:
                rules_dict[lhs_type] = []
            rules_dict[lhs_type].append(rule)
        self._rules = {key:tuple(value) for key,value in rules_dict.items()}
        self._terminals = terminals

    def find_rule(self, non_terminal):
        rules = self._rules.get(non_terminal.get(TYPE, None), None)
        if rules:
            for rule in rules:
                prodId = non_terminal.get_feature(PRODUCTION_ID_FEATURE)
                if (not prodId or (prodId == rule.lhs().get_feature(PRODUCTION_ID_FEATURE))) and featstruct.unify(non_terminal, rule.lhs(), treatBool = False):
                    yield rule

        # return (rule for rule in self._rules.get(non_terminal.get(TYPE, None),None)
        #         if featstruct.unify(non_terminal, rule.lhs(), treatBool = False))
        # non_terminal.get_feature(PRODUCTION_ID_FEATURE)  and

class AbstractEarley:

    def __init__(self, grammar):
        self._grammar = grammar

    def parse(self, input):
        if not input:
            raise ValueError("parser input is empty")
        tokens = input.split()
        return self.parse(tokens)

    def parse(self, tokens, start_symbol = None):
        if not tokens or not start_symbol:
            raise ValueError("Empty argument {}{}".format(tokens,start_symbol))

        self.init(tokens)
        self.predictor_non_terminal(start_symbol, 0)

        for i, current_chart in enumerate(self._charts, 0):
            j = 0
            while j < len(current_chart):
                state = current_chart.get_state(j)
                if state.is_finished():
                    self.completer(state, i)
                elif state.is_next_symbol_nonterminal():
                    self.predictor(state, i)
                # do not call scanner for the last chart
                elif i < len(tokens):
                    self.scanner(state, i)
                j += 1
        return ChartManager(self._charts, start_symbol, tokens)

    def init(self, tokens):
        raise NotImplementedError

    def predictor_non_terminal(self, lhs, token_index):
        for rule in self._grammar.find_rule(lhs):
            self._charts[token_index].add_state(State(rule, token_index, 0))

    def predictor (self, state, token_index):
        lhs = state.next_symbol()
        self.predictor_non_terminal(lhs, token_index)
        if lhs.has_feature({BRANCH_FEATURE: 'facultative'}):
            self._charts[token_index].add_state(State(state.rule(), state.from_index(), state.dot()+1))
        # if lhs.is_nullable():

    def completer (self, origin_state, token_index):
        lhs = origin_state.rule().lhs()
        current_chart = self._charts[token_index]
        for temp_state in self._charts[origin_state.from_index()].states():
            if (not temp_state.is_finished()) and is_nonterminal(temp_state.next_symbol()) and featstruct.unify(lhs, temp_state.next_symbol(), treatBool=False):
                current_chart.add_state(State(temp_state.rule(), temp_state.from_index(), temp_state.dot()+1))

    def scanner (self, state, token_index):
        raise NotImplementedError

class EarleyParser(AbstractEarley):

   def init(self, tokens):
       self._tokens = tokens
       self._charts = tuple(Chart() for i in range(len(tokens)+1))

   def scanner(self, state, token_index):
       if self._tokens[token_index] == state.next_symbol():
           self._charts[token_index + 1].add_state(State(state.rule(), state.from_index(), state.dot()+1))

if __name__ == "__main__":
    # docTEST this
    import doctest
    doctest.testmod()

    fstruct_reader = CelexFeatStructReader(fdict_class=FeatStructNonterminal)
    sentence = "singe ich"
    tokens = sentence.split()
    # cp = FeatureTopDownChartParser(productions, use_agenda=True, trace=trace)
    start_timer = timer()
    grammar = build_rules(tokens, fstruct_reader)
    productions = grammar.productions()
    # rule = Rule(productions[0])
    # state = State(rule, 2, 1)
    # print(rule)
    # print(state)
    # print(state.is_finished())
    earley_grammar = Grammar((Rule(production.lhs(), production.rhs()) for production in productions), None)
    # test_subj1 = FeatStructNonterminal("subj[ProdId='S6']")
    # test_subj2 = FeatStructNonterminal("S[mood='indicative',number='singular']")
    # subj1_rules = tuple(earley_grammar.find_rule(test_subj1))
    # subj2_rules = tuple(earley_grammar.find_rule(test_subj2))
    load_grammar_timer = timer()

    earley_parser = EarleyParser(earley_grammar)

    manager = earley_parser.parse(tokens, grammar.start())
    end_time = timer()
    print(manager.pretty_print(sentence))
    print("Final states:")
    final_states = tuple(manager.final_states())
    if final_states:
        for state in final_states:
            print(state.str(state.dot()-1))
    else:
        print(None)
    print("\nLoading grammar time: {:.3f}s.".format(load_grammar_timer - start_timer))
    print("Recognition time: {:.3f}s.".format(end_time - load_grammar_timer))