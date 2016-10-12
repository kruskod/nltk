# testsplitter.py
import unittest
# Unit tests
from nltk import CFG
from yaep.parse.earley import Rule
from nltk.grammar import Nonterminal

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
        self.grammar = None
        with open("grammar.txt") as f:
            self.grammar = CFG.fromstring(f.readlines())
        print(self.grammar)


    def tearDown(self):
        # Perform clean-up actions (if any)
        self.production = self.production2 = self.production3 = None
        self.rule = None

    def testparse(self):
        self.assertTrue(True)

    def parse(self):

        chartManager = parser.parse(tokens);
        System.out.println(Chart.prettyPrint(String.join(" ", tokens), chartManager.getCharts()));
        // check
        chart
        size
        assertThat(chartManager.getCharts().length, equalTo(tokens.length + 1));
        assertTrue(1 == chartManager.initialStates().count());
        assertTrue(chartManager.isRecognized());


# Run the unittests
if __name__ == '__main__':
    unittest.main()