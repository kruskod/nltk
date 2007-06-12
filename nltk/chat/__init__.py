# Natural Language Toolkit: Chatbots
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Authors: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

# Based on an Eliza implementation by Joe Strout <joe@strout.net>,
# Jeff Epler <jepler@inetnebr.com> and Jez Higgins <jez@jezuk.co.uk>.

"""
A class for simple chatbots.  These perform simple pattern matching on sentences
typed by users, and respond with automatically generated sentences.

These chatbots may not work using the windows command line or the
windows IDLE GUI.
"""

from util import *
from eliza import eliza_chat
from iesha import iesha_chat
from rude import rude_chat
from suntsu import suntsu_chat
from zen import zen_chat
