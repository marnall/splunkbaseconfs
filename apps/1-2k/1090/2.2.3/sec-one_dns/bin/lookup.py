import urllib2
import re
import os

iscurl = 'http://www.defensive-iss.com/blacklists/blacklist.csv'

outfile = os.path.join(os.environ["SPLUNK_HOME"], 'etc', 'apps', 'sec-one_dns', 'lookups', "blacklist.csv")

u = urllib2.urlopen(iscurl)

localFile = open(outfile, 'w')
localFile.write(u.read())
localFile.close