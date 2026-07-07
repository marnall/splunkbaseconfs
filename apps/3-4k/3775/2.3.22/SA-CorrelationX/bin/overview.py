#!/usr/bin/python

import sys,csv,splunk.Intersplunk,string,re,os,platform
import json
import splunk.search

from datamodel import DataModel
from datamodelstorage import DataModelStorage
from savedsearchstorage import SavedSearchStorage

def checkEsInstallation(settings):
	try:
		authString = settings.get("authString", None)
		if authString == None:
			exit

		start = authString.find('<authToken>') + 11
		stop = authString.find('</authToken>')
		authToken = authString[start:stop]

		if not os.path.exists("../local"):
			os.makedirs("../local")
		with open("../local/eschecker.json", "w+") as esCheckerFile:
			appInfo = splunk.search.searchAll("rest /services/apps/local | search disabled=0 | where label=\"Enterprise Security\"", sessionKey = authToken)
			result = "True" if "Enterprise Security" in ','.join(map(str, appInfo)) else "False"
			json.dump({
				"hasEnterpriseSecurity": result
			}, esCheckerFile)

		return result == "True"
	except:
		return False

def main():
	try:
		(isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
		if len(sys.argv) < 2:
			splunk.Intersplunk.parseError("No arguments provided")
			sys.exit(0)

		token = sys.argv[1].strip()

		results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
		authString = settings.get("authString", None)
		if authString == None:
			exit

		start = authString.find('<authToken>') + 11
		stop = authString.find('</authToken>')
		authToken = authString[start:stop]

		checkEsInstallation(settings)

		service = DataModel(token, authToken)
		dataModelStorage = DataModelStorage()
		savedSearchStorage = SavedSearchStorage(token, authToken)

		output = csv.writer(sys.stdout)
		output.writerow([
			"Data",
		])

		savedSearchStorage.refreshSavedSearchesBasedOnExistence()

		output.writerow([
			json.dumps(savedSearchStorage.load()),
		])

		output.writerow([
			json.dumps(savedSearchStorage.getKillChainPhases())
		])

		try:
			dataModels = dataModelStorage.load()
			apiDataModels = service.getDataModels()
			splunkDataModels = service.getSplunkDataModels()

			for dataModel in dataModels:
				dataModel["isMissing"] = len(filter(lambda splunkDataModel: splunkDataModel.name == dataModel["name"], splunkDataModels)) == 0

			for splunkDataModel in splunkDataModels:
				dataModel = filter(lambda dataModel: splunkDataModel.name == dataModel["name"], dataModels)
				apiDataModel = filter(lambda apiDataModel: splunkDataModel.name == apiDataModel["name"], apiDataModels)
				if len(dataModel) == 0 and len(apiDataModel) != 0:
					dataModels.append({
						"name": splunkDataModel.name,
						"displayName": splunkDataModel.name,
						"type": 2,
						"sourceTypes": [],
					})

			output.writerow([
				json.dumps(dataModels),
			])
			compareResult = dataModelStorage.compareDataModels(apiDataModels, splunkDataModels)

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

			output.writerow([
				json.dumps({
					"CxDataModelsInstalled": cxDataModelsInstalled,
					"CimDataModelsInstalled": cimDataModelsInstalled,
					"CxDataModelsHaveUpdates": cxDataModelsHaveUpdates,
					"CimDataModelsHaveUpdates": cimDataModelsHaveUpdates,
				}),
			])

		except Exception as ex:
			raise ex

	except Exception as e:
		splunk.Intersplunk.parseError(str(e))


main()
