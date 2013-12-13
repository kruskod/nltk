# -*- coding: utf-8 -*-


# Natural Language Toolkit: Brill Tagger
#
# Copyright (C) 2001-2013 NLTK Project
# Authors: Christopher Maloof <cjmaloof@gradient.cis.upenn.edu>
#          Edward Loper <edloper@gmail.com>
#          Steven Bird <stevenbird1@gmail.com>
#          Marcus Uneson <marcus.uneson@gmail.com>
# URL: <http://nltk.org/>
# For license information, see  LICENSE.TXT

from __future__ import print_function
import abc

import yaml

from nltk.compat import python_2_unicode_compatible, unicode_repr

######################################################################
## Brill Rules
######################################################################


class BrillRule(yaml.YAMLObject):
    """
    An interface for tag transformations on a tagged corpus, as
    performed by brill taggers.  Each transformation finds all tokens
    in the corpus that are tagged with a specific original tag and
    satisfy a specific condition, and replaces their tags with a
    replacement tag.  For any given transformation, the original
    tag, replacement tag, and condition are fixed.  Conditions may
    depend on the token under consideration, as well as any other
    tokens in the corpus.

    Brill rules must be comparable and hashable.
    """

    def __init__(self, original_tag, replacement_tag):

        self.original_tag = original_tag
        """The tag which this BrillRule may cause to be replaced."""

        self.replacement_tag = replacement_tag
        """The tag with which this BrillRule may replace another tag."""

    def apply(self, tokens, positions=None):
        """
        Apply this rule at every position in positions where it
        applies to the given sentence.  I.e., for each position p
        in *positions*, if *tokens[p]* is tagged with this rule's
        original tag, and satisfies this rule's condition, then set
        its tag to be this rule's replacement tag.

        :param tokens: The tagged sentence
        :type tokens: list(tuple(str, str))
        :type positions: list(int)
        :param positions: The positions where the transformation is to
            be tried.  If not specified, try it at all positions.
        :return: The indices of tokens whose tags were changed by this
            rule.
        :rtype: int
        """
        if positions is None:
            positions = list(range(len(tokens)))

        # Determine the indices at which this rule applies.
        change = [i for i in positions if self.applies(tokens, i)]

        # Make the changes.  Note: this must be done in a separate
        # step from finding applicable locations, since we don't want
        # the rule to interact with itself.
        for i in change:
            tokens[i] = (tokens[i][0], self.replacement_tag)

        return change

    def applies(self, tokens, index):
        """
        :return: True if the rule would change the tag of
            ``tokens[index]``, False otherwise
        :rtype: bool
        :param tokens: A tagged sentence
        :type tokens: list(str)
        :param index: The index to check
        :type index: int
        """
        raise NotImplementedError

    # Rules must be comparable and hashable for the algorithm to work
    def __eq__(self, other):
        raise TypeError("Rules must implement __eq__()")
    def __ne__(self, other):
        raise TypeError("Rules must implement __ne__()")
    def __hash__(self):
        raise TypeError("Rules must implement __hash__()")


@python_2_unicode_compatible
class Rule(BrillRule):
    """
    A Rule checks the current corpus position for a certain set of conditions;
    if they are all fulfilled, the Rule is triggered, meaning that it
    will change tag A to tag B. For other tags than A, nothing happens.

    The conditions are parameters to the Rule instance. Each condition is a feature-value pair,
    with a set of positions to check for the value of the corresponding feature.
    Conceptually, the positions are joined by logical OR, and the feature set by logical AND.

    More formally, the Rule is then applicable to the M{n}th token iff:

      - The M{n}th token is tagged with the Rule's original tag; and
      - For each (Feature(positions), M{value}) tuple:
        - The value of Feature of at least one token in {n+p for p in positions}
          is M{value}.

    """
    yaml_tag = '!Rule'
    def __init__(self, templateid, original_tag, replacement_tag, conditions):
        """
        Construct a new Rule that changes a token's tag from
        C{original_tag} to C{replacement_tag} if all of the properties
        specified in C{conditions} hold.

        @type templateid: string
        @param templateid: the template id (a zero-padded string, '001' etc,
          so it will sort nicely)

        @type conditions: C{iterable} of C{Feature}
        @param conditions: A list of Feature(positions),
            each of which specifies that the property (computed by
            Feature.extract_property()) of at least one
            token in M{n} + p in positions is C{value}.

        """
        BrillRule.__init__(self, original_tag, replacement_tag)
        self._conditions = conditions
        self.templateid = templateid

    # Make Rules look nice in YAML.
    @classmethod
    def to_yaml(cls, dumper, data):
        d = dict(
            description=str(data),
            conditions=list(data._conditions),
            original=data.original_tag,
            replacement=data.replacement_tag,
            templateid=data.templateid)
        node = dumper.represent_mapping(cls.yaml_tag, d)
        return node

    @classmethod
    def from_yaml(cls, loader, node):
        map = loader.construct_mapping(node, deep=True)
        return cls(map['templateid'], map['original'], map['replacement'], map['conditions'])


    def applies(self, tokens, index):
        # Inherit docs from BrillRule

        # Does the given token have this Rule's "original tag"?
        if tokens[index][1] != self.original_tag:
            return False

        # Check to make sure that every condition holds.
        for (feature, val) in self._conditions:

            # Look for *any* token that satisfies the condition.
            for pos in feature.positions:
                if not (0 <= index + pos < len(tokens)):
                    continue
                if feature.extract_property(tokens, index+pos) == val:
                    break
            else:
                # No token satisfied the condition; return false.
                return False

        # Every condition checked out, so the Rule is applicable.
        return True

    def __eq__(self, other):
        return (self is other or
                (other is not None and
                 other.__class__ == self.__class__ and
                 self.original_tag == other.original_tag and
                 self.replacement_tag == other.replacement_tag and
                 self._conditions == other._conditions))

    def __ne__(self, other):
        return not (self==other)

    def __hash__(self):

        # Cache our hash value (justified by profiling.)
        try:
            return self.__hash
        except:
            self.__hash = hash(repr(self))
            return self.__hash

    def __repr__(self):
        # Cache the repr (justified by profiling -- this is used as
        # a sort key when deterministic=True.)
        try:
            return self.__repr
        except:
            self.__repr = ('%s(%r, %s, %s, [%s])' % (
                self.__class__.__name__,
                self.templateid,
                unicode_repr(self.original_tag),
                unicode_repr(self.replacement_tag),

                # list(self._conditions) would be simpler but will not generate
                # the same Rule.__repr__ in python 2 and 3 and thus break some tests
                ", ".join("({0:s},{1:s})".format(f,unicode_repr(v)) for (f,v) in self._conditions)))

            return self.__repr

    def __str__(self):
        def _condition_to_logic(feature, value):
            """
            Return a compact, predicate-logic styled string representation
            of the given condition.
            """
            return ('%s:%s@[%s]' %
                (feature.PROPERTY_NAME, value, ",".join(str(w) for w in feature.positions)))

        conditions = ' & '.join([_condition_to_logic(f,v) for (f,v) in self._conditions])
        s = ('%s->%s if %s' % (
            self.original_tag,
            self.replacement_tag,
            conditions))
        return s


    def format(self, fmt):
        """
        Return a string representation of this rule.

        >>> from nltk.tag.brill.rule import Rule
        >>> from nltk.tag.brill.task.postagging import Pos

        >>> r = Rule(23, "VB", "NN", [(Pos([-2,-1]), 'DT')])

        #r.format("str") == str(r)
        >>> r.format("str")
        'VB->NN if Pos:DT@[-2,-1]'

        #r.format("repr") == repr(r)
        >>> r.format("repr")
        "Rule(23, 'VB', 'NN', [(Pos([-2, -1]),'DT')])"

        >>> r.format("verbose")
        'VB -> NN if the Pos of words i-2...i-1 is "DT"'

        >>> r.format("not_found")
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
          File "nltk/tag/brill/rule.py", line 256, in format
            raise ValueError("unknown rule format spec: {0}".format(fmt))
        ValueError: unknown rule format spec: not_found
        >>>

        :param fmt: format specification
        :type fmt: str
        :return: string representation
        :rtype: str
        """
        if fmt == "str":
            return self.__str__()
        elif fmt == "repr":
            return self.__repr__()
        elif fmt == "verbose":
            return self._verbose_format()
        else:
            raise ValueError("unknown rule format spec: {0}".format(fmt))

    def _verbose_format(self):
        """
        Return a wordy, human-readable string representation
        of the given rule.

        Not sure how useful this is.
        """
        def condition_to_str(feature, value):
            return ('the %s of %s is "%s"' %
                    (feature.PROPERTY_NAME, range_to_str(feature.positions), value))

        def range_to_str(positions):
            if len(positions) == 1:
                p = positions[0]
                if p == 0:
                    return 'this word'
                if p == -1:
                    return 'the preceding word'
                elif p == 1:
                    return 'the following word'
                elif p < 0:
                    return 'word i-%d' % -p
                elif p > 0:
                    return 'word i+%d' % p
            else:
                # for complete compatibility with the wordy format of nltk2
                mx = max(positions)
                mn = min(positions)
                if mx - mn == len(positions) - 1:
                    return 'words i%+d...i%+d' % (mn, mx)
                else:
                    return 'words {%s}' % (",".join("i%+d" % d for d in positions),)

        replacement = '%s -> %s' % (self.original_tag, self.replacement_tag)
        conditions = (' if ' if self._conditions else "") + ', and '.join(
            [condition_to_str(f,v) for (f,v) in self._conditions])
        return replacement + conditions
