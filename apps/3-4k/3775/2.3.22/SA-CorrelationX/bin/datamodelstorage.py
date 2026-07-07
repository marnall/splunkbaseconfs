#!/usr/bin/python

# app shared configuration
import globals
# python modules
import json


class DataModelStorage:

	def load(self):
		try:
			with open("../local/datamodel.json") as dataModelFile:
				return json.load(dataModelFile)
		except:
			return []

	def save(self, dataModels):
		try:
			with open("../local/datamodel.json", "w") as dataModelFile:
				json.dump(dataModels, dataModelFile)
			return True
		except:
			return False

	def getDataModel(self, name, dataModels = None):
		if dataModels is None:
			dataModels = self.load()
		result = filter(lambda dataModel: dataModel["name"] == name, dataModels)
		if len(result) > 0:
			return result[0]

	def saveDataModel(self, apiDataModel, apiDataSources = None):
		dataModels = self.load()
		dataModel = self.getDataModel(apiDataModel["name"], dataModels)

		if dataModel is None:
			dataModel = {
				"name": apiDataModel["name"],
			}
			dataModels.append(dataModel)

		dataModel["dataModelId"] = apiDataModel["dataModelId"]
		dataModel["displayName"] = apiDataModel["displayName"]
		dataModel["type"] = apiDataModel["type"]
		dataModel["version"] = apiDataModel["activeVersion"]["version"]
		dataModel["sourceTypes"] = []

		if apiDataSources is not None:
			dataModel["sourceTypes"] = map(lambda apiDataSource: {
				"name": apiDataSource["name"],
				"splunkSourceTypes": apiDataSource["splunkSourceTypes"],
				"savedAlternateNames": apiDataSource["savedAlternateNames"] if apiDataSource.has_key("savedAlternateNames") else None,
			}, apiDataSources)

		self.save(dataModels)

	def deleteDataModel(self, dataModelId, dataModels = None):
		if dataModels is None:
			dataModels = self.load()

		dataModels = filter(lambda savedSearch: savedSearch["dataModelId"] != dataModelId, dataModels)

		self.save(dataModels)

	def compareDataModels(self, apiDataModels, splunkDataModels = None):
		result = {}
		dataModels = self.load()

		if splunkDataModels is not None:
			for dataModel in dataModels:
				dataModel["isMissing"] = len(filter(lambda splunkDataModel: splunkDataModel.name == dataModel["name"], splunkDataModels)) == 0

		result["delete"] = filter(lambda dataModel: len(filter(lambda apiDataModel: dataModel["dataModelId"] == apiDataModel["dataModelId"], apiDataModels)) < 1, dataModels)
		result["create"] = filter(lambda apiDataModel: len(filter(lambda dataModel: dataModel["dataModelId"] == apiDataModel["dataModelId"] and (not dataModel["isMissing"] or dataModel["type"] == 2), dataModels)) < 1, apiDataModels)
		result["update"] = filter(lambda apiDataModel: len(filter(lambda dataModel: dataModel["dataModelId"] == apiDataModel["dataModelId"] and dataModel["version"] != apiDataModel["activeVersion"], dataModels)) > 0, apiDataModels)
		#result["update"] = filter(lambda apiDataModel: len(filter(lambda dataModel: dataModel["dataModelId"] == apiDataModel["dataModelId"], dataModels)) > 0, apiDataModels)

		return result

	def mergeDataModel(self, apiDataModel, onlyInstalledDataSources = False):
		dataModel = self.getDataModel(apiDataModel["name"])
		if dataModel is not None:
			if onlyInstalledDataSources:
				apiDataModel["dataSources"] = dataModel["sourceTypes"]
			else:
				for dataSource in dataModel["sourceTypes"]:
					apiDataSource = filter(lambda apiDataSource: apiDataSource["name"] == dataSource["name"], apiDataModel["dataSources"])
					if len(apiDataSource) > 0:
						if dataSource.has_key("savedAlternateNames") and dataSource["savedAlternateNames"] is not None and apiDataSource[0].has_key("alternateNames"):
							dataSource["alternateNames"] = filter(lambda alternateName: len(filter(lambda saved: alternateName["name"] == saved["name"], dataSource["savedAlternateNames"])) == 0, apiDataSource[0]["alternateNames"])
						dataSource["savedAlternateNames"] = apiDataSource[0]["alternateNames"] if apiDataSource[0].has_key("alternateNames") else None

					apiDataModel["dataSources"] = filter(lambda apiDataSource: apiDataSource["name"] != dataSource["name"], apiDataModel["dataSources"])
					apiDataModel["dataSources"].append(dataSource)
		return apiDataModel
