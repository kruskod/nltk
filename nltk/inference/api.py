# Natural Language Toolkit: Classifier Interface
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#         Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

"""
Interfaces for theorem provers and model builders.

L{Prover} is a standard interface for a theorem prover which tries to prove a goal from a 
list of assumptions.

L{ModelBuilder} is a standard interface for a model builder. Given just a set of assumptions.
the model builder tries to build a model for the assumptions. Given a set of assumptions and a 
goal M{G}, the model builder tries to find a counter-model, in the sense of a model that will satisfy
the assumptions plus the negation of M{G}. 
"""

class Prover(object):
    """
    Interface for trying to prove a goal from assumptions. 
    Both the goal and the assumptions are 
    constrained to be formulas of L{logic.Expression}.
    """
    def prove(self, goal=None, assumptions=[], verbose=False):
        """
        @return: Whether the proof was successful or not.
        @rtype: C{bool} 
        """
        raise NotImplementedError()
    
class ModelBuilder(object):
    """
    Interface for trying to build a model of set of formulas.
    Open formulas are assumed to be universally quantified.
    Both the goal and the assumptions are 
    constrained to be formulas of L{logic.Expression}.
    """
    def build_model(self, goal=None, assumptions=[], verbose=False):
        """
        @return: A model if one is generated; None otherwise.
        @rtype: C{nltk.sem.evaluate.Valuation} 
        """
        raise NotImplementedError()


class TheoremToolCommand(object):
    """
    This class holds a goal and a list of assumptions to be used in proving
    or model building.
    """
    def __init__(self, goal=None, assumptions=[]):
        """
        @param goal: Input expression to prove
        @type goal: L{logic.Expression}
        @param assumptions: Input expressions to use as assumptions in 
            the proof.
        @type assumptions: C{list} of L{logic.Expression}
        """
        self._goal = goal
        """The logic expression to prove.
           L{logic.Expression}"""
        
        self._assumptions = list(assumptions)
        """The set of expressions to use as assumptions in the proof.
           C{list} of L{logic.Expression}"""
           
        self._result = None
        """A holder for the result, so prevent unnecessary re-proving"""
        
    def add_assumptions(self, new_assumptions):
        """
        Add new assumptions to the assumption list.
        
        @param new_assumptions: new assumptions
        @type new_assumptions: C{list} of L{sem.logic.Expression}s
        """
        self._assumptions += new_assumptions
        self._result = None
    
    def retract_assumptions(self, retracted, debug=False):
        """
        Retract assumptions from the assumption list.
        
        @param debug: If True, give warning when C{retracted} is not present on 
        assumptions list.
        @type debug: C{bool}
        @param retracted: assumptions to be retracted
        @type retracted: C{list} of L{sem.logic.Expression}s
        """
        retracted = set(retracted)
        result_list = [a for a in self._assumptions if a not in retracted]
        if debug and result_list == self._assumptions:
            print Warning("Assumptions list has not been changed:")
            self.assumptions()
            
        self._assumptions = result_list
        
        self._result = None
    
    def assumptions(self):
        """
        List the current assumptions.       
        """
        return self._assumptions
    
    def goal(self):
        """
        Return the goal
        """
        return self._goal
        
    def print_assumptions(self):
        """
        Print the list of the current assumptions.       
        """
        for a in self.assumptions():
            print a

class ProverCommand(TheoremToolCommand):
    """
    This class holds a C{Prover}, a goal, and a list of assumptions.  When
    prove() is called, the C{Prover} is executed with the goal and assumptions.
    """
    def __init__(self, prover, goal=None, assumptions=[]):
        """
        @param prover: The theorem tool to execute with the assumptions
        @type prover: C{Prover}
        @see: C{TheoremToolCommand}
        """
        self._prover = prover
        """The theorem tool to execute with the assumptions"""
        
        TheoremToolCommand.__init__(self, goal, assumptions)
        
        self._proof = None

    def prove(self, verbose=False):
        """
        Perform the actual proof.  Store the result to prevent unnecessary
        re-proving.
        """
        if self._result is None:
            self._result, self._proof = self._prover.prove(self.goal(), 
                                                           self.assumptions(),
                                                           verbose)
        return self._result

    def show_proof(self):
        print self._proof

    def get_prover(self):
        return self._prover
    
class ModelBuilderCommand(TheoremToolCommand):
    """
    This class holds a C{ModelBuilder}, a goal, and a list of assumptions.  When
    build_model() is called, the C{ModelBuilder} is executed with the goal and 
    assumptions.
    """
    def __init__(self, modelbuilder, goal=None, assumptions=[]):
        """
        @param modelbuilder: The theorem tool to execute with the assumptions
        @type modelbuilder: C{ModelBuilder}
        @see: C{TheoremToolCommand}
        """
        self._modelbuilder = modelbuilder
        """The theorem tool to execute with the assumptions"""
        
        TheoremToolCommand.__init__(self, goal, assumptions)
        
        self._valuation = None

    def build_model(self, verbose=False):
        """
        Perform the actual proof.  Store the result to prevent unnecessary
        re-building.
        """
        if self._result is None:
            self._result, self._valuation = \
                    self._modelbuilder.build_model(self.goal(), 
                                                   self.assumptions(),
                                                   verbose)
        return self._result

