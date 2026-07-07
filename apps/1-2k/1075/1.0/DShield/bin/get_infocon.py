import urllib2
import csv
import re
import sys
import splunk.Intersplunk as si

handlerapi = "http://isc.sans.edu/api/infocon"
results = []

u = urllib2.urlopen(handlerapi)

for line in u:
	matcher = re.match(r"<status>(.*?)</status>", line)
	if matcher:
		results.append({'infocon' : matcher.group(1)})
		si.outputResults(results)
