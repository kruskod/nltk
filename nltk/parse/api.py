# Natural Language Toolkit: Parser API
#
# Copyright (C) 2001-2014 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#         Edward Loper <edloper@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
#

import itertools

from nltk.internals import overridden

class ParserI(object):
    """
    A processing class for deriving trees that represent possible
    structures for a sequence of tokens.  These tree structures are
    known as "parses".  Typically, parsers are used to derive syntax
    trees for sentences.  But parsers can also be used to derive other
    kinds of tree structure, such as morphological trees and discourse
    structures.

    Subclasses must define:
      - at least one of: ``parse()``, ``parse_sents()``.

    Subclasses may define:
      - ``grammar()``
    """
    def grammar(self):
        """
        :return: The grammar used by this parser.
        """
        raise NotImplementedError()

    def parse(self, sent):
        """
        :return: An iterator that generates parse trees for the sentence.
        When possible this list is sorted from most likely to least likely.

        :param sent: The sentence to be parsed
        :type sent: list(str)
        :rtype: iter(Tree)
        """
        if overridden(self.parse_sents):
            return self.parse_sents([sent])[0]
        elif overridden(self.parse):
            return self.parse(sent)
        else:
            raise NotImplementedError()

    def parse_sents(self, sents):
        """
        Apply ``self.parse()`` to each element of ``sents``.
        :rtype: list(iter(Tree))
        """
        return [self.parse(sent) for sent in sents]


