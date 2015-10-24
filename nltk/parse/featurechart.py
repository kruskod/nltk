# -*- coding: utf-8 -*-
# Natural Language Toolkit: Chart Parser for Feature-Based Grammars
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Rob Speer <rspeer@mit.edu>
# Peter Ljunglöf <peter.ljunglof@heatherleaf.se>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
Extension of chart parsing implementation to handle grammars with
feature structures as nodes.
"""
from __future__ import print_function, unicode_literals
import copy

from nltk.compat import xrange, python_2_unicode_compatible
from nltk.draw.tree import TreeTabView
from nltk.featstruct import FeatStruct, unify, TYPE, find_variables, EXPRESSION, _unify_feature_values, \
    _UnificationFailureError
from nltk.sem import logic, Variable
from nltk.topology.FeatTree import simplify_expression
from nltk.topology.compassFeat import GRAM_FUNC_FEATURE, INHERITED_FEATURE, PRODUCTION_ID_FEATURE, POS_FEATURE, \
    BRANCH_FEATURE
from nltk.tree import Tree
from nltk.grammar import (FeatStructNonterminal, is_nonterminal,
                          is_terminal)
from nltk.parse.chart import (TreeEdge, Chart, ChartParser, EdgeI,
                              FundamentalRule, LeafInitRule,
                              EmptyPredictRule, BottomUpPredictRule,
                              SingleEdgeFundamentalRule,
                              BottomUpPredictCombineRule,
                              TopDownInitRule, CachedTopDownPredictRule, AbstractChartRule, PGLeafInitRule)

#////////////////////////////////////////////////////////////
# Tree Edge
#////////////////////////////////////////////////////////////

@python_2_unicode_compatible
class FeatureTreeEdge(TreeEdge):
    """
    A specialized tree edge that allows shared variable bindings
    between nonterminals on the left-hand side and right-hand side.

    Each ``FeatureTreeEdge`` contains a set of ``bindings``, i.e., a
    dictionary mapping from variables to values.  If the edge is not
    complete, then these bindings are simply stored.  However, if the
    edge is complete, then the constructor applies these bindings to
    every nonterminal in the edge whose symbol implements the
    interface ``SubstituteBindingsI``.
    """

    def __init__(self, span, lhs, rhs, dot=0, bindings=None, children=None):
        """
        Construct a new edge.  If the edge is incomplete (i.e., if
        ``dot<len(rhs)``), then store the bindings as-is.  If the edge
        is complete (i.e., if ``dot==len(rhs)``), then apply the
        bindings to all nonterminals in ``lhs`` and ``rhs``, and then
        clear the bindings.  See ``TreeEdge`` for a description of
        the other arguments.
        """
        if bindings is None: bindings = {}
        if children is None:
            self.children = {}
        else:
            self.children = children

        # If the edge is complete, then substitute in the bindings,
        # and then throw them away.  (If we didn't throw them away, we
        # might think that 2 complete edges are different just because
        # they have different bindings, even though all bindings have
        # already been applied.)
        if dot == len(rhs) and bindings:
            lhs = self._bind(lhs, bindings)
            rhs = [self._bind(elt, bindings) for elt in rhs]
            bindings = {}

        # Initialize the edge.
        TreeEdge.__init__(self, span, lhs, rhs, dot)
        self._bindings = bindings
        self._comparison_key = (self._comparison_key, tuple(sorted(bindings.items())))


    @staticmethod
    def from_production(production, index):
        """
        :return: A new ``TreeEdge`` formed from the given production.
            The new edge's left-hand side and right-hand side will
            be taken from ``production``; its span will be
            ``(index,index)``; and its dot position will be ``0``.
        :rtype: TreeEdge
        """
        return FeatureTreeEdge(span=(index, index), lhs=production.lhs(),
                               rhs=production.rhs(), dot=0)

    def move_dot_forward(self, new_end, bindings=None):
        """
        :return: A new ``FeatureTreeEdge`` formed from this edge.
            The new edge's dot position is increased by ``1``,
            and its end index will be replaced by ``new_end``.
        :rtype: FeatureTreeEdge
        :param new_end: The new end index.
        :type new_end: int
        :param bindings: Bindings for the new edge.
        :type bindings: dict
        """
        return FeatureTreeEdge(span=(self._span[0], new_end),
                               lhs=self._lhs, rhs=self._rhs,
                               dot=self._dot + 1, bindings=bindings, children=self.children)

    def hfc(self):
        """
        :return: filtered features of the head node
        """
        for nt in self.rhs():
            if isinstance(nt, FeatStructNonterminal) and nt.has_feature({GRAM_FUNC_FEATURE:'hd'}):
                return nt.filter_feature(PRODUCTION_ID_FEATURE, GRAM_FUNC_FEATURE, POS_FEATURE, BRANCH_FEATURE)


    # def apply_hfc(self):
    #     """
    #     Go throw the right part of edge and apply left-part inherited features for each nonterminal
    #     if nonterminal is head, merge filtered nonterminal feautures with the left part of the rule
    #     :return:
    #     """
    #
    #     bindings = {}
    #     lhs = self._lhs.filter_feature(GRAM_FUNC_FEATURE, TYPE)
    #     res_lhs = self._lhs.copy()
    #     rhs = list()
    #     for i, nt in enumerate(self._rhs):
    #         inh_features = nt.get_feature(INHERITED_FEATURE)
    #         if inh_features:
    #             #update rule bindings
    #             feature_map = {}
    #             if isinstance(inh_features, str):
    #                 inh_features = (inh_features,)
    #             for feat in inh_features:
    #                  feat_var = Variable('?' + feat)
    #                  feat_val = lhs.get_feature(feat)
    #                  if feat_var in self._bindings:
    #                     feature_map[feat] = bindings[feat_var] = self._bindings[feat_var]
    #                  elif feat_val:
    #                     if not isinstance(feat_val, Variable):
    #                         bindings[feat_var] = feat_val
    #                     feature_map[feat] = feat_val
    #                  else:
    #                     feature_map[feat] = feat_var
    #                     #res_lhs[feat] = feat_var
    #             nt = nt.filter_feature(INHERITED_FEATURE)
    #             nt.add_feature(feature_map)
    #         if nt.has_feature({GRAM_FUNC_FEATURE:'hd'}):
    #             nt = unify(nt, lhs)
    #             if not nt:
    #                 return False
    #         rhs.append(nt)
    #     return FeatureTreeEdge(self.span(), res_lhs, rhs)

    def apply_hfc(self, bindings = {}):
            """
            Go throw the right part of edge and apply left-part inherited features for each nonterminal
            if nonterminal is head, merge filtered nonterminal feautures with the left part of the rule
            :return:
            """
            lhs = self._lhs.filter_feature(GRAM_FUNC_FEATURE, TYPE)
            res_lhs = self._lhs.copy(deep=True)
            rhs = list()
            for nt in self._rhs:
                inh_features = nt.get_feature(INHERITED_FEATURE)
                if inh_features:
                    #update rule bindings
                    feature_map = {}
                    if isinstance(inh_features, str):
                        inh_features = (inh_features,)
                    for feat in inh_features:
                         feat_var = Variable('?' + feat)
                         feat_val = lhs.get_feature(feat)
                         if feat_var in self._bindings:
                            try:
                                update_bindings(bindings, feat_var, self._bindings[feat_var])
                            except _UnificationFailureError:
                                return None
                         if feat_val or feat_val == False:
                            try:
                                update_bindings(bindings, feat_var, feat_val)
                            except _UnificationFailureError:
                                return None
                         feature_map[feat] = feat_var
                         res_lhs[feat] = feat_var
                    nt = nt.filter_feature(INHERITED_FEATURE)
                    nt.add_feature(feature_map)
                rhs.append(nt)
            for i,nt in enumerate(self._rhs):
                if nt.has_feature({GRAM_FUNC_FEATURE:'hd'}):
                    nt = unify(nt, lhs)
                    rhs[i] = nt
                    if not nt:
                        return None
                    break
            return FeatureTreeEdge(self.span(), res_lhs, rhs, bindings=bindings)


    def _bind(self, nt, bindings):
        if not isinstance(nt, FeatStructNonterminal): return nt
        return nt.substitute_bindings(bindings)

    def next_with_bindings(self):
        return self._bind(self.nextsym(), self._bindings)

    def bindings(self):
        """
        Return a copy of this edge's bindings dictionary.
        """
        return self._bindings.copy()

    def variables(self):
        """
        :return: The set of variables used by this edge.
        :rtype: set(Variable)
        """
        return find_variables([self._lhs] + list(self._rhs) +
                              list(self._bindings.keys()) +
                              list(self._bindings.values()),
                              fs_class=FeatStruct)

    def __str__(self):
        if self.is_complete():
            return TreeEdge.__unicode__(self)
        else:
            bindings = '{%s}' % ', '.join('%s: %r' % item for item in
                                          sorted(self._bindings.items()))
            return '%s %s' % (TreeEdge.__unicode__(self), bindings)


#////////////////////////////////////////////////////////////
# A specialized Chart for feature grammars
#////////////////////////////////////////////////////////////

# TODO: subsumes check when adding new edges

class FeatureChart(Chart):
    """
    A Chart for feature grammars.
    :see: ``Chart`` for more information.
    """

    def select(self, **restrictions):
        """
        Returns an iterator over the edges in this chart.
        See ``Chart.select`` for more information about the
        ``restrictions`` on the edges.
        """
        # If there are no restrictions, then return all edges.
        if restrictions == {}: return iter(self._edges)

        # Find the index corresponding to the given restrictions.
        restr_keys = sorted(restrictions.keys())
        restr_keys = tuple(restr_keys)

        # If it doesn't exist, then create it.
        if restr_keys not in self._indexes:
            self._add_index(restr_keys)

        vals = tuple(self._get_type_if_possible(restrictions[key])
                     for key in restr_keys)
        return iter(self._indexes[restr_keys].get(vals, []))

    def _add_index(self, restr_keys):
        """
        A helper function for ``select``, which creates a new index for
        a given set of attributes (aka restriction keys).
        """
        # Make sure it's a valid index.
        for key in restr_keys:
            if not hasattr(EdgeI, key):
                raise ValueError('Bad restriction: %s' % key)

        # Create the index.
        index = self._indexes[restr_keys] = {}

        # Add all existing edges to the index.
        for edge in self._edges:
            vals = tuple(self._get_type_if_possible(getattr(edge, key)())
                         for key in restr_keys)
            index.setdefault(vals, []).append(edge)

    def _register_with_indexes(self, edge):
        """
        A helper function for ``insert``, which registers the new
        edge with all existing indexes.
        """
        for (restr_keys, index) in self._indexes.items():
            vals = tuple(self._get_type_if_possible(getattr(edge, key)())
                         for key in restr_keys)
            index.setdefault(vals, []).append(edge)

    def _get_type_if_possible(self, item):
        """
        Helper function which returns the ``TYPE`` feature of the ``item``,
        if it exists, otherwise it returns the ``item`` itself
        """
        if isinstance(item, dict) and TYPE in item:
            return item[TYPE]
        else:
            return item

    def parses(self, start, tree_class=Tree):
        for edge in self.select(start=0, end=self._num_leaves):
            if ((isinstance(edge, FeatureTreeEdge)) and
                    (edge.lhs()[TYPE] == start[TYPE]) and
                    (unify(edge.lhs(), start, rename_vars=True))
            ):
                for tree in self.trees(edge, complete=True, tree_class=tree_class):
                    yield tree


#////////////////////////////////////////////////////////////
# Fundamental Rule
#////////////////////////////////////////////////////////////

class FeatureFundamentalRule(FundamentalRule):
    """
    A specialized version of the fundamental rule that operates on
    nonterminals whose symbols are ``FeatStructNonterminal``s.  Rather
    tha simply comparing the nonterminals for equality, they are
    unified.  Variable bindings from these unifications are collected
    and stored in the chart using a ``FeatureTreeEdge``.  When a
    complete edge is generated, these bindings are applied to all
    nonterminals in the edge.

    The fundamental rule states that:

    - ``[A -> alpha \* B1 beta][i:j]``
    - ``[B2 -> gamma \*][j:k]``

    licenses the edge:

    - ``[A -> alpha B3 \* beta][i:j]``

    assuming that B1 and B2 can be unified to generate B3.
    """

    def apply(self, chart, grammar, left_edge, right_edge):
        # Make sure the rule is applicable.
        if not (left_edge.end() == right_edge.start() and
                    #left_edge.is_incomplete() and
                    right_edge.is_complete() and
                    isinstance(left_edge, FeatureTreeEdge)):
            return
        found = right_edge.lhs()
        nextsym = left_edge.nextsym()
        if isinstance(right_edge, FeatureTreeEdge):
            if not is_nonterminal(nextsym): return
            if left_edge.nextsym()[TYPE] != right_edge.lhs()[TYPE]: return
            # Create a copy of the bindings.
            bindings = left_edge.bindings()
            # We rename vars here, because we don't want variables
            # from the two different productions to match.
            found = found.rename_variables(used_vars=left_edge.variables())
            # Unify B1 (left_edge.nextsym) with B2 (right_edge.lhs) to
            # generate B3 (result).
            result = unify(nextsym, found, bindings, rename_vars=False)
            if result is None: return
        else:
            if nextsym != found: return
            # Create a copy of the bindings.
            bindings = left_edge.bindings()

        # Construct the new edge.
        new_edge = left_edge.move_dot_forward(right_edge.end(), bindings)

        # Add it to the chart, with appropriate child pointers.
        if chart.insert_with_backpointer(new_edge, left_edge, right_edge):
            yield new_edge


class FeatureSingleEdgeFundamentalRule(SingleEdgeFundamentalRule):
    """
    A specialized version of the completer / single edge fundamental rule
    that operates on nonterminals whose symbols are ``FeatStructNonterminal``s.
    Rather than simply comparing the nonterminals for equality, they are
    unified.
    """
    _fundamental_rule = FeatureFundamentalRule()

    def _apply_complete(self, chart, grammar, right_edge):
        fr = self._fundamental_rule
        for left_edge in chart.select(end=right_edge.start(),
                                      is_complete=False,
                                      nextsym=right_edge.lhs()):
            for new_edge in fr.apply(chart, grammar, left_edge, right_edge):
                yield new_edge

    def _apply_incomplete(self, chart, grammar, left_edge):
        fr = self._fundamental_rule
        for right_edge in chart.select(start=left_edge.end(),
                                       is_complete=True,
                                       lhs=left_edge.nextsym()):
            for new_edge in fr.apply(chart, grammar, left_edge, right_edge):
                yield new_edge


class PGFeatureSingleEdgeFundamentalRule(FeatureSingleEdgeFundamentalRule):
    """
    A specialized version of the fundamental rule that operates on
    nonterminals whose symbols are ``FeatStructNonterminal``s.  Rather
    tha simply comparing the nonterminals for equality, they are
    unified.  Variable bindings from these unifications are collected
    and stored in the chart using a ``FeatureTreeEdge``.  When a
    complete edge is generated, these bindings are applied to all
    nonterminals in the edge.

    The fundamental rule states that:

    - ``[A -> alpha \* B1 beta][i:j]``
    - ``[B2 -> gamma \*][j:k]``

    licenses the edge:

    - ``[A -> alpha B3 \* beta][i:j]``

    assuming that B1 and B2 can be unified to generate B3.
    """

    def _apply_complete(self, chart, grammar, right_edge):
        for left_edge in chart.select(end=right_edge.start(),
                                      is_complete=False,
                                      nextsym=right_edge.lhs()):
            for new_edge in self.apply_rule(chart, grammar, left_edge, right_edge):
                yield new_edge

    def _apply_incomplete(self, chart, grammar, left_edge):
        for right_edge in chart.select(start=left_edge.end(),
                                       is_complete=True,
                                       lhs=left_edge.nextsym()):
            for new_edge in self.apply_rule(chart, grammar, left_edge, right_edge):
                yield new_edge

    def apply_rule(self, chart, grammar, left_edge, right_edge):
        # Make sure the rule is applicable.
        if not (left_edge.end() == right_edge.start() and
                    #left_edge.is_incomplete() and
                    right_edge.is_complete() and
                    isinstance(left_edge, FeatureTreeEdge)):
            return
        found = right_edge.lhs()
        nextsym = left_edge.nextsym()
        if isinstance(right_edge, FeatureTreeEdge):
            if not is_nonterminal(nextsym): return
            if left_edge.nextsym()[TYPE] != right_edge.lhs()[TYPE]: return
            # Create a copy of the bindings.
            bindings = left_edge.bindings()
            # We rename vars here, because we don't want variables
            # from the two different productions to match.
            found = found.rename_variables(used_vars=left_edge.variables())
            # Unify B1 (left_edge.nextsym) with B2 (right_edge.lhs) to
            # generate B3 (result).
            result = None
            hfc = right_edge.hfc()
            if hfc:
                hfc.pop(TYPE, None)
                new_found = unify(found, hfc, rename_vars=False)
                # if not new_found or not unify(nextsym, new_found, bindings, rename_vars=False):
                #     return
                if new_found:
                    result = unify(nextsym.filter_feature(BRANCH_FEATURE), new_found, bindings, rename_vars=False)
            else:
                result = unify(nextsym.filter_feature(BRANCH_FEATURE), found, bindings, rename_vars=False)
            if result:
                #right_edge = FeatureTreeEdge(right_edge.span(), result, right_edge.rhs(), dot = right_edge.dot(), bindings=right_edge.bindings())
                # if hfc:
                #     right_edge = right_edge.apply_hfc()
                sync_bindings(left_edge.lhs(), result, bindings)
                pass
            else:
                return
        else:
            if nextsym != found: return
            # Create a copy of the bindings.
            bindings = left_edge.bindings()

        # Construct the new edge.
        new_edge = left_edge.move_dot_forward(right_edge.end(), bindings)

        if not left_edge.dot() in new_edge.children:
            new_edge.children[left_edge.dot()] = set()

        # if is_nonterminal(nextsym):
        new_edge.children[left_edge.dot()].add(hash(right_edge))
        # Add it to the chart, with appropriate child pointers.
        if chart.insert_with_backpointer(new_edge, left_edge, right_edge):
            yield new_edge


def sync_bindings(lhs, rhs, bindings):
    """
        iterating throw all lhs key/values and update bindings according to rhs values
    :param lhs: FeatStructNonterminal
    :param rhs: FeatStructNonterminal
    :param bindings: map where keys are instances of Variable
    :return: none
    """
    if EXPRESSION in lhs:
        simpl_expres = simplify_expression(lhs[EXPRESSION])
        for exp in simpl_expres:
            for key,value in exp.items():
                if isinstance(value, Variable):
                    feat_val = rhs.get_feature(key)
                    try:
                        update_bindings(bindings, value, feat_val)
                    except _UnificationFailureError:
                        pass
    else:
        for key,value in lhs.items():
            if isinstance(value, Variable):
                feat_val = rhs.get_feature(key)
                try:
                    update_bindings(bindings, value, feat_val)
                except _UnificationFailureError:
                    pass

def update_bindings(bindings, key, val):
    if (not val and val != False) or isinstance(val, Variable):
        return
    if key in bindings:
        bindings[key] = _unify_feature_values(key, bindings[key], val, (), (), None, None, FeatStructNonterminal, None)
        pass
    else:
        bindings[key] = val

#////////////////////////////////////////////////////////////
# Top-Down Prediction
#////////////////////////////////////////////////////////////

class FeatureTopDownInitRule(TopDownInitRule):
    def apply(self, chart, grammar):
        for prod in grammar.productions(lhs=grammar.start()):
            new_edge = FeatureTreeEdge.from_production(prod, 0)
            if chart.insert(new_edge, ()):
                yield new_edge


class FeatureTopDownPredictRule(AbstractChartRule):
    """
    A rule licensing edges corresponding to the grammar productions
    for the nonterminal following an incomplete edge's dot.  In
    particular, this rule specifies that
    ``[A -> alpha \* B beta][i:j]`` licenses the edge
    ``[B -> \* gamma][j:j]`` for each grammar production ``B -> gamma``.

    :note: This rule corresponds to the Predictor Rule in Earley parsing.
    """
    NUM_EDGES = 1

    def apply(self, chart, grammar, edge):
        if edge.is_complete(): return
        for prod in grammar.productions(lhs=edge.nextsym()):
            new_edge = FeatureTreeEdge.from_production(prod, edge.end())
            if chart.insert(new_edge, ()):
                yield new_edge



class PGFeatureTopDownPredictRule(AbstractChartRule):
    """
    A rule licensing edges corresponding to the grammar productions
    for the nonterminal following an incomplete edge's dot.  In
    particular, this rule specifies that
    ``[A -> alpha \* B beta][i:j]`` licenses the edge
    ``[B -> \* gamma][j:j]`` for each grammar production ``B -> gamma``.

    :note: This rule corresponds to the Predictor Rule in Earley parsing.
    """
    NUM_EDGES = 1
    FACULTATIVE_VAL = "facultative"
    inserted_edges = []

    def apply(self, chart, grammar, edge):
        if edge.is_complete(): return
        lhs=edge.nextsym()
        bindings = edge.bindings()
        for prod in grammar.productions(lhs):
            new_edge = FeatureTreeEdge.from_production(prod, edge.end())
            #unify new_edge and edge and insert unified edge in chart

            rhs = new_edge.lhs()
            hfc = new_edge.hfc()
            result = None
            if hfc:
                hfc.pop(TYPE, None)
                rhs_hfc = unify(rhs, hfc, rename_vars=False)
                if rhs_hfc:
                    result = unify(rhs_hfc, lhs.filter_feature(BRANCH_FEATURE), bindings=bindings, rename_vars=False)
            else:
                # increasing speed of parsing by checking terminal position
                # if is_terminal(new_edge.rhs()):
                #     if edge.end() < len(chart._tokens) and new_edge.rhs()[0] != chart._tokens[edge.end()]:
                        # continue
                result = unify(rhs, lhs.filter_feature(BRANCH_FEATURE), bindings=bindings, rename_vars=False)
            if result:
                if rhs != result:
                    new_right_edge = FeatureTreeEdge(new_edge.span(), result, new_edge.rhs(), bindings=bindings)
                    if hfc:
                        new_right_edge = new_right_edge.apply_hfc(bindings)
                    if new_right_edge:
                        # if chart.insert(new_right_edge, ()):
                        #     self.inserted_edges.append(new_right_edge)
                        #     yield new_right_edge
                        if chart.insert(new_edge, ()):
                            yield new_edge
                else:
                    if chart.insert(new_edge, ()):
                        yield new_edge
        if is_nonterminal(lhs) and lhs.has_feature({BRANCH_FEATURE: self.FACULTATIVE_VAL}):
            # new_edge = edge.move_dot_forward(new_end=edge.end(),bindings=bindings)
            rhs = list(edge.rhs())
            rhs.remove(lhs)
            new_edge = FeatureTreeEdge(edge.span(),
                               lhs=edge.lhs(), rhs=tuple(rhs),
                               dot=edge.dot(), bindings=bindings, children=copy.deepcopy(edge.children))
            # if chart.insert_with_backpointer(new_edge, edge, None):
            #     yield new_edge
            if chart.insert(new_edge, *chart.child_pointer_lists(edge)):
                yield new_edge

class FeatureCachedTopDownPredictRule(CachedTopDownPredictRule):
    """
    A specialized version of the (cached) top down predict rule that operates
    on nonterminals whose symbols are ``FeatStructNonterminal``s.  Rather
    than simply comparing the nonterminals for equality, they are
    unified.

    The top down expand rule states that:

    - ``[A -> alpha \* B1 beta][i:j]``

    licenses the edge:

    - ``[B2 -> \* gamma][j:j]``

    for each grammar production ``B2 -> gamma``, assuming that B1
    and B2 can be unified.
    """

    def apply(self, chart, grammar, edge):
        if edge.is_complete(): return
        nextsym, index = edge.nextsym(), edge.end()
        if not is_nonterminal(nextsym): return

        # If we've already applied this rule to an edge with the same
        # next & end, and the chart & grammar have not changed, then
        # just return (no new edges to add).
        nextsym_with_bindings = edge.next_with_bindings()
        done = self._done.get((nextsym_with_bindings, index), (None, None))
        if done[0] is chart and done[1] is grammar:
            return

        for prod in grammar.productions(lhs=nextsym):
            # If the left corner in the predicted production is
            # leaf, it must match with the input.
            if prod.rhs():
                first = prod.rhs()[0]
                if is_terminal(first):
                    if index >= chart.num_leaves(): continue
                    if first != chart.leaf(index): continue

            # We rename vars here, because we don't want variables
            # from the two different productions to match.
            if unify(prod.lhs(), nextsym_with_bindings, rename_vars=True):
                new_edge = FeatureTreeEdge.from_production(prod, edge.end())
                if chart.insert(new_edge, ()):
                    yield new_edge

        # Record the fact that we've applied this rule.
        self._done[nextsym_with_bindings, index] = (chart, grammar)


#////////////////////////////////////////////////////////////
# Bottom-Up Prediction
#////////////////////////////////////////////////////////////

class FeatureBottomUpPredictRule(BottomUpPredictRule):
    def apply(self, chart, grammar, edge):
        if edge.is_incomplete(): return
        for prod in grammar.productions(rhs=edge.lhs()):
            if isinstance(edge, FeatureTreeEdge):
                _next = prod.rhs()[0]
                if not is_nonterminal(_next): continue

            new_edge = FeatureTreeEdge.from_production(prod, edge.start())
            if chart.insert(new_edge, ()):
                yield new_edge


class FeatureBottomUpPredictCombineRule(BottomUpPredictCombineRule):
    def apply(self, chart, grammar, edge):
        if edge.is_incomplete(): return
        found = edge.lhs()
        for prod in grammar.productions(rhs=found):
            bindings = {}
            if isinstance(edge, FeatureTreeEdge):
                _next = prod.rhs()[0]
                if not is_nonterminal(_next): continue

                # We rename vars here, because we don't want variables
                # from the two different productions to match.
                used_vars = find_variables((prod.lhs(),) + prod.rhs(),
                                           fs_class=FeatStruct)
                found = found.rename_variables(used_vars=used_vars)

                result = unify(_next, found, bindings, rename_vars=False)
                if result is None: continue

            new_edge = (FeatureTreeEdge.from_production(prod, edge.start())
                        .move_dot_forward(edge.end(), bindings))
            if chart.insert(new_edge, (edge,)):
                yield new_edge


class FeatureEmptyPredictRule(EmptyPredictRule):
    def apply(self, chart, grammar):
        for prod in grammar.productions(empty=True):
            for index in xrange(chart.num_leaves() + 1):
                new_edge = FeatureTreeEdge.from_production(prod, index)
                if chart.insert(new_edge, ()):
                    yield new_edge


#////////////////////////////////////////////////////////////
# Feature Chart Parser
#////////////////////////////////////////////////////////////

TD_FEATURE_STRATEGY = [PGLeafInitRule(),
                       FeatureTopDownInitRule(),
                       PGFeatureTopDownPredictRule(),
                       FeatureSingleEdgeFundamentalRule()]
BU_FEATURE_STRATEGY = [LeafInitRule(),
                       FeatureEmptyPredictRule(),
                       FeatureBottomUpPredictRule(),
                       FeatureSingleEdgeFundamentalRule()]
BU_LC_FEATURE_STRATEGY = [LeafInitRule(),
                          FeatureEmptyPredictRule(),
                          FeatureBottomUpPredictCombineRule(),
                          FeatureSingleEdgeFundamentalRule()]


class FeatureChartParser(ChartParser):
    def __init__(self, grammar,
                 strategy=TD_FEATURE_STRATEGY,
                 trace_chart_width=20,
                 chart_class=FeatureChart,
                 **parser_args):
        ChartParser.__init__(self, grammar,
                             strategy=strategy,
                             trace_chart_width=trace_chart_width,
                             chart_class=chart_class,
                             **parser_args)


class FeatureTopDownChartParser(FeatureChartParser):
    def __init__(self, grammar, **parser_args):
        FeatureChartParser.__init__(self, grammar, TD_FEATURE_STRATEGY, **parser_args)


class FeatureBottomUpChartParser(FeatureChartParser):
    def __init__(self, grammar, **parser_args):
        FeatureChartParser.__init__(self, grammar, BU_FEATURE_STRATEGY, **parser_args)


class FeatureBottomUpLeftCornerChartParser(FeatureChartParser):
    def __init__(self, grammar, **parser_args):
        FeatureChartParser.__init__(self, grammar, BU_LC_FEATURE_STRATEGY, **parser_args)


#////////////////////////////////////////////////////////////
# Instantiate Variable Chart
#////////////////////////////////////////////////////////////

class InstantiateVarsChart(FeatureChart):
    """
    A specialized chart that 'instantiates' variables whose names
    start with '@', by replacing them with unique new variables.
    In particular, whenever a complete edge is added to the chart, any
    variables in the edge's ``lhs`` whose names start with '@' will be
    replaced by unique new ``Variable``s.
    """

    def __init__(self, tokens):
        FeatureChart.__init__(self, tokens)

    def initialize(self):
        self._instantiated = set()
        FeatureChart.initialize(self)

    def insert(self, edge, child_pointer_list):
        if edge in self._instantiated: return False
        self.instantiate_edge(edge)
        return FeatureChart.insert(self, edge, child_pointer_list)

    def instantiate_edge(self, edge):
        """
        If the edge is a ``FeatureTreeEdge``, and it is complete,
        then instantiate all variables whose names start with '@',
        by replacing them with unique new variables.

        Note that instantiation is done in-place, since the
        parsing algorithms might already hold a reference to
        the edge for future use.
        """
        # If the edge is a leaf, or is not complete, or is
        # already in the chart, then just return it as-is.
        if not isinstance(edge, FeatureTreeEdge): return
        if not edge.is_complete(): return
        if edge in self._edge_to_cpls: return

        # Get a list of variables that need to be instantiated.
        # If there are none, then return as-is.
        inst_vars = self.inst_vars(edge)
        if not inst_vars: return

        # Instantiate the edge!
        self._instantiated.add(edge)
        edge._lhs = edge.lhs().substitute_bindings(inst_vars)

    def inst_vars(self, edge):
        return dict((var, logic.unique_variable())
                    for var in edge.lhs().variables()
                    if var.name.startswith('@'))


#////////////////////////////////////////////////////////////
# Demo
#////////////////////////////////////////////////////////////

def demo_grammar():
    from nltk.grammar import FeatureGrammar

    return FeatureGrammar.fromstring("""
S  -> NP VP
PP -> Prep NP
NP -> NP PP
VP -> VP PP
VP -> Verb NP
VP -> Verb
NP -> Det[pl=?x] Noun[pl=?x]
NP -> "John"
NP -> "I"
Det -> "the"
Det -> "my"
Det[-pl] -> "a"
Noun[-pl] -> "dog"
Noun[-pl] -> "cookie"
Verb -> "ate"
Verb -> "saw"
Prep -> "with"
Prep -> "under"
""")


def demo(print_times=True, print_grammar=True,
         print_trees=True, print_sentence=True,
         trace=1,
         parser=FeatureChartParser,
         sent='I saw John with a dog with my cookie'):
    import time

    print()
    grammar = demo_grammar()
    if print_grammar:
        print(grammar)
        print()
    print("*", parser.__name__)
    if print_sentence:
        print("Sentence:", sent)
    tokens = sent.split()
    t = time.clock()
    cp = parser(grammar, trace=trace)
    chart = cp.chart_parse(tokens)
    trees = list(chart.parses(grammar.start()))
    if print_times:
        print("Time: %s" % (time.clock() - t))
    if print_trees:
        for tree in trees: print(tree)
    else:
        print("Nr trees:", len(trees))


def run_profile():
    import profile

    profile.run('for i in range(1): demo()', '/tmp/profile.out')
    import pstats

    p = pstats.Stats('/tmp/profile.out')
    p.strip_dirs().sort_stats('time', 'cum').print_stats(60)
    p.strip_dirs().sort_stats('cum', 'time').print_stats(60)

def celex_preprocessing(file_name):
    from nltk.featstruct import pair_checker
    _CELEX_SEPARATOR = "|-"
    _PRODUCTION_SEPARATOR = " -> "
    phrasal_head_map = {};
    with open(file_name, encoding='utf-8') as file:
        line_num = 0
        for line in file:
            line_num += 1
            line = line.rstrip()
            if line and not line.startswith('#'):
                if _CELEX_SEPARATOR in line:
                    tree, postProduction = line.split(_CELEX_SEPARATOR)
                    postProduction = postProduction.strip()
                    group = pair_checker(tree)
                    if (group):
                        start_group, end_group = group
                        s = tree[start_group+1:end_group]
                        group = pair_checker(s)
                        if (group):
                            start_group, end_group = group
                            production = []
                            production.append( s[:start_group].strip() )
                            while(group):
                                start_group, end_group = group
                                # Inside this group: mod (ADVP [branch=facultative])
                                # we take first member as feature and collect a second member as nonterminal
                                start_nonterminal, end_nonterminal = pair_checker(s, start_group + 1)
                                grammatical_function = s[start_group +1:start_nonterminal].strip()
                                nonterminal = s[start_nonterminal + 1: end_nonterminal].strip()
                                phrasal_head = nonterminal
                                index = len(nonterminal)
                                insert = GRAM_FUNC_FEATURE + '=' + grammatical_function
                                # check if there are any features
                                try:
                                    feat_block = pair_checker(s, start_nonterminal + 1)
                                except ValueError:
                                    insert = '[' + insert + ']'
                                else:
                                    if feat_block:
                                        phrasal_head = s[start_nonterminal + 1: feat_block[0]].strip()
                                        if s[feat_block[0] + 1:feat_block[1]].strip(): # if feature block is not empty
                                            insert = ',' + insert
                                        #recognise case when there is not enough brackets
                                        if len(s[feat_block[1] + 1:end_nonterminal].strip()) > 1:
                                            nonterminal= phrasal_head + '[' + s[feat_block[0]:end_nonterminal] + ']'
                                        index = len(nonterminal)
                                        index -= 1
                                    else:
                                        insert = '[' + insert + ']'
                                finally:
                                    nonterminal = nonterminal[:index] + insert + nonterminal[index:]

                                if 'hd' == grammatical_function:
                                    prodId = PRODUCTION_ID_FEATURE + '=' + postProduction
                                    nonterminal = nonterminal[:-1] + ',' + prodId + nonterminal[-1:]
                                    phrasal_head_map[postProduction] = (phrasal_head, prodId)
                                    # yield nonterminal + _PRODUCTION_SEPARATOR + postProduction
                                production.append(nonterminal)
                                group = pair_checker(s, end_group + 1)
                    yield production[0] + _PRODUCTION_SEPARATOR + " ".join(production[1:])
                elif _PRODUCTION_SEPARATOR in line:
                    lhs, rhs = line.split(_PRODUCTION_SEPARATOR)
                    group = pair_checker(lhs)
                    if (group):
                        phrasal_head = lhs[:group[0]].strip()
                        if phrasal_head in phrasal_head_map:
                            phrasal_head, prodId = phrasal_head_map[phrasal_head]
                            if lhs[group[0] + 1:group[1]].strip(): # if feature block is not empty
                                prodId = ',' + prodId
                            lhs = phrasal_head + lhs[group[0]: -1] + prodId + lhs[group[1]:]
                    else:
                        phrasal_head = lhs.strip()
                        if phrasal_head in phrasal_head_map:
                            phrasal_head, prodId = phrasal_head_map[phrasal_head]
                            lhs = phrasal_head + '[' + prodId + ']'
                    yield lhs + _PRODUCTION_SEPARATOR + rhs
                else:
                    yield line

def pg_demo():
    """
    Demo for Performance Grammar FeatureChart
    """

    import time
    from nltk.featstruct import CelexFeatStructReader
    from nltk.grammar import FeatureGrammar
    from nltk.parse.earleychart import wordPresenceVerifier

    sentence = 'Hans sieht'
    #sentence = 'sehe ich'
    t = time.clock()
    #grammar = load('../../examples/grammars/book_grammars/pg_german.fcfg')
    #grammar = load('../../examples/grammars/book_grammars/test.fcfg')
    #grammar = load('../../fsa/lexframetree.fcfg')

    # #opened_resource = _open('../../examples/grammars/book_grammars/test.fcfg')
    # opened_resource = _open('../../fsa/lexfootexport.fcfg')
    # #opened_resource = _open('../../examples/grammars/book_grammars/pg_german.fcfg')
    # binary_data = opened_resource.read()
    # string_data = binary_data.decode('utf-8')
    fstruct_reader = CelexFeatStructReader(fdict_class=FeatStructNonterminal)
    #grammar = FeatureGrammar.fromstring(celex_preprocessing('../../examples/grammars/book_grammars/test.fcfg'), logic_parser=None, fstruct_reader=fstruct_reader, encoding=None)
    #productions = FeatureGrammar.fromstring(celex_preprocessing('../../fsa/lex_test.fcfg'), logic_parser=None, fstruct_reader=fstruct_reader, encoding=None)
    productions = FeatureGrammar.fromstring(celex_preprocessing('../../examples/grammars/book_grammars/pg_german.fcfg'), logic_parser=None, fstruct_reader=fstruct_reader, encoding=None)

    # lexical_productions = FeatureGrammar.fromstring(string_data, logic_parser=None, fstruct_reader=fstruct_reader, encoding=None)
    #productions = FeatureGrammar(grammar_productions.start(), grammar_productions.productions())
    #
    # with open('../../fsa/celex.pickle', 'wb') as f:
    #     pickle.dump(productions, f, pickle.HIGHEST_PROTOCOL)
    # #print(resource_val)
    #productions = []

    # with open('../../fsa/celex.pickle', 'rb') as f:
    #     productions = pickle.load(f)
    # print("Execution time: ", (time.clock() - t))
    # tokens = sent.split()
    # # for comb in itertools.permutations(tokens):
    #print(productions)
    cp = FeatureTopDownChartParser(productions, trace=1)
    tokens = sentence.split()
    trees = list(cp.parse(tokens))

    verifier = wordPresenceVerifier(tokens)
    dominance_structures = []
    count_trees = 0
    for tree in trees:
        count_trees += 1
        ver_result = verifier(tree)
        if ver_result:
            dominance_structures.append(tree)
        else:
            print(tree)
            print("Word presence verification result: {}\n".format(ver_result))

    if dominance_structures:
        print("####################################################")
        print("Dominance structures:")
        for tree in dominance_structures:
            print(tree)
        TreeTabView(*dominance_structures[:20])

    print("Nr trees:", count_trees)
    print("Nr Dominance structures:", len(dominance_structures))
    print("Time:", t)
    #print("Execution time: ", (time.clock() - t))

if __name__ == '__main__':
    pg_demo()
