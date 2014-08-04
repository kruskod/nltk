# Natural Language Toolkit: Twitter client
#
# Copyright (C) 2001-2014 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

import itertools
import json
import os
import datetime

from twython import Twython, TwythonStreamer


class Streamer(TwythonStreamer):
    """
    Retrieve data from the Twitter streaming API.

    The streaming API requires OAuth 1.0 authentication. 
    """
    def __init__(self, handler, app_key, app_secret, oauth_token, oauth_token_secret):
        self.handler = handler
        self.do_continue = True
        super().__init__(app_key, app_secret, oauth_token, oauth_token_secret)

    #def register(self, handler):
        #"""
        #Register a method of :py:class:`TweetHandler`.
        #"""
        #self.handler = handler

    def on_success(self, data):
        """
        :param data: response from Twitter API
        """
        if self.do_continue:
        #if self.handler is not None:
            if 'text' in data:
                self.do_continue = self.handler.handle(data)
        else:
            self.disconnect()
            #raise ValueError("No data handler has been registered.")

    def on_error(self, status_code, data):
        """
        :param data: response from Twitter API
        """        
        print(status_code)
        
    

class Query(Twython):
    """
    Class for accessing the Twitter REST API.
    """ 


    def hydrate(self, infile):
        """
        Given a file containing a list of Tweet IDs, fetch the corresponding
        Tweets (if they haven't been deleted).

        :param infile: name of a file consisting of Tweet IDs, one to a line
        :return: iterable of Tweet objects
        """
        with open(infile) as f:
            ids = [line.rstrip() for line in f]
            # The Twitter endpoint takes lists of up to 100 ids, so we chunk the ids   
        id_chunks = [ids[i:i+100] for i in range(0, len(ids), 100)]
        listoflists = [self.post('statuses/lookup', {'id': chunk}) for chunk in id_chunks]
        return itertools.chain.from_iterable(listoflists)


class TweetHandler:
    """
    A group of methods for handling the Tweets returned by the Twitter API.
    Each method processes its input on a per-item basis.

    The handler needs to be able to signal a disconnect to the client.
    """
    def __init__(self, limit=2000, repeat=False, fprefix='tweets', subdir='streamed_data', ):
        #self.client = client
        self.limit = limit
        self.repeat = repeat
        self.counter = 0
        self.subdir = subdir
        self.fprefix = fprefix
        self.fname = self.timestamped_file()
        self.startingup = True


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

    #def stdout(self, data, encoding=None):
        #"""
        #Direct data to `sys.stdout`

        #:param data: Tweet object returned by Twitter API
        #"""
        #text = data['text']
        #if encoding is None:            
            #print(text)            
        #else:
            #print(text.encode(encoding))
        #self.counter += 1
        #if self.counter >= self.limit:
            ##self.client.disconnect()
            #return False
        #return True


    #def write(self, data, verbose=True):
        #"""
        #Write Twitter data as line-delimited JSON into one or more files.
        #"""
        #if self.startingup:
            #self.output = open(self.fname, 'w')
            #if verbose:
                #print('Writing to {}'.format(self.fname))            
        #json_data = json.dumps(data)
        #self.output.write(json_data + "\n")
        #self.startingup = False
        #self.counter += 1

        #if self.counter >= self.limit:
            #self.output.close()
            #if not self.repeat:
                ##self.client.disconnect()
                #return False
            #else:
                #self.output = open(self.timestamped_file(), 'w')               
                #self.counter = 0
                #if verbose:
                    #print('Writing to new file {}'.format(self.fname))
        #return True
    
class TweetViewer(TweetHandler):
    
    def handle(self, data):
        """
        Direct data to `sys.stdout`

        :param data: Tweet object returned by Twitter API
        """
        text = data['text']            
        print(text)            
        self.counter += 1
        if self.counter >= self.limit:
            #self.client.disconnect()
            return False
        return True
    
class TweetWriter(TweetHandler):
    
    def handle(self, data):
        """
        Write Twitter data as line-delimited JSON into one or more files.
        """
        if self.startingup:
            self.output = open(self.fname, 'w')
            if verbose:
                print('Writing to {}'.format(self.fname))            
        json_data = json.dumps(data)
        self.output.write(json_data + "\n")
        self.startingup = False
        self.counter += 1
    
        if self.counter >= self.limit:
            self.output.close()
            if not self.repeat:
                #self.client.disconnect()
                return False
            else:
                self.output = open(self.timestamped_file(), 'w')               
                self.counter = 0
                if verbose:
                    print('Writing to new file {}'.format(self.fname))
        return True        

################################
# Utility functions
################################                    

def dehydrate(infile):
    """
    Transform a file of serialized Tweet objects into a file of corresponding
    Tweet IDs.
    """
    with open(infile) as tweets:
        ids = [json.loads(t)['id_str'] for t in tweets]        
        return ids


def authenticate(creds_file=None):
    """
    Read OAuth credentials from a text file.  

    File format for OAuth 1:
    ========================
    app_key=YOUR_APP_KEY
    app_secret=YOUR_APP_SECRET
    oauth_token=OAUTH_TOKEN
    oauth_token_secret=OAUTH_TOKEN_SECRET


    File format for OAuth 2
    =======================
    app_key=YOUR_APP_KEY
    app_secret=YOUR_APP_SECRET
    access_token=ACCESS_TOKEN

    :param file_name: File containing credentials. None (default) reads
    data from "./credentials.txt"
    """
    if creds_file is None:
        path = os.path.dirname(__file__)
        creds_file = os.path.join(path, 'credentials.txt')

    with open(creds_file) as f:
        oauth = {}
        for line in f:
            if '=' in line:
                name, value = line.split('=', 1)
                oauth[name.strip()] = value.strip()    
    return oauth


def add_access_token(creds_file=None):
    """
    For OAuth 2, retrieve an access token for an app and append it to a
    credentials file.
    """
    if creds_file is None:
        path = os.path.dirname(__file__)
        creds_file = os.path.join(path, 'credentials2.txt')  
    oauth2 = authenticate(creds_file=creds_file)
    APP_KEY = oauth2['app_key']
    APP_SECRET = oauth2['app_secret']

    twitter = Twython(APP_KEY, APP_SECRET, oauth_version=2)
    ACCESS_TOKEN = twitter.obtain_access_token()
    s = 'access_token={}\n'.format(ACCESS_TOKEN)
    with open(creds_file, 'a') as f:
        print(s, file=f)



################################
# Demos
################################


TWITTERHOME = '/Users/ewan/twitter/'
CREDS = TWITTERHOME + 'credentials.txt'
TWEETS = TWITTERHOME + 'tweets.20140801-150110.json'
IDS = TWITTERHOME + 'tweet_ids.txt'
REHYDE = TWITTERHOME + 'rehdrated.json'

def streamtoscreen_demo(limit=20):
    oauth = authenticate(CREDS)
    handler = TweetViewer(limit=limit)
    client = Streamer(handler, **oauth)        
    
    #method = handler.stdout
    #client.register(method)
    #client.stdout()
    client.statuses.sample()

def streamtofile_demo(limit=20):
    oauth = authenticate(CREDS) 
    client = Streamer(**oauth)
    handler = TweetHandler(client, limit=limit, subdir=TWITTERHOME)    
    method = handler.write    
    client.register(method)
    client.statuses.sample()    

def dehydrate_demo(infile, outfile):
    ids = dehydrate(infile)
    with open(outfile, 'w') as f:
        for id_str in ids:
            print(id_str, file=f)


def hydrate_demo(infile, outfile):
    oauth = authenticate(CREDS) 
    client = Query(**oauth)
    tweets = client.hydrate(infile)
    with open(outfile, 'w') as f:
        for data in tweets:
            json_data = json.dumps(data)
            f.write(json_data + "\n")                    


def corpusreader_demo():
    #from nltk.corpus import twitter 
    from nltk.corpus import TwitterCorpusReader
    root = 'streamed_data/'
    reader = TwitterCorpusReader(root, '.*\.json')
    for t in reader.tweets()[:10]:
        print(t)

    for t in reader.tokenised_tweets()[:10]:
        print(t)




DEMOS = [0]

if __name__ == "__main__":
    #import doctest
    #doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)   

    if 0 in DEMOS:
        streamtoscreen_demo()    
    if 1 in DEMOS:
        streamtofile_demo()
    if 2 in DEMOS:
        dehydrate_demo(TWEETS, IDS)
    if 3 in DEMOS:
        hydrate_demo(IDS, REHYDE)
    if 4 in DEMOS:
        corpusreader_demo()






