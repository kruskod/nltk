# -*- coding: utf-8 -*-
# Natural Language Toolkit: Twitter client
#
# Copyright (C) 2001-2014 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
NLTK Twitter client.
"""
import datetime
import itertools
import json
import os

try:
    from twython import Twython, TwythonStreamer
except ImportError as e:
    e.msg = """The twitterclient module requires the Twython
    package. See https://twython.readthedocs.org/ for installation
    instructions."""
    raise

from api import TweetHandlerI
from util import credsfromfile


class Streamer(TwythonStreamer):
    """
    Retrieve data from the Twitter streaming API.

    The streaming API requires OAuth 1.0 authentication.
    """
    def __init__(self, handler, app_key, app_secret, oauth_token,
                 oauth_token_secret):
        self.handler = handler
        self.do_continue = True
        super().__init__(app_key, app_secret, oauth_token, oauth_token_secret)

    def register(self, handler):
        self.handler = handler

    def on_success(self, data):
        """
        :param data: response from Twitter API
        """
        if self.do_continue:
            if self.handler is not None:
                if 'text' in data:
                    self.do_continue = self.handler.handle(data)
            else:
                raise ValueError("No data handler has been registered.")
        else:
            self.disconnect()


    def on_error(self, status_code, data):
        """
        :param data: response from Twitter API
        """
        print(status_code)



class Query(Twython):
    """
    Class for accessing the Twitter REST API.
    """
    def __init__(self, handler, app_key, app_secret, oauth_token,
                 oauth_token_secret):
        self.handler = handler
        self.do_continue = True
        super().__init__(app_key, app_secret, oauth_token, oauth_token_secret)

    def register(self, handler):
        self.handler = handler

    def _lookup(self, infile, verbose=True):
        """
        :param infile: name of a file consisting of Tweet IDs, one to a line
        :return: iterable of Tweet objects
        """
        with open(infile) as f:
            ids = [line.rstrip() for line in f]
        if verbose:
            print("Counted {} Tweet IDs in {}.".format(len(ids), infile))

        id_chunks = [ids[i:i+100] for i in range(0, len(ids), 100)]
        """
        The Twitter endpoint takes lists of up to 100 ids, so we chunk
        the ids.
        """

        listoflists = [self.post('statuses/lookup', {'id': chunk}) for chunk
                       in id_chunks]
        return itertools.chain.from_iterable(listoflists)


    def lookup(self, infile, outfile, verbose=True):
        """
        Given a file containing a list of Tweet IDs, fetch the corresponding
        Tweets (if they haven't been deleted) and dump them in a file.

        :param infile: name of a file consisting of Tweet IDs, one to a line

        :param outfile: name of file where JSON serialisations of fully
        hydrated Tweets will be written.
        """
        tweets = self._lookup(infile, verbose=verbose)
        count = 0

        if os.path.isfile(outfile):
            os.remove(outfile)

        with open(outfile, 'a') as f:
            for data in tweets:
                json.dump(data, f)
                f.write("\n")
                count += 1

        if verbose:
            print("""Written {} Tweets to file {} of length {}
            bytes""".format(count, outfile, os.path.getsize( outfile)))

    def search(self, query, count=100, lang='en'):
        """
        Call the REST API 'search/tweets' endpoint with some plausible defaults.
        """
        results = self.search(q=query, count=100, lang='en')
        return results['statuses']




class Twitter(object):
    """
    Wrapper class with severely restricted functionality.
    """
    def __init__(self):
        self._oauth = credsfromfile()
        self.streamer = Streamer(None, **self._oauth)
        self.query = Query(None, **self._oauth)


    def tweets(self, keywords='', follow='', stream=True, limit=100):
        handler = TweetViewer(limit=limit)
        if stream:
            self.streamer.register(handler)
            if keywords=='' and follow=='':
                self.streamer.statuses.sample()
            else:
                self.streamer.statuses.filter(track=keywords, follow=follow)
        else:
            self.query.register(handler)
            if keywords != '':
                tweets = self.query.search(keywords)
                for t in tweets:
                    print(t['text'])




    def tofile(self, keywords='', track='', stream=True, limit=100):
        pass




class TweetViewer(TweetHandlerI):
    """
    Handle data by sending it to the terminal.
    """
    def handle(self, data):
        """
        Direct data to `sys.stdout`

        :return: return False if processing should cease, otherwise return
        True.
        :rtype: boolean
        :param data: Tweet object returned by Twitter API
        """
        text = data['text']
        print(text)
        self.counter += 1
        if self.counter >= self.limit:
            # Tell the client to disconnect
            return False
        return True


class TweetWriter(TweetHandlerI):
    """
    Handle data by writing it to a file.
    """
    def __init__(self, limit=2000, repeat=True, fprefix='tweets',
                 subdir='streamed_data'):
        """
        :param limit: number of data items to process in the current round of
        processing

        """
        self.repeat = repeat
        self.fprefix = fprefix
        self.subdir = subdir
        self.fname = self.timestamped_file()
        self.startingup = True
        super().__init__(limit)


    def timestamped_file(self):
        """
        :return: timestamped file name
        :rtype: str
        """
        subdir = self.subdir
        fprefix = self.fprefix
        if subdir:
            if not os.path.exists(subdir):
                os.mkdir(subdir)

        fname = os.path.join(subdir, fprefix)
        fmt = '%Y%m%d-%H%M%S'
        timestamp = datetime.datetime.now().strftime(fmt)
        outfile = '{0}.{1}.json'.format(fname, timestamp)
        return outfile


    def handle(self, data):
        """
        Write Twitter data as line-delimited JSON into one or more files.

        :return: return False if processing should cease, otherwise return True.
        :param data: Tweet object returned by Twitter API
        """
        if self.startingup:
            self.output = open(self.fname, 'w')
            print('Writing to {}'.format(self.fname))
        json_data = json.dumps(data)
        self.output.write(json_data + "\n")

        self.startingup = False
        self.counter += 1
        if self.counter < self.limit:
            return True
        else:
            print('Written {} tweets'.format(self.counter))
            self.output.close()
            if not self.repeat:
                "Tell the client to disconnect"
                return False
            else:
                self.fname = self.timestamped_file()
                self.output = open(self.fname, 'w')
                self.counter = 0
                print('\nWriting to new file {}'.format(self.fname))
                return True



################################
# Demos
################################

import os
TWITTER = os.environ['TWITTER']
TWEETS = os.path.join(TWITTER, 'tweets.20140801-150110.json')
IDS = os.path.join(TWITTER, 'tweet_ids.txt')
IDS2 = os.path.join(TWITTER, 'tweet_ids2.txt')
REHYDE = os.path.join(TWITTER, 'rehydrated.json')

def sampletoscreen_demo(limit=20):
    oauth = credsfromfile()
    handler = TweetViewer(limit=limit)
    client = Streamer(handler, **oauth)
    client.statuses.sample()

def tracktoscreen0_demo(limit=10):
    oauth = credsfromfile()
    handler = TweetViewer(limit=limit)
    client = Streamer(handler, **oauth)
    keywords = "Pistorius, #OscarTrial, gerrie nel"
    client.statuses.filter(track=keywords)

def tracktoscreen1_demo(limit=50):
    oauth = credsfromfile()
    handler = TweetViewer(limit=limit)
    client = Streamer(handler, **oauth)
    client.statuses.filter(follow='759251,612473,788524,15108530')

def streamtofile_demo(limit=20):
    oauth = credsfromfile()
    handler = TweetWriter(limit=limit, repeat=True)
    client = Streamer(handler, **oauth)
    client.statuses.sample()

def dehydrate_demo(infile, outfile):
    ids = dehydrate(infile)
    with open(outfile, 'w') as f:
        for id_str in ids:
            print(id_str, file=f)

def hydrate_demo(infile, outfile):
    oauth = credsfromfile()
    client = Query(**oauth)
    client.lookup(infile, outfile)

def corpusreader_demo():
    from nltk.corpus import TwitterCorpusReader
    root = os.environ['TWITTER']
    reader = TwitterCorpusReader(root, '.*\.json')
    for t in reader.full_tweets()[:2]:
        print(t)

    for t in reader.tweets()[:15]:
        print(t)

    for t in reader.tokenised_tweets()[:15]:
        print(t)


def search_demo():
    oauth = credsfromfile()
    client = Query(**oauth)
    s = client.search(q='nltk', count=100)
    for t in client.search(q='nltk', count=100)['statuses']:
        print(t['text'])


def twitterclass_demo():
    tw = Twitter()
    tw.tweets()


DEMOS = [6]

if __name__ == "__main__":
    #import doctest
    #doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)

    if 0 in DEMOS:
        tracktoscreen1_demo()
    if 1 in DEMOS:
        streamtofile_demo()
    if 2 in DEMOS:
        dehydrate_demo(TWEETS, IDS)
    if 3 in DEMOS:
        hydrate_demo(IDS, REHYDE)
    if 4 in DEMOS:
        corpusreader_demo()
    if 5 in DEMOS:
        search_demo()
    if 6 in DEMOS:
        twitterclass_demo()




