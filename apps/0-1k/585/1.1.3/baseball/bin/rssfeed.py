# Author: Nimish Doshi
# This program reads RSS feed entries from a file and sends its content to
# stdout. It uses feedparser from https://pypi.org/project/feedparser/


import sys

#sys.path.append('/usr/local/lib/python3.7/site-packages')
import feedparser

f = open(sys.argv[1], 'r')
for line in f:
    item = feedparser.parse(line)
    for i in item.entries:
        print (i.published + " " + "title=" + "\"" + i.title + "\"")
        print ("link=" + i.link)
        try:
            print ("description=" + "\"" + i.description + "\"")
        except:
            print ()
f.close()


