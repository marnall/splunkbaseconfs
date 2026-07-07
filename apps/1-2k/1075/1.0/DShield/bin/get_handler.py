import urllib2
import csv
import re
import sys
import splunk.Intersplunk as si

handlerapi = "http://isc.sans.edu/api/handler"
results = []

u = urllib2.urlopen(handlerapi)

for line in u:
	matcher = re.match(r"<name>(.*?)</name>", line)
	if matcher:
		results.append({'handler' : matcher.group(1)})
		si.outputResults(results)
