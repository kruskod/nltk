# Natural Language Toolkit: Taggers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@ldc.upenn.edu> (minor additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Classes and interfaces used to tag each token of a document with
supplementary information, such as its part of speech or its WordNet
synset tag.  Tagged tokens are represented by C{Token} objects whose
types are C{TaggedType} objects.  C{TaggedType}s consist of a base
type (the original token's type) and a tag.  A C{TaggedType} with base
M{b} and tag M{t} is written as M{b/m}.

A token M{tok} with tag M{type} is tagged by constructing a new token
whose type is M{type/tag}, where M{tag} is the appropriate tag value.
The new token's location is equal to M{tok}'s location.  To tag a
document, a new document is constructed, whose tokens are the result
of tagging the original document's tokens.  The tagger module defines
the C{TaggerI} interface for creating classes to tag documents.  It
also defines several different implementations of this interface,
providing a variety ways to tag documents.

The tagger module also defines the function C{parseTaggedType()} and
the tokenizer C{TaggedTokenizer}, for reading tagged tokens from
strings.

@group Data Types: TaggedType
@group Interfaces: TaggerI
@group Taggers: SequentialTagger, NN_CD_Tagger, UnigramTagger,
    NthOrderTagger, BackoffTagger
@group Tokenizers: TaggedTokenizer
@group Parsing: parseTaggedType
@group Evaluation: untag, accuracy
@sort: TaggedType, TaggedTokenizer, parseTaggedType, TaggerI, 
    SequentialTagger, NN_CD_Tagger, UnigramTagger, NthOrderTagger, 
    BackoffTagger, untag, accuracy

@todo 2.0: Add a Viterbi Tagger.
@todo 2.0: Rename
    C{SequentialTagger} to C{GreedySequentialTagger};
    C{UnigramTagger} to C{GreedyUnigramTagger}; 
    C{NthOrderTagger} to C{GreedyNthOrderTagger}; and 
    C{BackoffTagger} to C{GreedyBackoffTagger}.
"""

from nltk.chktype import chktype as _chktype
from nltk.chktype import classeq as _classeq
import types
from nltk.tokenizer import Token, TokenizerI, Location
import re
from nltk.probability import FreqDist, ConditionalFreqDist

##//////////////////////////////////////////////////////
##  TaggedType
##//////////////////////////////////////////////////////
class TaggedType:
    """
    An element of text that consists of a base type and a tag.  A
    typical example would be a part-of-speech tagged word, such as
    C{'bank'/'NN'}.  The base type and the tag are typically strings,
    but may be any immutable hashable objects.  Note that string base
    types and tags are case sensitive.

    @see: parseTaggedType
    @type _base: (any)
    @ivar _base: The base type of the C{TaggedType}.  This represents
        the type that is tagged.
    @type _tag: (any)
    @ivar _tag: The base type's tag.  This provides information about
        the base type, such as its part-of-speech.
    """
    def __init__(self, base, tag):
        """
        Construct a new C{TaggedType}

        @param base: The new C{TaggedType}'s base type.
        @param tag: The new C{TaggedType}'s tag.
        """
        self._base = base
        self._tag = tag
        
    def base(self):
        """
        @return: this C{TaggedType}'s base type.
        @rtype: (any)
        """
        return self._base
    
    def tag(self):
        """
        @return: this C{TaggedType}'s tag.
        @rtype: (any)
        """
        return self._tag
    
    def __eq__(self, other):
        """
        @return: true if this C{TaggedType} is equal to C{other}.  In
            particular, return true iff C{self.base()==other.base()}
            and C{self.tag()==other.tag()}.
        @raise TypeError: if C{other} is not a C{TaggedType}
        """
        return (_classeq(self, other) and
                self._base == other._base and
                self._tag == other._tag)

    def __ne__(self, other):
        return not (self == other)
    
    def __hash__(self):
        return hash( (self._base, self._tag) )
    
    def __repr__(self):
        """
        @return: a concise representation of this C{TaggedType}.
        @rtype: string
        """
        return repr(self._base)+'/'+repr(self._tag)

##//////////////////////////////////////////////////////
##  Parsing and Tokenizing TaggedTypes
##//////////////////////////////////////////////////////
def parse_tagged_type(string):
    """
    Parse a string into a C{TaggedType}.  The C{TaggedType}'s base
    type will be the substring preceeding the first '/', and the
    C{TaggedType}'s tag will be the substring following the first
    '/'.  If the input string contains no '/', then the base type will
    be the input string and the tag will be C{None}.

    @param string: The string to parse
    @type string: {string}
    @return: The C{TaggedType} represented by C{string}
    @rtype: C{TaggedType}
    """
    assert _chktype(1, string, types.StringType)
    elts = string.split('/')
    if len(elts) > 1:
        return TaggedType('/'.join(elts[:-1]), elts[-1].upper())
    else:
        return TaggedType(string, None)

class TaggedTokenizer(TokenizerI):
    """
    A tokenizer that splits a string of tagged text into tokens.  Each
    tagged token is encoded as a C{Token} whose type is a
    C{TaggedType}.  Location indices start at zero, and have a default
    unit of C{'w'}.

    The string is split into words using whitespace, and each word
    should have the form C{I{type}/I{tag}}, where C{I{type}} is the
    base type for the token, and C{I{tag}} is the tag for the token.
    Words that do not contain a slash are ignored.

      >>> tt = TaggedTokenizer()
      >>> tt.tokenize('The/DT dog/NN saw/VBD him/PRP')
      ['The'/'DT'@[0w], 'dog'/'NN'@[1w],
       'saw'/'VBD'@[2w], 'him'/'PRP'@[3w]]
    """
    def __init__(self): pass
    def tokenize(self, str, unit='w', source=None):
        # Inherit docs from TokenizerI
        assert _chktype(1, str, types.StringType)
        words = str.split()
        tokens = []
        index = 0
        for word in words:
            toktype = parse_tagged_type(word)
            if toktype.tag() is not None:
                tokloc = Location(index, unit=unit, source=source)
                tokens.append(Token(toktype, tokloc))
                index += 1
        return tokens

##//////////////////////////////////////////////////////
##  Tagger Interface
##//////////////////////////////////////////////////////
class TaggerI:
    """
    A processing interface for assigning a tag to each token in an
    ordered list of tokens.  Taggers are required to define one
    function, C{tag}, which tags a list of C{Token}s.
    
    Classes implementing the C{TaggerI} interface may choose to only
    support certain classes of tokens for input.  If a method is
    unable to return a correct result because it is given an
    unsupported class of token, then it should raise a
    NotImplementedError.
    """
    def __init__(self):
        """
        Construct a new C{Tagger}.
        """
        assert 0, "TaggerI is an abstract interface"
        
    def tag(self, tokens):
        """
        Assign a tag to each token in an ordered list of tokens, and
        return the resulting list of tagged tokens.  In particular,
        return a list C{out} where:

            - C{len(tokens)} = C{len(out)}
            - C{out[i].type} = C{TaggedType(tokens[i].type, M{tag})}
                for some C{M{tag}}.
            - C{out[i].loc()} = C{tokens[i].loc()}

        @param tokens: The list of tokens to be tagged.
        @type tokens: C{list} of C{Token}
        @return: The tagged list of tokens.
        @returntype: C{list} of C{Token}
        """
        assert 0, "TaggerI is an abstract interface"

##//////////////////////////////////////////////////////
##  Taggers
##//////////////////////////////////////////////////////
class SequentialTagger(TaggerI):
    """
    An abstract base class for taggers that assign tags to tokens in
    sequential order.  In particular, X{sequential taggers} are
    taggers that:

        - Assign tags to one token at a time, starting with the first
          token of the text, and proceeding in sequential order.
        - Decide which tag to assign a token on the basis of that
          token, the tokens that preceed it, and the predicted tags of
          the tokens that preceed it.

    Each C{SequentialTagger} subclass defines the C{next_tag} method,
    which returns the tag for a token, given the list of tagged tokens
    that preceeds it.  The C{tag} method calls C{next_tag} once for
    each token, and uses the return values to construct the tagged
    text.
    """
    def __init__(self, lookbehind_window = 0, lookahead_window = 0):
        """
        Construct a C{SequentialTagger}. The two parameters constrain the
        size of the look behind and look ahead windows. Only the tokens
        that fit within this window of the current token to tag are
        supplied to the C{next_tag} function. All tokens in the look
        behind window will contain a C{TaggedType}, and all tokens in the
        look ahead window will not.
        
        @type lookbehind_window: C{int}
        @param lookbehind_window: The number of tagged tokens to provide
            as look-behind context to the C{next_tag} function.  Must be
            a positive number.
        @type lookahead_window: C{int}
        @param lookahead_window: The number of tokens to provide
            as look-ahead context to the C{next_tag} function. Must be a
            positive number.
        """
        assert _chktype(1, lookbehind_window, types.IntType)
        assert lookbehind_window >= 0, 'window size must be positive'
        assert _chktype(2, lookahead_window, types.IntType)
        assert lookahead_window >= 0, 'window size must be positive'
        self._lookbehind_window = lookbehind_window
        self._lookahead_window = lookahead_window

    def lookbehind_window(self):
        """
        @rtype: C{int}
        @return: The size of the look-behind window.
        """
        return self._lookbehind_window

    def lookahead_window(self):
        """
        @rtype: C{int}
        @return: The size of the look-ahead window.
        """
        return self._lookahead_window
    
    def next_tag(self, tagged_tokens, next_tokens):
        """
        Decide which tag to assign a token, given the list of tagged
        tokens that preceeds it.

        @type tagged_tokens: C{list} of tagged C{Token}
        @param tagged_tokens: A list of the tagged tokens that preceed
            C{token}.  The tokens' base types are taken from the text
            being tagged, and their tags are prediced by previous
            calls to C{next_tag}. This list is trimmed to the size of the
            look-behind window, such that the I{n}th element
            of C{tagged_tokens} is a tagged token whose base type is
            equal to the type of the I{n}th element within the window;
            whose location is equal to the location of the I{n}th element
            within the window; and whose tag is a predicted tag returned
            by a previous call to C{next_tag}.
        @type next_tokens: C{list} of C{Token}
        @param next_tokens: The (untagged) tokens, the first for which to
            assign a tag. The remaining tokens form the look-ahead
            window -- the following I{n} tokens in the text.
        @rtype: tag
        @return: the most likely tag for the first token in
            C{next_tokens}, given that it is preceeded by
            C{tagged_tokens} and followed by the remainder of
            C{next_tokens}.
        """
        assert 0, "next_tag not defined by SequentialTagger subclass"

    def tag(self, tokens):
        # Inherit documentation
        assert _chktype(1, tokens, [Token], (Token,))

        # Tag each token, in sequential order.
        rear_window = []
        front_window = tokens[:self._lookahead_window + 1]
        tagged_text = []
        for index in xrange(len(tokens)):
            token = tokens[index]

            # Get the tag for the next token.
            if self._lookbehind_window > 0:
                rear_window = tagged_text[-self._lookbehind_window:]
            tag = self.next_tag(rear_window, front_window)

            # Construct a tagged token with the given tag, and add it
            # to the end of rear_window.
            tagged_token = Token(TaggedType(token.type(), tag), token.loc())
            tagged_text.append(tagged_token)

            # maintain front_window
            del front_window[0]
            if index + self._lookahead_window + 1 < len(tokens):
                front_window.append(tokens[index + self._lookahead_window + 1])

        return tagged_text

class NN_CD_Tagger(SequentialTagger):
    """
    A "default" tagger, which will assign the tag C{"CD"} to numbers,
    and C{"NN"} to anything else.  This tagger expects token types to
    be C{strings}s.
    """
    def __init__(self): 
        SequentialTagger.__init__(self, 0, 0) # window of (0, 0)

    def next_tag(self, tagged_tokens, next_tokens):
        # Inherit docs from SequentialTagger
        assert _chktype(1, tagged_tokens, [Token], (Token,))
        assert _chktype(2, next_tokens, [Token], (Token,))
        
        if re.match(r'^[0-9]+(.[0-9]+)?$', next_tokens[0].type()):
            return 'CD'
        else:
            return 'NN'

class UnigramTagger(SequentialTagger):
    """
    A unigram stochastic tagger.  Before a C{UnigramTagger} can be
    used, it should be trained on a list of C{TaggedToken}s.  Using
    this training data, it will find the most likely tag for each word
    type.  It will then use this information to assign the most
    frequent tag to each word.  If the C{NthOrderTagger} encounters a
    word in a context for which it has no data, it will assign it the
    tag C{None}.
    """
    def __init__(self):
        SequentialTagger.__init__(self, 0, 0) # window of (0, 0)
        self._freqdist = ConditionalFreqDist()
    
    def train(self, tagged_tokens):
        """
        Train this C{UnigramTagger} using the given training data.  If
        this method is called multiple times, then the training data
        will be combined.
        
        @param tagged_tokens: The training data.
        @type tagged_tokens: list of TaggedToken
        @returntype: None
        """
        assert _chktype(1, tagged_tokens, [Token], (Token,))
        for token in tagged_tokens:
            context = token.type().base()
            feature = token.type().tag()
            self._freqdist[context].inc(feature)

    def next_tag(self, tagged_tokens, next_tokens):
        # Inherit docs from SequentialTagger
        assert _chktype(1, tagged_tokens, [Token], (Token,))
        assert _chktype(2, next_tokens, [Token], (Token,))

        # Find the most likely tag for the token's type.
        context = next_tokens[0].type()
        return self._freqdist[context].max()
    
class NthOrderTagger(SequentialTagger):
    """
    An I{n}-th order stochastic tagger.  Before an C{NthOrderTagger}
    can be used, it should be trained on a list of C{TaggedToken}s.
    Using this list, it will construct a frequency distribution
    describing the frequencies with each word is tagged in different
    contexts.  The context considered consists of the word to be
    tagged and the I{n} previous words' tags.  Once it has constructed
    this frequency distribution, it uses it to tag words by assigning
    each word the tag with the maximum frequency given its context.
    If the C{NthOrderTagger} encounters a word in a context for which
    it has no data, it will assign it the tag C{None}.
    """
    def __init__(self, n):
        """
        Construct a new I{n}-th order stochastic tagger.  The
        new tagger should be trained, using the train() method, before
        it is used to tag data.
        
        @param n: The order of the new C{NthOrderTagger}.
        @type n: int
        """
        assert _chktype(1, n, types.IntType)
        if n < 0: raise ValueError('n must be non-negative')
        SequentialTagger.__init__(self, n, 0) # window of (n, 0)
        self._n = n
        self._freqdist = ConditionalFreqDist()

    def train(self, tagged_tokens):
        """
        Train this C{NthOrderTagger} using the given training data.
        If this method is called multiple times, then the training
        data will be combined.
        
        @param tagged_tokens: The training data.
        @type tagged_tokens: list of TaggedToken
        @returntype: None
        """
        assert _chktype(1, tagged_tokens, [Token], (Token,))
        # prev_tags is a list of the previous n tags that we've assigned.
        prev_tags = []

        for token in tagged_tokens:
            context = tuple(prev_tags + [token.type().base()])
            feature = token.type().tag()
            self._freqdist[context].inc(feature)

            # Update prev_tags
            prev_tags.append(token.type().tag())
            if len(prev_tags) == (self._n+1):
                del prev_tags[0]

    def next_tag(self, tagged_tokens, next_tokens):
        # Inherit docs from SequentialTagger
        assert _chktype(1, tagged_tokens, [Token], (Token,))
        assert _chktype(2, next_tokens, [Token], (Token,))

        # Find the tags of the n previous tokens.
        prev_tags = []
        start = max(len(tagged_tokens) - self._n, 0)
        for token in tagged_tokens[start:]:
            prev_tags.append(token.type().tag())

        # Return the most likely tag for the token's context.
        context = tuple(prev_tags + [next_tokens[0].type()])
        return self._freqdist[context].max()

class BackoffTagger(SequentialTagger):
    """
    A C{Tagger} that tags tokens using a basic backoff model.  Each
    C{BackoffTagger} is paramatrised by an ordered list sub-taggers.
    In order to assign a tag to a token, each of these sub-taggers is
    consulted in order.  If a sub-tagger is unable to determine a tag
    for the given token, it should use assign the special tag C{None}.
    Each token is assigned the first non-C{None} tag returned by a
    sub-tagger.

    This tagger expects a list of C{Token}s as its input, and
    generates a list of C{TaggedToken}s as its output.  Each
    sub-tagger should accept a list a list of C{Token}s as its input,
    and should generate a list of C{TaggedToken}s as its output.
    """
    def __init__(self, subtaggers):
        """
        Construct a new C{BackoffTagger}, from the given
        list of sub-taggers.
        
        @param subtaggers: The list of sub-taggers used by this
               C{BackoffTagger}.  These sub-taggers will be
               consulted in the order in which they appear in the
               list.
        @type subtaggers: list of SequentialTagger
        """
        assert _chktype(1, subtaggers, (SequentialTagger,), [SequentialTagger])
        self._subtaggers = subtaggers

        # calculate the look-behind & look-ahead windows
        max_lookbehind = 0
        max_lookahead = 0
        for subtagger in self._subtaggers:
            max_lookbehind = max(max_lookbehind, subtagger.lookbehind_window())
            max_lookahead = max(max_lookahead, subtagger.lookahead_window())
        SequentialTagger.__init__(self, max_lookbehind, max_lookahead)

    def next_tag(self, tagged_tokens, next_tokens):
        # Inherit docs from SequentialTagger
        assert _chktype(1, tagged_tokens, [Token], (Token,))
        assert _chktype(2, next_tokens, [Token], (Token,))

        for subtagger in self._subtaggers:
            tag = subtagger.next_tag(tagged_tokens, next_tokens)
            if tag is not None:
                return tag

        # Default to None if all subtaggers return None.
        return None

##//////////////////////////////////////////////////////
##  Evaluation
##//////////////////////////////////////////////////////
def untag(tagged_tokens):
    """
    Given a list of tagged tokens, return a list of tokens constructed
    from the tagged tokens' base types and locations.  In particular,
    if C{tagged_tokens} = [I{ttok_1}, ..., I{ttok_n}], return a
    list of tokens [I{tok_1}, ..., I{tok_n}], where I{tok_i}.loc() ==
    I{ttok_i}.loc() and I{tok_i}.type() == I{ttok_i}.type.base().

    @param tagged_tokens: The list of tokens to transform.
    @type tagged_tokens: C{list} of C{TaggedToken}
    @return: A list of tokens constructed from the C{tagged_tokens}'
        base types and locations.
    @rtype: C{list} of C{Token}
    """
    assert _chktype(1, tagged_tokens, [Token], (Token,))
    return [Token(t.type().base(), t.loc()) for t in tagged_tokens]

def accuracy(orig, test):
    """
    Test the accuracy of a tagged text, with respect the correct
    tagging.  This accuracy is defined as the percentage of tokens
    tagged correctly.  Note that C{orig} and C{test} should be the
    same length, and should contain tokens with corresponding base
    types and locations; otherwise, C{test} is not a valid tagging of
    C{orig}.

    @param orig: The original (correctly-tagged) text.  This is the
        "gold standard" against which C{test} is compared.
    @type orig: C{list} of C{TaggedToken}
    @param test: The tagging whose accuracy you wish to test.
    @type test: C{list} of C{TaggedToken}
    """
    assert _chktype(1, test, [Token], (Token,))
    assert _chktype(2, orig, [Token], (Token,))
    if len(orig) != len(test):
        raise ValueError('Invalid Tagging')

    correct = 0
    for i in range(len(orig)):
        if orig[i] == test[i]: correct += 1
    return float(correct)/len(orig)

##//////////////////////////////////////////////////////
##  Demonstration
##//////////////////////////////////////////////////////

def demo(num_files=20):
    """
    A simple demonstration function for the C{Tagger} classes.  It
    constructs a C{BackoffTagger} using a 2nd order C{NthOrderTagger},
    a 1st order C{NthOrderTagger}, a 0th order C{NthOrderTagger}, and
    an C{NN_CD_Tagger}.  It trains and tests the tagger using the
    brown corpus.

    @type num_files: C{int}
    @param num_files: The number of files that should be used for
        training and for testing.  Two thirds of these files will be
        used for training.  All files are randomly selected
        (I{without} replacement) from the brown corpus.  If
        C{num_files>=500}, then all 500 files will be used.
    @rtype: None
    """
    from nltk.corpus import brown
    import sys, random
    num_files = max(min(num_files, 500), 3)

    # Get a randomly sorted list of files in the brown corpus.
    items = list(brown.items())
    random.shuffle(items)

    # Tokenize the training files.
    sys.stdout.write('Reading training data'); sys.stdout.flush()
    train_tokens = []
    for item in items[:num_files*2/3]:
        sys.stdout.write('.'); sys.stdout.flush()
        train_tokens += brown.tokenize(item)
    print '\nRead in %s training tokens' % len(train_tokens)

    # Create a default tagger
    default_tagger = NN_CD_Tagger()

    print 'training unigram tagger...'
    t0 = UnigramTagger()
    t0.train(train_tokens)

    print 'training bigram tagger...'
    t1 = NthOrderTagger(1)                
    t1.train(train_tokens)

    print 'training trigram tagger...'
    t2 = NthOrderTagger(2) 
    t2.train(train_tokens)

    print 'creating combined backoff tagger...'
    bt = BackoffTagger( [t2, t1, t0, default_tagger] )

    # Delete train_tokens, because it takes up lots of memory.
    del train_tokens
    
    # Tokenize the testing files
    test_tokens = []
    sys.stdout.write('Reading testing data'); sys.stdout.flush()
    for item in items[num_files*2/3:num_files]:
        sys.stdout.write('.'); sys.stdout.flush()
        test_tokens += brown.tokenize(item)
    print '\nRead in %s testing tokens' % len(test_tokens)

    # Run the taggers.  For t0, t1, and t2, back-off to NN_CD_Tagger.
    # This is especially important for t1 and t2, which count on
    # having known tags as contexts; if they get a context containing
    # None, then they will generate an output of None, and so all
    # words will get tagged a None.
    print 'running the taggers...'
    print 'Correct tagger results:  ' + `test_tokens`[:48] + '...'
    result = default_tagger.tag(untag(test_tokens))
    print 'Default tagger results:  ' + `result`[:48] + '...'
    print 'Default tagger accuracy: %.5f' % accuracy(test_tokens, result)
    result = BackoffTagger([t0, default_tagger]).tag(untag(test_tokens))
    print 'Unigram tagger results:  ' + `result`[:48] + '...'
    print 'Unigram tagger accuracy: %.5f' % accuracy(test_tokens, result)
    result = BackoffTagger([t1, default_tagger]).tag(untag(test_tokens))
    print 'Bigram tagger results:   ' + `result`[:48] + '...'
    print 'Bigram tagger accuracy:  %.5f' % accuracy(test_tokens, result)
    result = BackoffTagger([t2, default_tagger]).tag(untag(test_tokens))
    print 'Trigram tagger results:  ' + `result`[:48] + '...'
    print 'Trigram tagger accuracy: %.5f' % accuracy(test_tokens, result)
    result = bt.tag(untag(test_tokens))
    print 'Backoff tagger results:  ' + `result`[:48] + '...'
    print 'Backoff tagger accuracy: %.5f' % accuracy(test_tokens, result)

if __name__ == '__main__':
    # Standard boilerpate.  (See note in <http://?>)
    from nltk.tagger import *
    demo()
