# Natural Language Toolkit: Tagged Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
A reader for corpora whose documents contain part-of-speech-tagged
words.
"""       

from api import *
from util import *
from nltk.tag import string2tags, string2words
from nltk import tokenize
import os

class TaggedCorpusReader(CorpusReader):
    """
    Reader for simple part-of-speech tagged corpora.  Paragraphs are
    assumed to be split using blank lines.  Sentences and words can be
    tokenized using the default tokenizers, or by custom tokenizers
    specificed as parameters to the constructor.  Words are parsed
    using L{nltk.tag.string2tags}.  By default, C{'/'} is used as the
    separator.  I.e., words should have the form::

       word1/tag1 word2/tag2 word3/tag3 ...

    But custom separators may be specified as parameters to the
    constructor.  Part of speech tags are case-normalized to upper
    case.
    """
    def __init__(self, root, items, extension='',
                 sep='/', word_tokenizer=tokenize.whitespace,
                 sent_tokenizer=tokenize.line):
        """
        Construct a new Tagged Corpus reader for a set of documents
        located at the given root directory.  Example usage:

            >>> root = '/...path to corpus.../'
            >>> reader = TaggedCorpusReader(root, '.*', '.txt')
        
        @param root: The root directory for this corpus.
        @param items: A list of items in this corpus.  This list can
            either be specified explicitly, as a list of strings; or
            implicitly, as a regular expression over file paths.  The
            filename for each item will be constructed by joining the
            reader's root to the filename, and adding the extension.
        @param extension: File extension for items in this corpus.
            This extension will be concatenated to item names to form
            file names.  If C{items} is specified as a regular
            expression, then the escaped extension will automatically
            be added to that regular expression.
        """
        if not os.path.isdir(root):
            raise ValueError('Root directory %r not found!' % root)
        self._items = items
        self._root = root
        self._extension = extension
        self._sep = sep
        self._word_tokenizer = word_tokenizer
        self._sent_tokenizer = sent_tokenizer

    @property
    def root(self):
        """The directory where this corpus is stored.."""
        return self._root

    @property
    def items(self):
        """A list of the documents in this corpus"""
        items = self._items
        if isinstance(items, basestring):
            items = find_corpus_items(self._root, items, self._extension)
        self.__dict__['items'] = tuple(items)
        return self.items
            
    def raw(self, items=None):
        """
        @return: the given document or documents as a single string.
        @rtype: C{str}
        """
        return concat([open(filename).read()
                       for filename in self._item_filenames(items)])

    def words(self, items=None):
        """
        @return: the given document or documents as a list of words
            and punctuation symbols.
        @rtype: C{list} of C{str}
        """
        return concat([TaggedCorpusView(filename, False, False, False,
                                        self._sep, self._word_tokenizer,
                                        self._sent_tokenizer)
                       for filename in self._item_filenames(items)])

    def sents(self, items=None):
        """
        @return: the given document or documents as a list of
            sentences or utterances, each encoded as a list of word
            strings.
        @rtype: C{list} of (C{list} of C{str})
        """
        return concat([TaggedCorpusView(filename, False, True, False,
                                        self._sep, self._word_tokenizer,
                                        self._sent_tokenizer)
                       for filename in self._item_filenames(items)])

    def paras(self, items=None):
        """
        @return: the given document or documents as a list of
            paragraphs, each encoded as a list of sentences, which are
            in turn encoded as lists of word strings.
        @rtype: C{list} of (C{list} of (C{list} of C{str}))
        """
        return concat([TaggedCorpusView(filename, False, True, True,
                                        self._sep, self._word_tokenizer,
                                        self._sent_tokenizer)
                       for filename in self._item_filenames(items)])

    def tagged_words(self, items=None):
        """
        @return: the given document or documents as a list of tagged
            words and punctuation symbols, encoded as tuples
            C{(word,tag)}.
        @rtype: C{list} of C{(str,str)}
        """
        return concat([TaggedCorpusView(filename, True, False, False,
                                        self._sep, self._word_tokenizer,
                                        self._sent_tokenizer)
                       for filename in self._item_filenames(items)])

    def tagged_sents(self, items=None):
        """
        @return: the given document or documents as a list of
            sentences, each encoded as a list of C{(word,tag)} tuples.
            
        @rtype: C{list} of (C{list} of C{(str,str)})
        """
        return concat([TaggedCorpusView(filename, True, True, False,
                                        self._sep, self._word_tokenizer,
                                        self._sent_tokenizer)
                       for filename in self._item_filenames(items)])

    def tagged_paras(self, items=None):
        """
        @return: the given document or documents as a list of
            paragraphs, each encoded as a list of sentences, which are
            in turn encoded as lists of C{(word,tag)} tuples.
        @rtype: C{list} of (C{list} of (C{list} of C{(str,str)}))
        """
        return concat([TaggedCorpusView(filename, True, True, True,
                                        self._sep, self._word_tokenizer,
                                        self._sent_tokenizer)
                       for filename in self._item_filenames(items)])

    def _item_filenames(self, items):
        if items is None: items = self.items
        if isinstance(items, basestring): items = [items]
        return [os.path.join(self._root, '%s%s' % (item, self._extension))
                for item in items]
    
class TaggedCorpusView(StreamBackedCorpusView):
    """
    A specialized corpus view for tagged documents.  It can be
    customized via flags to divide the tagged corpus documents up by
    sentence or paragraph, and to include or omit part of speech tags.
    C{TaggedCorpusView} objects are typically created by
    L{TaggedCorpusReader} (not directly by nltk users).
    """
    def __init__(self, corpus_file, tagged, group_by_sent, group_by_para,
                 sep, word_tokenizer, sent_tokenizer):
        self._tagged = tagged
        self._group_by_sent = group_by_sent
        self._group_by_para = group_by_para
        self._sep = sep
        self._word_tokenizer = word_tokenizer
        self._sent_tokenizer = sent_tokenizer
        StreamBackedCorpusView.__init__(self, corpus_file)
        
    def read_block(self, stream):
        """Reads one paragraph at a time."""
        block = []
        for para_str in read_blankline_block(stream):
            para = []
            for sent_str in self._sent_tokenizer(para_str):
                if self._tagged:
                    sent = string2tags(sent_str, self._sep)
                else:
                    sent = string2words(sent_str, self._sep)
                if self._group_by_sent:
                    para.append(sent)
                else:
                    para.extend(sent)
            if self._group_by_para:
                block.append(para)
            else:
                block.extend(para)
        return block

######################################################################
#{ Demo
######################################################################

def demo():
    from nltk.corpus import brown
    import textwrap
    def show(hdr, info):
        print hdr, textwrap.fill(info, initial_indent=' '*len(hdr),
                                 subsequent_indent=' '*4)[len(hdr):]
    
    d1 = brown.sents('a')
    for sent in d1[3:5]:
        show('Sentence from a:', ' '.join(sent))

    d2 = brown.tagged_words('b')
    show('Tagged words from b:', ' '.join('%s/%s' % w for w in d2[220:240]))
                       
    d3 = brown.words('c')
    show('Untagged words from c:', ' '.join(d3[220:250]))

if __name__ == '__main__':
    demo()

