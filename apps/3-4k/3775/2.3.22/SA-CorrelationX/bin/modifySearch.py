#!/usr/bin/python

import json
import sys,csv,splunk.Intersplunk,splunk.saved,string,re,os,platform
import splunk.entity,splunk.version
import requests
import globals
import ConfigParser

from savedsearchstorage import SavedSearchStorage


def main():
	(isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
	if len(sys.argv) < 5:
		splunk.Intersplunk.parseError("No arguments provided")
		sys.exit(0)

	token = sys.argv[1].strip()
	contentId = sys.argv[2].strip()
	syntax = sys.argv[3].strip()
	username = sys.argv[4].strip()

	results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
	authString = settings.get("authString", None)
	if authString == None:
		exit

	start = authString.find('<username>') + 10
	stop = authString.find('</username>')
	user = authString[start:stop]

	start = authString.find('<authToken>') + 11
	stop = authString.find('</authToken>')
	authToken = authString[start:stop]

	try:

		savedSearchStorage = SavedSearchStorage(token, authToken)

		output = csv.writer(sys.stdout)
		output.writerow([
			"Result",
		])

		output.writerow([
			json.dumps(savedSearchStorage.updateContentSyntax(contentId, syntax, username)),
		])

	except Exception as e:
		splunk.Intersplunk.parseError(str(e))

main()
