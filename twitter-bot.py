#!/usr/bin/python
# -*- coding: utf-8 -*-



from pysqlite2 import dbapi2 as sqlite
import urllib
import urllib2
import feedparser
import twitter
import getopt
import sys
import os


TWITTERBOT_DB = "%s/twitterbot.db" % os.path.dirname(sys.argv[0])

class TwitterBot(object):

	def __init__(self, user, passw):
		self.user = user
		self.api = twitter.Api(username=user, password=passw)

	def startBot(self, searchtag):
		try:
			con = sqlite.connect(TWITTERBOT_DB)
			con.isolation_level = None
			twitts = self._search(searchtag)

			for twitt in reversed(twitts['entries']):
				twitt_id = twitt.id.split(':')[2]
				twitt_author = twitt.author.split(' ')[0]

				if self.user == twitt_author:
					# I don't want to RT my own twitts!
					continue

				db_id = con.execute("SELECT id FROM repeated_twitts WHERE id = %s LIMIT 1" % twitt_id)

				if db_id.fetchall():
					# We already twitted this!
					continue

				try:
					self.api.PostUpdate("@%s: %s" % (twitt_author,  twitt.title))

				except:
					pass

				else:
					con.execute("INSERT INTO repeated_twitts(id) VALUES(%s)" % twitt_id)

			con.close()

		except sqlite.Error, e:
			print "[ERROR]", e
			sys.exit(1)

	def _doRequest(self, url, data=None):
	    try:
	        opener = urllib2.build_opener()
	        opener.addheaders = [ ( 'User-agent', 'Mozilla/5.0' ) ]
	        req = urllib2.Request(url, data)
	        return opener.open(req)
	    except urllib2.HTTPError, err:
	        print str(err)
		
	def _search(self, tag, lang='en'):
	    data = urllib.urlencode({'tag' : tag, 'lang' : lang})
	    f = self._doRequest('http://search.twitter.com/search.atom', data)
	    d = feedparser.parse(f.read())
	    return d


if __name__ == "__main__":
    usage = "python twitterbot.py -u username -p password -t search_tag"
    try:
        opts, args = getopt.getopt(sys.argv[1:], "u:p:t:")
        if len(opts) == 3:
	    for o, a in opts:
		if o == "-u":
		    user = a
		    continue
		elif o == "-p":
		    passw = a
		    continue
		elif o == "-t":
		    tag = a
		    continue

	    tb = TwitterBot(user, passw)
	    tb.startBot(tag)
	    sys.exit(0)

        else:
	    print usage
	    sys.exit(1)

    except getopt.GetoptError, err:
        print str(err)
        print usage
        sys.exit(1)

