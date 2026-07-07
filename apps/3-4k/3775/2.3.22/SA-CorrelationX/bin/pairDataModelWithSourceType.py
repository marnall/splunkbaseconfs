#!/usr/bin/python

import json
import sys,csv,splunk.Intersplunk,string,re,os,platform
import requests
import globals
import ConfigParser
import datamodel
import datamodelstorage


def main():
	(isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
	if len(sys.argv) < 5:
		splunk.Intersplunk.parseError("No arguments provided")
		sys.exit(0)

	token = sys.argv[1].strip()
	dataModelId = sys.argv[2].strip()
	sourceTypeName = sys.argv[3].strip()
	splunkSourceTypeName = sys.argv[4].strip()

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

		config = ConfigParser.RawConfigParser()
		config.read('../local/proxy.conf')
		try:
			isGlobal = config.get('corx', 'install_datamodels_globally')
		except:
			isGlobal = "True"

		output = csv.writer(sys.stdout)
		output.writerow([
			"Result",
		])

		service = datamodel.DataModel(token, authToken, isGlobal)

		output.writerow([
			json.dumps(service.pairSourceTypeWithDataModel(dataModelId, sourceTypeName, splunkSourceTypeName))
		])

	except Exception as e:
		splunk.Intersplunk.parseError(str(e))


main()
