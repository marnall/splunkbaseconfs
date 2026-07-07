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
	if len(sys.argv) < 2:
		splunk.Intersplunk.parseError("No arguments provided")
		sys.exit(0)

	token = sys.argv[1].strip()

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
		storage = datamodelstorage.DataModelStorage()

		dataModels = storage.load()
		apiDataModels = service.getDataModels()
		splunkDataModels = service.getSplunkDataModels()

		for dataModel in dataModels:
			dataModel["isMissing"] = len(filter(lambda splunkDataModel: splunkDataModel.name == dataModel["name"], splunkDataModels)) == 0

		result = []
		for splunkDataModel in splunkDataModels:
			dataModel = filter(lambda dataModel: splunkDataModel.name == dataModel["name"], dataModels)
			apiDataModel = filter(lambda apiDataModel: splunkDataModel.name == apiDataModel["name"], apiDataModels)
			if len(apiDataModel) != 0:
				if len(dataModel) == 0:
					result.append({
						"name": splunkDataModel.name,
						"displayName": splunkDataModel.name,
						"isEditable": True,
						"type": 2,
						"dataModelId": apiDataModel[0]["dataModelId"],
						"sourceTypes": []
					})
				else:
					dataModel[0]["isEditable"] = True
					result.append(dataModel[0])

		output.writerow([
			json.dumps(result)
		])

		output.writerow([
			json.dumps(service.getSplunkSourceTypes())
		])

		compareResult = storage.compareDataModels(apiDataModels, splunkDataModels)

		cxDataModelsInstalled = len(filter(lambda item: item["type"] == 1, dataModels)) > 0 and len(filter(lambda item: item["type"] == 1 and item["isMissing"], dataModels)) == 0
		cimDataModelsInstalled = len(filter(lambda item: item["type"] == 2 and len(filter(lambda splunkItem: splunkItem.name == item["name"], splunkDataModels)) > 0, apiDataModels)) > 0
		cxDataModelsHaveUpdates = False
		cimDataModelsHaveUpdates = False

		if compareResult["create"] is not None:
			cxDataModelsHaveUpdates = cxDataModelsHaveUpdates or len(filter(lambda item: item["type"] == 1, compareResult["create"])) > 0
			cimDataModelsHaveUpdates = cimDataModelsHaveUpdates or len(filter(lambda item: item["type"] == 2, compareResult["create"])) > 0
		if compareResult["update"] is not None:
			cxDataModelsHaveUpdates = cxDataModelsHaveUpdates or len(filter(lambda item: item["type"] == 1, compareResult["update"])) > 0
			cimDataModelsHaveUpdates = cimDataModelsHaveUpdates or len(filter(lambda item: item["type"] == 2, compareResult["update"])) > 0
		if compareResult["delete"] is not None:
			cxDataModelsHaveUpdates = cxDataModelsHaveUpdates or len(filter(lambda item: item["type"] == 1, compareResult["delete"])) > 0
			cimDataModelsHaveUpdates = cimDataModelsHaveUpdates or len(filter(lambda item: item["type"] == 2, compareResult["delete"])) > 0

		config = ConfigParser.RawConfigParser()
		config.read('../local/proxy.conf')
		try:
			isGlobal = config.get('corx', 'install_datamodels_globally')
		except:
			isGlobal = "True"

		output.writerow([
			json.dumps({
				"CxDataModelsInstalled": cxDataModelsInstalled,
				"CimDataModelsInstalled": cimDataModelsInstalled,
				"CxDataModelsHaveUpdates": cxDataModelsHaveUpdates,
				"CimDataModelsHaveUpdates": cimDataModelsHaveUpdates,
				"IsGlobal": True if isGlobal == "True" else False,
			}),
		])

	except Exception as e:
		splunk.Intersplunk.parseError(str(e))


main()
