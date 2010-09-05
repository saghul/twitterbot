#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (C) 2010 Saúl ibarra Corretgé <saghul@gmail.com>
#

import feedparser
import os
import re
import sys
import twitter
import urllib
import urllib2

from application.configuration import ConfigSection
from optparse import OptionParser
from pysqlite2 import dbapi2 as sqlite


TWITTERBOT_CFG = "%s/config.ini" % (os.path.dirname(sys.argv[0]) or '.')
TWITTERBOT_DB = "%s/twitterbot.db" % (os.path.dirname(sys.argv[0]) or '.')

class Config(ConfigSection):
    __cfgfile__ = TWITTERBOT_CFG
    __section__ = 'twitterbot'

    consumer_key = ''
    consumer_secret = ''
    access_token_key = ''
    access_token_secret = ''

class TwitterBot(object):
    _rt_regex = re.compile(r"^(RT @\w+: )*(?P<tweet>.*)$")
    _via_regex = re.compile(r"^(?P<tweet>.*)\(via @\w+\)$")

    def __init__(self):
	self._api = twitter.Api(username=Config.consumer_key, 
                                password=Config.consumer_secret,
                                access_token_key=Config.access_token_key,
                                access_token_secret=Config.access_token_secret)
        try:
            user = self._api.VerifyCredentials()
        except twitter.TwitterError, e:
            raise RuntimeError(str(e))
        else:
            self.user = user.GetName()

    def start(self, searchtag):
        try:
            con = sqlite.connect(TWITTERBOT_DB)
            con.isolation_level = None
            twitts = self.search_tag(searchtag)
            for twitt in reversed(twitts['entries']):
                twitt_id = twitt.id.split(':')[2]
                twitt_author = twitt.author.split(' ')[0]
                twitt_content = twitt.title

                if self.user == twitt_author:
                    # I don't want to RT my own twitts!
                    continue

                db_id = con.execute("SELECT id FROM twitts WHERE id MATCH ?", [twitt_id])
                if db_id.fetchall():
                    # We already twitted this!
                    continue

                # Avoid duplicated twitts because of retwitting
                tmp = twitt_content
                if tmp.find('RT @') != -1:
                    tmp = tmp[tmp.find('RT @'):]
                m = self._rt_regex.match(tmp) or self._via_regex.match(tmp)
                if m:
                    data = m.groupdict()
                    tmp = data['tweet']
                    if not tmp:
                        continue
                    db_content = con.execute("SELECT id FROM twitts WHERE content MATCH ?", [tmp])
                    if db_content.fetchall():
                        continue
                try:
                    message = "RT @%s: %s" % (twitt_author,  twitt_content)
                    if len(message) > 140:
                        message = "%s..." % message[:137]
                    self._api.PostUpdate(message)
                except twitter.TwitterError, e:
                    print "-- ERROR: %s" % e.message
                else:
                    con.execute("INSERT INTO twitts(id, content) VALUES(?, ?)", [twitt_id, message])
            con.close()
        except sqlite.Error, e:
            print "[SQLite error: %s]" % str(e)
            sys.exit(1)

    def search_tag(self, tag, lang='en'):
        url = 'http://search.twitter.com/search.atom'
        data = urllib.urlencode({'tag' : tag, 'lang' : lang})
        try:
            opener = urllib2.build_opener()
            opener.addheaders = [ ( 'User-agent', 'Mozilla/5.0' ) ]
            req = urllib2.Request(url, data)
        except urllib2.HTTPError, err:
            print str(err)
            return {}
        else:
            d = feedparser.parse(opener.open(req).read())
            if d.bozo == 1:
                return {}
            return d


if __name__ == "__main__":
    if not Config.consumer_key or not Config.consumer_secret or not Config.access_token_key or not Config.access_token_secret:
        print "Please, fill the confion file"
        sys.exit(1)

    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    parser.add_option('-t', dest='tag', help='Hashtag to search for')
    options, args = parser.parse_args()

    if options.tag:
        bot = TwitterBot()
	bot.start(options.tag)
    else:
        parser.print_help()
        sys.exit(1)

