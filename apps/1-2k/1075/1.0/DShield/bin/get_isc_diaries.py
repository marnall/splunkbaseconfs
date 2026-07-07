import urllib2
import re
import sys
import os
from xml.dom.minidom import parseString

# We retrieve RSS feed from ISC for information about diaries
handlerapi = "http://isc.sans.edu/rssfeed.xml"

outfile = os.path.join(os.environ["SPLUNK_HOME"], 'etc', 'apps', 'DShield', 'appserver', 'static', "diaries.html")

try:
	u = urllib2.urlopen(handlerapi)
except:
	sys.exit(1)

data = u.read()
u.close()

# Open HTML file
f = open(outfile, 'w')

# Write header
f.write("<html>\n<head>\n<meta http-equiv=\"Content-Type\" content=\"text/html; charset=UTF-8\" />\n<title>SANS ISC diaries</title>\n</head>\n\n<body>")

dom = parseString(data)

xmlTag = dom.getElementsByTagName('item')
i=0
for x in xmlTag:
	if i < 3:
		i=i+1
		continue
	title = dom.getElementsByTagName('title')[i].firstChild.nodeValue
	link = dom.getElementsByTagName('link')[i].firstChild.nodeValue
	i = i+1
	f.write("<a href=\"" + link + "\">" + title + "</a><br>\n")

f.write("<br>\n</body>\n</html>\n\n")
