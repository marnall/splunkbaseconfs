#!/usr/bin/python

# app shared configuration
import globals
# app modules
from datamodelstorage import DataModelStorage
# python modules
import copy
import json
import requests
# splunk modules
import splunk.entity
import splunk.search

# data models constants
DATA_MODELS_ENDPOINT_ENTITY_PATH = "datamodel/model"
SOURCE_TYPES_ENDPOINT_ENTITY_PATH = "saved/sourcetypes"
EVENT_TYPES_ENDPOINT_ENTITY_PATH = "saved/eventtypes"
FIELDS_ENDPOINT_ENTITY_PATH = "search/fields"
FIELD_ALIASES_ENDPOINT_ENTITY_PATH = "data/props/fieldaliases"
ACCELERATION_EARLIEST_TIME = {
	1: "-1d",
	7: "-1w",
	30: "-1mon",
	91: "-3mon",
	365: "-1y",
	32767: "0",
}

class DataModel:

	def __init__(self, apiToken, sessionKey, isGlobal = "True"):
		self.apiToken = apiToken
		self.sessionKey = sessionKey
		self.isGlobal = isGlobal
		self.dataModelStorage = DataModelStorage()
		self.splunkDataModels = []
		self.splunkSourceTypes = []
		self.splunkFields = []
		self.splunkFieldAliases = []
		self.splunkSourceTypeFields = {}

	# load data from api
	def getDataModels(self):
		return getApi("/api/dataModel/splunk", self.apiToken, self.sessionKey)

	def getDataModel(self, dataModelId):
		return getApi("/api/dataModel/" + str(dataModelId) + "/splunk", self.apiToken, self.sessionKey)

	# splunk data models methods
	def getSplunkDataModels(self):
		return getEntitiesList(DATA_MODELS_ENDPOINT_ENTITY_PATH, self.sessionKey)

	def loadSplunkDataModels(self):
		if len(self.splunkDataModels) == 0:
			self.splunkDataModels = self.getSplunkDataModels()

	def getSplunkDataModel(self, name):
		return getEntity(DATA_MODELS_ENDPOINT_ENTITY_PATH, name, self.sessionKey)

	def setSplunkDataModel(self, dataModel):
		try:
			result = splunk.entity.getEntity(DATA_MODELS_ENDPOINT_ENTITY_PATH, dataModel["name"], namespace = "SA-CorrelationX", owner = "nobody", sessionKey = self.sessionKey)
			result["acceleration.allowed"] = None
			result["disabled"] = None
		except:
			try:
				result = splunk.entity.Entity(DATA_MODELS_ENDPOINT_ENTITY_PATH, dataModel["name"], namespace = "SA-CorrelationX", owner = "nobody")
				result["acceleration"] = {"enabled":False,"earliest_time":"","cron_schedule":"*/5 * * * *","max_time":3600,"backfill_time":"","manual_rebuilds":False,"max_concurrent":2,"schedule_priority":"default","hunk.file_format":"","hunk.dfs_block_size":0,"hunk.compression_codec":""}
			except Exception as ex:
				return False

		result["description"] = dataModel["activeVersion"]["splunkConfig"]
		if type(result["acceleration"]) is str:
			try:
				result["acceleration"] = json.loads(result["acceleration"])
			except Exception as ex:
				pass

		result["acceleration"]["enabled"] = dataModel["isAccelerated"]
		if dataModel["isAccelerated"]:
			result["acceleration"]["earliest_time"] = ACCELERATION_EARLIEST_TIME[dataModel["dataModelAccelerationRange"]]
		else:
			result["acceleration"]["earliest_time"] = ""

		try:
			result["acceleration"] = json.dumps(result["acceleration"])
		except Exception as ex:
			pass

		try:
			splunk.entity.setEntity(result, sessionKey = self.sessionKey)
		except Exception as ex:
			return False

		try:
			acl = splunk.entity.Entity(DATA_MODELS_ENDPOINT_ENTITY_PATH + "/" + dataModel["name"].replace("/", "%2F"), "acl", namespace = "SA-CorrelationX", owner = "nobody")
			acl["owner"] = "nobody"
			acl["sharing"] = "global" if self.isGlobal == "True" else "app"
			splunk.entity.setEntity(acl, sessionKey = self.sessionKey)
		except Exception as ex:
			pass

		return True

	def deleteSplunkDataModel(self, dataModel):
		try:
			self.dataModelStorage.deleteDataModel(dataModel["dataModelId"])
			if dataModel["type"] == 1:
				splunk.entity.deleteEntity(DATA_MODELS_ENDPOINT_ENTITY_PATH, dataModel["name"], namespace = "SA-CorrelationX", owner = "nobody", sessionKey = self.sessionKey)
			return True
		except:
			return False

	# splunk source types methods
	def getSplunkSourceTypes(self):
		try:
			return map(lambda item: str(item["name"]), splunk.search.searchAll("| metadata type=sourcetypes | fields + sourcetype | rename sourcetype as name ", sessionKey = self.sessionKey))
		except:
			return []

	def loadSplunkSourceTypes(self):
		if len(self.splunkSourceTypes) == 0:
			self.splunkSourceTypes = self.getSplunkSourceTypes()

	#def getSplunkSourceType(self, name):
	#	return getEntitiesList(SOURCE_TYPES_ENDPOINT_ENTITY_PATH, name, self.sessionKey)

	# splunk event types methods
	def getSplunkEventTypes(self):
		return getEntitiesList(EVENT_TYPES_ENDPOINT_ENTITY_PATH, self.sessionKey)

	def loadSplunkEventTypes(self):
		if len(self.splunkEventTypes) == 0:
			self.splunkEventTypes = self.getSplunkEventTypes()

	def getSplunkEventType(self, name):
		return getEntitiesList(EVENT_TYPES_ENDPOINT_ENTITY_PATH, name, self.sessionKey)

	def setSplunkEventTypes(self, eventTypes):
		for eventType in eventTypes:
			self.setSplunkEventType(eventType)

	def setSplunkEventType(self, eventType):
		exists = False
		try:
			result = splunk.entity.getEntity(EVENT_TYPES_ENDPOINT_ENTITY_PATH, eventType["name"], namespace = "SA-CorrelationX", owner = "nobody", sessionKey = self.sessionKey)
			exists = True
		except:
			try:
				result = splunk.entity.Entity(EVENT_TYPES_ENDPOINT_ENTITY_PATH, eventType["name"], namespace = "SA-CorrelationX", owner = "nobody")
			except:
				return False

		if (not exists) or (result["search"] != eventType["search"]) or (eventType["tags"] not in result["search"]):

			result["search"] = eventType["search"]
			result["tags"] = eventType["tags"]

			try:
				splunk.entity.setEntity(result, sessionKey = self.sessionKey)
			except:
				pass

		try:
			acl = splunk.entity.Entity(EVENT_TYPES_ENDPOINT_ENTITY_PATH + "/" + eventType["name"].replace("/", "%2F"), "acl", namespace = "SA-CorrelationX", owner = "nobody")
			acl.properties["owner"] = "nobody"
			acl.properties["sharing"] = "global" if self.isGlobal == "True" else "app"
			splunk.entity.setEntity(acl, sessionKey = self.sessionKey)
		except Exception as ex:
			pass

	def deleteSplunkEventType(self, eventTypeName):
		try:
			splunk.entity.deleteEntity(EVENT_TYPES_ENDPOINT_ENTITY_PATH, eventTypeName, namespace = "SA-CorrelationX", owner = "nobody", sessionKey = self.sessionKey)
			return True
		except:
			return False

	# splunk fields methods
	def getSplunkFields(self):
		return getEntitiesList(FIELDS_ENDPOINT_ENTITY_PATH, self.sessionKey)

	def loadSplunkFields(self):
		if len(self.splunkFields) == 0:
			self.splunkFields = self.getSplunkFields()

	def getSplunkField(self, name):
		return getEntitiesList(FIELDS_ENDPOINT_ENTITY_PATH, name, self.sessionKey)

	# splunk field aliases methods
	def getSplunkFieldAliases(self):
		return getEntitiesList(FIELD_ALIASES_ENDPOINT_ENTITY_PATH, self.sessionKey)

	def loadSplunkFieldAliases(self):
		if len(self.splunkFieldAliases) == 0:
			self.splunkFieldAliases = self.getSplunkFieldAliases()

	def getSplunkFieldAlias(self, name):
		return getEntitiesList(FIELD_ALIASES_ENDPOINT_ENTITY_PATH, name, self.sessionKey)

	def setSplunkFieldAlias(self, sourceTypeName, name, alias, oldName = None):
		try:
			result = splunk.entity.getEntity(FIELD_ALIASES_ENDPOINT_ENTITY_PATH, sourceTypeName + " : FIELDALIAS-" + alias, namespace = "SA-CorrelationX", owner = "nobody", sessionKey = self.sessionKey)
			splunk.entity.deleteEntity(FIELD_ALIASES_ENDPOINT_ENTITY_PATH, sourceTypeName + " : FIELDALIAS-" + alias, namespace = "SA-CorrelationX", owner = "nobody", sessionKey = self.sessionKey)
		except Exception as ex:
			pass

		if not name:
			return True

		result = splunk.entity.Entity(FIELD_ALIASES_ENDPOINT_ENTITY_PATH, alias, namespace = "SA-CorrelationX", owner = "nobody")
		result["stanza"] = sourceTypeName
		result["alias." + name] = alias

		try:
			splunk.entity.setEntity(result, sessionKey = self.sessionKey)
		except Exception as ex:
			pass

		try:
			acl = splunk.entity.Entity(FIELD_ALIASES_ENDPOINT_ENTITY_PATH + "/" + sourceTypeName.replace("/", "%2F") + " : FIELDALIAS-" + alias, "acl", namespace = "SA-CorrelationX", owner = "nobody")
			acl["owner"] = "nobody"
			acl["sharing"] = "global" if self.isGlobal == "True" else "app"
			splunk.entity.setEntity(acl, sessionKey = self.sessionKey)
		except Exception as ex:
			pass

		return True

	# splunk source type fields methods
	def getSplunkSourceTypeFields(self, sourceTypeName):
		try:
			if not self.splunkSourceTypeFields.has_key(sourceTypeName):
				data = splunk.search.searchAll("search sourcetype=\"" + sourceTypeName + "\" | head 50000 | fieldsummary ", sessionKey = self.sessionKey)
				self.splunkSourceTypeFields[sourceTypeName] = data
			return self.splunkSourceTypeFields[sourceTypeName]
		except:
			return []

	# save data model methods
	def saveGenericDataModel(self, dataModel):
		self.updateDataModelConstraints(dataModel, [])
		self.dataModelStorage.saveDataModel(dataModel)
		if dataModel["type"] == 1:
			self.setSplunkDataModel(dataModel)

	def saveTypedDataModel(self, dataModel, sourceTypes):
		self.updateDataModelConstraints(dataModel, sourceTypes)
		self.dataModelStorage.saveDataModel(dataModel, sourceTypes)
		if dataModel["type"] == 1:
			self.setSplunkDataModel(dataModel)

	def refreshDataModels(self, modelsType = None):
		try:
			dataModels = self.getDataModels()
			splunkDataModels = self.getSplunkDataModels()
			compareResult = self.dataModelStorage.compareDataModels(dataModels, splunkDataModels)
			if compareResult["create"]:
				if modelsType is not None:
					compareResult["create"] = filter(lambda item: item["type"] == modelsType, compareResult["create"])
				for item in compareResult["create"]:
					dataModel = self.getDataModel(item["dataModelId"])
					self.matchSourceTypesFromDataModel(dataModel)
			if compareResult["update"]:
				if modelsType is not None:
					compareResult["update"] = filter(lambda item: item["type"] == modelsType, compareResult["update"])
				for item in compareResult["update"]:
					dataModel = self.dataModelStorage.mergeDataModel(self.getDataModel(item["dataModelId"]))
					if dataModel is not None:
						self.matchSourceTypesFromDataModel(dataModel)
			if compareResult["delete"]:
				if modelsType is not None:
					compareResult["delete"] = filter(lambda item: item["type"] == modelsType, compareResult["delete"])
				for item in compareResult["delete"]:
					self.deleteSplunkDataModel(item)

			if modelsType == 1:
				for dataModel in dataModels:
					# if cx model does not exits
					if dataModel["type"] == 1 and len(filter(lambda splunkDataModel: splunkDataModel.name == dataModel["name"], splunkDataModels)) == 0:
						dataModel = self.dataModelStorage.mergeDataModel(self.getDataModel(dataModel["dataModelId"]))
						if dataModel is not None:
							self.matchSourceTypesFromDataModel(dataModel)
			return True
		except Exception as ex:
			pass

	def updateDataModelConstraints(self, dataModel, sourceTypes):
		try:
			dataModelPrimaryTag = dataModel["selectedPrimarySplunkTag"] if dataModel.has_key("selectedPrimarySplunkTag") else None
			# primary tags
			constraints = reduce(lambda result, sourceType: result + map(lambda splunkSourceType: {
				"name": "CorrelationX " + splunkSourceType["splunkName"].replace("*", "") + " " + dataModelPrimaryTag.replace("*", "") if dataModelPrimaryTag is not None else "CorrelationX " + splunkSourceType["splunkName"].replace("*", ""),
				"search": "index=* sourcetype=" + splunkSourceType["splunkName"],
				"tags": dataModelPrimaryTag,
			}, sourceType["splunkSourceTypes"]), sourceTypes, [])
			# alternate tags
			if dataModel.has_key("dataModelTags") and dataModel["dataModelTags"] is not None:
				for tag in dataModel["dataModelTags"]:
					for search in tag["dataModelTagStrings"]:
						constraints.append({
							"name": "CorrelationX " + dataModel["name"] + " " + tag["name"].replace("*", "") + " " + str(search["dataModelStringId"]),
							"search": search["name"],
							"tags": tag["name"],
						})

			self.setSplunkEventTypes(constraints)
			splunkConfig = json.loads(dataModel["activeVersion"]["splunkConfig"])
			if splunkConfig["objects"] is not None:
				for obj in splunkConfig["objects"]:
					if obj.has_key("constraints"):
						obj["constraints"].insert(0, constraints)
			dataModel["activeVersion"]["splunkConfig"] = json.dumps(splunkConfig)
		except Exception as ex:
			pass

	# match source types methods
	def matchSourceTypesFromDataModels(self, dataModels):
		for dataModel in dataModels:
			self.matchSourceTypesFromDataModel(dataModel)

	def matchSourceTypesFromDataModel(self, dataModel):
		sourceTypes = self.matchSourceTypes(dataModel["dataSources"])
		if len(sourceTypes) == 0:
			self.saveGenericDataModel(dataModel)
		else:
			self.matchFieldsFromSourceTypes(sourceTypes, dataModel)
			self.saveTypedDataModel(dataModel, sourceTypes)

	def pairSourceTypeWithDataModel(self, dataModelId, sourceTypeName, splunkSourceTypeName):
		dataModel = self.dataModelStorage.mergeDataModel(self.getDataModel(dataModelId), onlyInstalledDataSources = True)
		dataSource = filter(lambda dataSource: dataSource["name"] == sourceTypeName or dataSource["name"] == splunkSourceTypeName, dataModel["dataSources"])
		if len(dataSource) == 0:
			dataSource = {
				"name": sourceTypeName,
				"splunkSourceTypes": [],
			}
			dataModel["dataSources"].append(dataSource)
		else:
			dataSource = dataSource[0]

		if (len(filter(lambda splunkDataSource: splunkDataSource["splunkName"] == splunkSourceTypeName, dataSource["splunkSourceTypes"])) == 0):
			dataSource["splunkSourceTypes"].append({
				"splunkName": sourceTypeName,
			})
		else:
			dataSource["splunkSourceTypes"] = filter(lambda splunkDataSource: splunkDataSource["splunkName"] != splunkSourceTypeName, dataSource["splunkSourceTypes"])
			dataModelPrimaryTag = dataModel["selectedPrimarySplunkTag"] if dataModel.has_key("selectedPrimarySplunkTag") else None
			self.deleteSplunkEventType("CorrelationX " + sourceTypeName + " " + dataModelPrimaryTag if dataModelPrimaryTag is not None else "CorrelationX " + sourceTypeName)
		self.matchSourceTypesFromDataModel(dataModel)
		return self.dataModelStorage.getDataModel(dataModel["name"])

	def matchSourceTypes(self, sourceTypes):
		return filter(lambda sourceType: sourceType is not None, map(lambda sourceType: self.matchSourceType(sourceType), sourceTypes))

	def matchSourceType(self, sourceType):
		names = []
		if sourceType.has_key("dataSourceId"):
			names.append({
				"name": sourceType["name"],
				"dataSourceSearchType": 0,
			})
		if sourceType.has_key("splunkSourceTypes"):
			names += map(lambda item: { "name": item["splunkName"], "dataSourceSearchType": 0 }, sourceType["splunkSourceTypes"])
		if sourceType.has_key("alternateNames"):
			names.extend(sourceType["alternateNames"])

		if not sourceType.has_key("splunkSourceTypes"):
			sourceType["splunkSourceTypes"] = []

		result = self.findSourceTypesByAlternateNames(names) if names else []
		if result:
			sourceType["splunkSourceTypes"] += map(lambda item: { "splunkName": item }, filter(lambda item: len(filter(lambda splunkSourceType: item == splunkSourceType["splunkName"], sourceType["splunkSourceTypes"])) == 0, result))
			return sourceType

	def matchFieldsFromSourceTypes(self, sourceTypes, dataModel):
		for sourceType in sourceTypes:
			if len(sourceType["splunkSourceTypes"]) > 0:
				self.matchFieldsFromSourceType(sourceType, dataModel) 

	def matchFieldsFromSourceType(self, sourceType, dataModel):
		for splunkSourceType in sourceType["splunkSourceTypes"]:
			fields = map(lambda item: item.fields["field"], self.getSplunkSourceTypeFields(splunkSourceType["splunkName"]))
			if splunkSourceType.has_key("fields"):
				# remove old fields
				splunkSourceType["fields"] = filter(lambda field: len(filter(lambda apiField: apiField["fieldName"] == field["fieldName"], dataModel["activeVersion"]["fields"])) > 0, splunkSourceType["fields"])
				# update existing fields
				for field in splunkSourceType["fields"]:
					apiField = filter(lambda apiField: field["fieldName"] == apiField["fieldName"], dataModel["activeVersion"]["fields"])[0]
					field["isCalculated"] = apiField["isCalculated"]
					field["isUsed"] = apiField["isUsed"]
					field["isActive"] = apiField["isActive"]
					field["aliases"] = apiField["aliases"]
				# add new fields
				splunkSourceType["fields"] += filter(lambda apiField: len(filter(lambda field: field["fieldName"] == apiField["fieldName"], splunkSourceType["fields"])) == 0, dataModel["activeVersion"]["fields"])
			else:
				splunkSourceType["fields"] = copy.deepcopy(dataModel["activeVersion"]["fields"])

			for field in fields:
				fieldName = str(field)
				dataModelField = filter(lambda item: item["fieldName"] == fieldName or len(filter(lambda alias: alias["name"] == fieldName, item["aliases"])) > 0, splunkSourceType["fields"])
				if len(dataModelField) > 0:
					for fieldItem in dataModelField:
						if not fieldItem.has_key("isMatched"):
							fieldItem["isMatched"] = True
							fieldItem["matchedField"] = fieldName
							if fieldItem["fieldName"] != fieldName:
								self.setSplunkFieldAlias(splunkSourceType["splunkName"], fieldName, fieldItem["fieldName"])

	def reassignDataModelSourceTypeField(self, dataModelId, sourceTypeName, splunkSourceTypeName, reassignArray):
		dataModel = self.dataModelStorage.mergeDataModel(self.getDataModel(dataModelId), onlyInstalledDataSources = True)
		sourceType = filter(lambda dataSource: dataSource["name"] == sourceTypeName, dataModel["dataSources"])

		for field in reassignArray:
			splunkSourceType = filter(lambda item: item["splunkName"] == splunkSourceTypeName, sourceType[0]["splunkSourceTypes"])
			if len(splunkSourceType) > 0:
				dataModelField = filter(lambda item: item["fieldName"] == field["name"], splunkSourceType[0]["fields"])
				if len(dataModelField) > 0:
					if field.has_key("newMatch"):
						dataModelField[0]["isMatched"] = True
						dataModelField[0]["matchedField"] = field["newMatch"]
						if field["name"] != field["newMatch"]:
							self.setSplunkFieldAlias(splunkSourceType[0]["splunkName"], field["newMatch"], field["name"], field["oldMatch"] if field.has_key("oldMatch") else None)
					else:
						dataModelField[0]["isMatched"] = False
						dataModelField[0]["matchedField"] = None
						self.setSplunkFieldAlias(splunkSourceType[0]["splunkName"], field["newMatch"], field["name"], field["oldMatch"] if field.has_key("oldMatch") else None)

		self.matchSourceTypesFromDataModel(dataModel)

		return self.dataModelStorage.getDataModel(dataModel["name"])

	def findSourceTypesByAlternateNames(self, alternateNames):
		result = []
		for alternateName in alternateNames:
			found = self.findSourceTypesByAlternateName(alternateName)
			result += filter(lambda foundItem: len(filter(lambda resultItem: foundItem == resultItem, result)) == 0, found)
		return result

	def findSourceTypesByAlternateName(self, alternateName):
		self.loadSplunkSourceTypes()
		return filter(lambda sourceType: self.compareSourceTypeWithAlternateName(sourceType, alternateName), self.splunkSourceTypes)

	def compareSourceTypeWithAlternateName(self, sourceTypeName, alternateName):
		sourceTypeName = sourceTypeName.lower()
		alternateNameText = alternateName["name"].lower()
		if alternateName["dataSourceSearchType"] == 0:
			return sourceTypeName == alternateNameText
		else:
			return sourceTypeName in alternateNameText or alternateNameText in sourceTypeName


# helper functions
def getApi(path, apiToken, sessionKey):
	try:
		return requests.get(globals.API_HOST + path, headers = {
			"Accept": "application/json",
			"Authorization": "Bearer " + apiToken,
		}, proxies = globals.getProxiesByAuthString(sessionKey), verify = not '.smartru.com' in globals.API_HOST).json()
	except:
		return

def getEntitiesList(entityPath, sessionKey, namespace = "SA-CorrelationX"):
	try:
		return splunk.entity.getEntitiesList(entityPath, namespace = namespace, owner = "nobody", sessionKey = sessionKey, count = -1)
	except:
		return []

def getEntity(entityPath, entityName, sessionKey):
	try:
		return splunk.entity.getEntity(entityPath, entityName, namespace = "SA-CorrelationX", owner = "nobody", sessionKey = sessionKey)
	except:
		return

def setEntity(entityPath, entityName, sessionKey, isGlobal = "True", **kwargs):
	try:
		result = splunk.entity.Entity(entityPath, entityName, namespace = "SA-CorrelationX", owner = "nobody")
		for (name, value) in kwargs.items():
			result[name] = value
		splunk.entity.setEntity(result, sessionKey = sessionKey)

		try:
			acl = splunk.entity.Entity(entityPath + "/" + entityName, "acl", namespace = "SA-CorrelationX", owner = "nobody")
			acl["owner"] = "nobody"
			acl["sharing"] = "global" if self.isGlobal == "True" else "app"
			splunk.entity.setEntity(acl, sessionKey = self.sessionKey)
		except Exception as ex:
			pass

		return True
	except:
		return False
