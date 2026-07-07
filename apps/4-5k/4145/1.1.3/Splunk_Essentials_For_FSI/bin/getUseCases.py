##!/usr/bin/python


import json, csv, re, os
import urllib3
import sys
import splunk.mining.dcutils as dcu
logger = dcu.getLogger()
sessionKey = ""

for line in sys.stdin:
  m = re.search("sessionKey:\s*(.*?)$", line)
  if m:
	  sessionKey = m.group(1)

import splunk.entity, splunk.Intersplunk

settings = dict()
records = splunk.Intersplunk.readResults(settings = settings, has_header = True)
entity = splunk.entity.getEntity('/server','settings', namespace='Splunk_Essentials_For_FSI', sessionKey=sessionKey, owner='-')
mydict = dict()
mydict = entity
myPort = mydict['mgmtHostPort']

base_url = "https://127.0.0.1:8089"
#print base_url + '/servicesNS/nobody/search_activity/properties/macros/test'
http = urllib3.PoolManager(cert_reqs='CERT_NONE')
try:
	request = http.request('GET',base_url + '/servicesNS/nobody/Splunk_Essentials_For_FSI/storage/collections/data/bookmark',
		headers = { 'Authorization': ('Splunk %s' % sessionKey)})
	logger.info(f"Status code: {request.status}") 
	search_results = request.data
except Exception as e:
	logger.info(f"Error: {e}") 

kvstore_output = json.loads(search_results)

kvstore_usernames = dict()
kvstore_conversion = dict()
for i in kvstore_output:
	kvstore_conversion[i['showcase_name']] = i['status']
	if "user" in i:
		kvstore_usernames[i['showcase_name']] = i['user']

myApps = ["Splunk_Essentials_For_FSI"]
globalSourceList = dict()
globalSearchList = dict()
for myApp in myApps:
	with open(os.environ['SPLUNK_HOME'] + "/etc/apps/" + myApp + "/appserver/static/components/data/ShowcaseInfo.json") as f:
		data = json.load(f)
		if "summaries" not in globalSourceList:
			globalSourceList = data
		else:
			for summaryName in data['summaries']:
				if summaryName not in globalSourceList['summaries']:
					globalSourceList['summaries'][summaryName] = data['summaries'][summaryName]
					globalSourceList['roles']['default']['summaries'].append(summaryName)

myAssistants = ["showcase_first_seen_demo", "showcase_standard_deviation", "showcase_simple_search"]
for assistant in myAssistants:
	with open(os.environ['SPLUNK_HOME'] + "/etc/apps/" + myApps[0] + "/appserver/static/components/data/sampleSearches/" + assistant + ".json") as f:
		data = json.load(f)
		globalSearchList.update(data)

for summaryName in globalSourceList['summaries']:
	if globalSourceList['summaries'][summaryName]['name'] in kvstore_conversion:
		globalSourceList['summaries'][summaryName]['bookmark_status'] = kvstore_conversion[globalSourceList['summaries'][summaryName]['name']]
	else:
		globalSourceList['summaries'][summaryName]['bookmark_status'] = "none"
	if globalSourceList['summaries'][summaryName]['name'] in kvstore_usernames:
		globalSourceList['summaries'][summaryName]['bookmark_user'] = kvstore_usernames[globalSourceList['summaries'][summaryName]['name']]
	else:
		globalSourceList['summaries'][summaryName]['bookmark_user'] = "none"
	if "examples" in globalSourceList['summaries'][summaryName]:
		for i in range(0, len(globalSourceList['summaries'][summaryName]['examples'])):
			globalSourceList['summaries'][summaryName]['example' + str(i)] = dict()
			globalSourceList['summaries'][summaryName]['example' + str(i)]['name'] = globalSourceList['summaries'][summaryName]['examples'][i]['name']
			globalSourceList['summaries'][summaryName]['example' + str(i)]['label'] = globalSourceList['summaries'][summaryName]['examples'][i]['label']
			if globalSourceList['summaries'][summaryName]['examples'][i]['name'] in globalSearchList:
				globalSourceList['summaries'][summaryName]['example' + str(i)]['object'] = globalSearchList[ globalSourceList['summaries'][summaryName]['examples'][i]['name'] ]
				globalSourceList['summaries'][summaryName]['example' + str(i)]['object']['numDescriptions'] = 0
				globalSourceList['summaries'][summaryName]['example' + str(i)]['object']['numPreReqs'] = 0
				if "prereqs" in globalSourceList['summaries'][summaryName]['example' + str(i)]['object']:
					globalSourceList['summaries'][summaryName]['example' + str(i)]['object']['numPreReqs'] = len(globalSourceList['summaries'][summaryName]['example' + str(i)]['object']['prereqs'])
				if "description" in globalSourceList['summaries'][summaryName]['example' + str(i)]['object']:
					globalSourceList['summaries'][summaryName]['example' + str(i)]['object']['numDescriptions'] = len(globalSourceList['summaries'][summaryName]['example' + str(i)]['object']['description'])
		del globalSourceList['summaries'][summaryName]['examples']

print("summaries")
regex = '"'
for summaryName in globalSourceList['summaries']:
	line = json.dumps(globalSourceList['summaries'][summaryName], sort_keys=True)
	print('"' + re.sub('\n', '', re.sub('"', '""', line)) + '"')
