#!/usr/bin/python
import json
import urllib
link = "http://www.pm25.in/api/querys/aqi_ranking.json?token=BPz67QsTK8xRZw7HNMAx"
f = urllib.urlopen(link)
j = json.load(f)
for item in j:
    print json.dumps(item)


