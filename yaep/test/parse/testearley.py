import unittest

from nltk import CFG
from nltk.grammar import Nonterminal
from yaep.parse.earley import Rule, Grammar, EarleyParser, \
    nonterminal_to_term


class TestRule(unittest.TestCase):

    def setUp(self):
        # Perform set up actions (if any)
        self.production = CFG.fromstring("S -> A 'b'").productions()[0]
        self.production2 = CFG.fromstring("S -> A 'b'").productions()[0]
        self.production3 = CFG.fromstring("S -> A B").productions()[0]
        self.rule = Rule(self.production.lhs(), self.production.rhs())

    def tearDown(self):
        # Perform clean-up actions (if any)
        self.production = self.production2 = self.production3 = None
        self.rule = None

    def test__eq__(self):
        self.assertEqual(self.rule, Rule(self.production2.lhs(), self.production2.rhs()))
        self.failIfEqual(self.rule, Rule(self.production3.lhs(), self.production3.rhs()))
        self.assertTrue(self.rule != Rule(self.production3.lhs(), self.production3.rhs()))

        self.assertTrue(self.rule.is_nonterminal(0))
        self.assertFalse(self.rule.is_terminal(0))

        self.assertTrue(self.rule.is_terminal(1))
        self.assertFalse(self.rule.is_nonterminal(1))

    def testget_symbol(self):
        self.assertEqual(self.rule.get_symbol(0), Nonterminal("A"))

    def test__hash__(self):
        self.assertEqual(hash(self.rule), hash(Rule(self.production2.lhs(), self.production2.rhs())))
        self.failIfEqual(hash(self.rule), hash(Rule(self.production3.lhs(), self.production3.rhs())))

    def testLen(self):
        self.assertEqual(len(self.rule), 2)


class TestEarleyParser(unittest.TestCase):

    def setUp(self):
        # Perform set up actions (if any)
        self.tokens1 = ["Mary", "called", "Jan"]
        self.tokens2 = ["Mary", "called", "Jan", "from", "Frankfurt"]
        grammar = None
        with open("grammar.txt") as f:
            grammar = CFG.fromstring(f.readlines())
        self.start_nonterminal = nonterminal_to_term(grammar.start())

        earley_grammar = Grammar((Rule(nonterminal_to_term(production.lhs()),
                                       (nonterminal_to_term(fs) for fs in production.rhs())) for production
                                  in grammar.productions()), None)
        self.parser = EarleyParser(earley_grammar)


    def tearDown(self):
        # Perform clean-up actions (if any)
        self.production = self.production2 = self.production3 = None
        self.rule = None

    def testparse(self):
        self.parse(self.tokens1)
        self.parse(self.tokens2)

    def parse(self, tokens):

        chartManager = self.parser.parse(tokens, self.start_nonterminal)
        # print(chartManager.pretty_print(" ".join(tokens)))
        # print("Final states:")
        # final_states = tuple(chartManager.final_states())
        # if final_states:
        #     for state in final_states:
        #         print(state.str(state.dot() - 1))
        # print()

        self.assertEqual(len(chartManager.charts()), len(tokens) + 1)
        self.assertEqual(len(tuple(chartManager.initial_states())), 1)
        self.assertTrue(chartManager.is_recognized())

# Run the unittests
if __name__ == '__main__':
    unittest.main()