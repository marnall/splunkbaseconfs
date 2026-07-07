#!/usr/bin/python

import json
import sys,csv,splunk.Intersplunk,string,re,os,platform
import requests
import globals
import datamodel
import datamodelstorage


def main():
	(isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
	if len(sys.argv) < 3:
		splunk.Intersplunk.parseError("No arguments provided")
		sys.exit(0)

	token = sys.argv[1].strip()
	sourceType = sys.argv[2].strip()

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

		output = csv.writer(sys.stdout)
		output.writerow([
			"Data",
		])

		service = datamodel.DataModel(token, authToken)

		result = map(lambda item: str(item.fields["field"]), service.getSplunkSourceTypeFields(sourceType))

		output.writerow([
			json.dumps(result)
		])

	except Exception as e:
		splunk.Intersplunk.parseError(str(e))


main()
