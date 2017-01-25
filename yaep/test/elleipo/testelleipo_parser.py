import re
import unittest

from yaep.elleipo.elleipo_parser import load_grammar, parse_ellipses


class TestEllipsisEarleyParser(unittest.TestCase):

    def setUp(self):
        # Perform set up actions (if any)
        pass

    def tearDown(self):
        pass

    def parse_ellipses_to_string(self, grammar, tokens):
        result = ''
        for tree in parse_ellipses(grammar, tokens):
            result += tree.pretty_print(0)
        # print(result)
        return re.sub(r"\s+", '', result)

    def testparse_ellipses(self):
        filename = 'Hans_ißt_Äpfel_und_Peter_ißt_Birnen'
        grammar = load_grammar('../../../fsa/elleipo/grammars/', filename + '.cf')

        # tokens = tuple(token for token in filename.split('_'))
        # tokens = tokens[0:5]  + tokens[6:]
        # result2 = self.parse_ellipses_to_string(grammar, tokens)
        # print(" ".join(tokens))

        expected_result = """
            ([None:None] S[gf='expr']
                ([0:3] S[gf='conj', head='5', subject='2']
                    ([0:1] NP[gf='subj']
                        ([0:1] PropN[case='1', gender='masc', gf='head', number='sg', person='3', stem='Hans'] Hans))
                    ([1:2] V[gf='head', mode='active', number='sg', person='3', stem='eat', tense='present'] ißt)
                    ([2:3] NP[gf='dobj']
                        ([2:3] N[case='4', gender='masc', gf='head', number='pl', person='3', stem='apple'] Äpfel)))
                ([None:None] C[gf='coord'] und)
                ([0:1] S[gf='conj', head='5', subject='2']
                    ([0:1] NP[gf='subj']
                        ([0:1] PropN[case='1', gender='masc', gf='head', number='sg', person='3', stem='Peter'] Peter))
                    ([1:1] V[gf='head', mode='active', number='sg', person='3', stem='eat', tense='present'] ißt)
                    ([1:1] NP[gf='dobj']
                        ([2:3] N[case='4', gender='masc', gf='head', number='pl', person='3', stem='apple'] Äpfel))))
            """
        # Remove all non-word characters (everything except numbers and letters)
        cleaned_expected_result = re.sub(r"\s+", '', expected_result)
        self.assertEqual(self.parse_ellipses_to_string(grammar, "Hans ißt Äpfel und Peter".split()), cleaned_expected_result)

        expected_result2 = """
        ([None:None] S[gf='expr']
            ([0:3] S[gf='conj', head='5', subject='2']
                ([0:1] NP[gf='subj']
                    ([0:1] PropN[case='1', gender='masc', gf='head', number='sg', person='3', stem='Hans'] Hans))
                ([1:2] V[gf='head', mode='active', number='sg', person='3', stem='eat', tense='present'] ißt)
                ([2:3] NP[gf='dobj']
                    ([2:3] N[case='4', gender='masc', gf='head', number='pl', person='3', stem='apple'] Äpfel)))
            ([None:None] C[gf='coord'] und)
            ([0:2] S[gf='conj', head='5', subject='2']
                ([0:1] NP[gf='subj']
                    ([0:1] PropN[case='1', gender='masc', gf='head', number='sg', person='3', stem='Peter'] Peter))
                ([1:1] V[gf='head', mode='active', number='sg', person='3', stem='eat', tense='present'] ißt)
                ([1:2] NP[gf='dobj']
                    ([1:2] N[case='4', gender='fem', gf='head', number='pl', person='3', stem='pear'] Birnen))))"""

        cleaned_expected_result2 = re.sub(r"\s+", '', expected_result2)

        self.assertEqual(self.parse_ellipses_to_string(grammar, "Hans ißt Äpfel und Peter Birnen".split()),
                         cleaned_expected_result2)


        # self.assertEqual(self.rule, Rule(self.production2.lhs(), self.production2.rhs()))
        # self.failIfEqual(self.rule, Rule(self.production3.lhs(), self.production3.rhs()))
        # self.assertTrue(self.rule != Rule(self.production3.lhs(), self.production3.rhs()))
        #
        # self.assertTrue(self.rule.is_nonterminal(0))
        # self.assertFalse(self.rule.is_terminal(0))
        #
        # self.assertTrue(self.rule.is_terminal(1))
        # self.assertFalse(self.rule.is_nonterminal(1))

    # def testget_symbol(self):
    #     self.assertEqual(self.rule.get_symbol(0), Nonterminal("A"))
    #
    # def test__hash__(self):
    #     self.assertEqual(hash(self.rule), hash(Rule(self.production2.lhs(), self.production2.rhs())))
    #     self.failIfEqual(hash(self.rule), hash(Rule(self.production3.lhs(), self.production3.rhs())))
    #
    # def testLen(self):
    #     self.assertEqual(len(self.rule), 2)


# class TestEarleyParser(unittest.TestCase):
#
#     def setUp(self):
#         # Perform set up actions (if any)
#         self.tokens1 = ["Mary", "called", "Jan"]
#         self.tokens2 = ["Mary", "called", "Jan", "from", "Frankfurt"]
#         grammar = None
#         with open("grammar.txt") as f:
#             grammar = CFG.fromstring(f.readlines())
#         self.start_nonterminal = nonterminal_to_term(grammar.start())
#
#         earley_grammar = Grammar((Rule(nonterminal_to_term(production.lhs()),
#                                        (nonterminal_to_term(fs) for fs in production.rhs())) for production
#                                   in grammar.productions()), None)
#         self.parser = EarleyParser(earley_grammar)
#
#
#     def tearDown(self):
#         # Perform clean-up actions (if any)
#         self.production = self.production2 = self.production3 = None
#         self.rule = None
#
#     def testparse(self):
#         self.parse(self.tokens1)
#         self.parse(self.tokens2)
#
#     def parse(self, tokens):
#
#         chartManager = self.parser.parse(tokens, self.start_nonterminal)
#         # print(chartManager.pretty_print(" ".join(tokens)))
#         # print("Final states:")
#         # final_states = tuple(chartManager.final_states())
#         # if final_states:
#         #     for state in final_states:
#         #         print(state.str(state.dot() - 1))
#         # print()
#
#         self.assertEqual(len(chartManager.charts()), len(tokens) + 1)
#         self.assertEqual(len(tuple(chartManager.initial_states())), 1)
#         self.assertTrue(chartManager.is_recognized())

# Run the unittests
if __name__ == '__main__':
    unittest.main()