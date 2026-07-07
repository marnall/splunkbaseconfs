#!/usr/bin/python

import json
import sys,csv,splunk.Intersplunk,splunk.saved,string,re,os,platform
import splunk.entity,splunk.version
import requests
import globals
import ConfigParser

from datamodel import DataModel
from datamodelstorage import DataModelStorage


def main():
	(isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
	if len(sys.argv) < 4:
		splunk.Intersplunk.parseError("No arguments provided")
		sys.exit(0)

	token = sys.argv[1].strip()
	modelsType = int(sys.argv[2].strip())
	isGlobal = sys.argv[3].strip()

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

		if isGlobal == 'true':
			isGlobal = "True"
			config.set('corx', 'install_datamodels_globally', isGlobal)
		elif isGlobal == 'false':
			isGlobal = "False"
			config.set('corx', 'install_datamodels_globally', isGlobal)
		else:
			try:
				isGlobal = config.get('corx', 'install_datamodels_globally')
			except:
				isGlobal = "True"

		with open('../local/proxy.conf', 'wb') as configfile:
			config.write(configfile)

		output = csv.writer(sys.stdout)
		output.writerow([
			"Result",
		])

		service = DataModel(token, authToken, isGlobal)
		dataModelStorage = DataModelStorage()

		service.refreshDataModels(modelsType)

		dataModels = dataModelStorage.load()
		splunkDataModels = service.getSplunkDataModels()

		for dataModel in dataModels:
			dataModel["isMissing"] = len(filter(lambda splunkDataModel: splunkDataModel.name == dataModel["name"], splunkDataModels)) == 0

		output.writerow([
			json.dumps(dataModels),
		])

	except Exception as e:
		splunk.Intersplunk.parseError(str(e))

main()
