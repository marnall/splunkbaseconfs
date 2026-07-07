#!/usr/bin/python

# app shared configuration
import globals
# python modules
import json
import datetime
import requests
# splunk modules
import splunk.search


class SavedSearchStorage:

	def __init__(self, apiToken, sessionKey):
		self.apiToken = apiToken
		self.sessionKey = sessionKey

	def load(self, hideRemoved = True):
		try:
			with open("../local/savedsearch.json") as savedSearchFile:
				result = json.load(savedSearchFile)
				if hideRemoved:
					result = filter(lambda item: not item.has_key("deletedOn"), result)
				return result
		except:
			return []

	def loadAll(self):
		return self.load(hideRemoved = False)

	def save(self, savedSearches):
		try:
			with open("../local/savedsearch.json", "w") as savedSearchFile:
				json.dump(savedSearches, savedSearchFile)
			return True
		except:
			return False

	def getSavedSearch(self, contentId, savedSearches = None):
		if savedSearches is None:
			savedSearches = self.loadAll()
		result = filter(lambda savedSearch: savedSearch["contentId"] == contentId and not savedSearch.has_key("deletedOn"), savedSearches)
		if len(result) > 0:
			return result[0]

	def saveSavedSearch(self, apiSavedSearch):
		savedSearches = self.loadAll()
		savedSearch = self.getSavedSearch(apiSavedSearch["contentId"], savedSearches)

		if savedSearch is None:
			savedSearch = {
				"contentId": apiSavedSearch["contentId"],
				"createdOn": str(datetime.datetime.now()),
				"name": apiSavedSearch["name"],
			}
			savedSearches.append(savedSearch)

		if apiSavedSearch.has_key("killChainPhases"):
			savedSearch["killChainPhases"] = map(lambda killChainPhase: killChainPhase["killChainPhaseId"], apiSavedSearch["killChainPhases"])
		else:
			savedSearch["killChainPhases"] = []

		self.save(savedSearches)

	def deleteSavedSearch(self, contentId, savedSearches = None):
		if savedSearches is None:
			savedSearches = self.loadAll()

		removedSearches = filter(lambda savedSearch: savedSearch["contentId"] == contentId and not savedSearch.has_key("deletedOn"), savedSearches)
		for item in removedSearches:
			item["deletedOn"] = str(datetime.datetime.now())

		self.save(savedSearches)

	def refreshSavedSearchesBasedOnExistence(self, savedSearches = None):
		if savedSearches is None:
			savedSearches = self.loadAll()

		splunkSearches = splunk.search.searchAll("| rest /servicesNS/-/SA-CorrelationX/saved/searches/ count=0", sessionKey = self.sessionKey)

		removedSearches = filter(lambda savedSearch: not savedSearch.has_key("deletedOn") and len(filter(lambda splunkSearch: str(splunkSearch["title"]) == savedSearch["name"], splunkSearches)) == 0, savedSearches)
		for item in removedSearches:
			item["deletedOn"] = str(datetime.datetime.now())

		installedSearchesNotSaved = filter(lambda splunkSearch: len(filter(lambda savedSearch: not savedSearch.has_key("deletedOn") and str(splunkSearch["title"]) == savedSearch["name"], savedSearches)) == 0, splunkSearches)
		contentIds = self.getContentIdsByNames(map(lambda splunkSearch: str(splunkSearch["title"]), installedSearchesNotSaved))

		searches = []
		for i in range(0, len(installedSearchesNotSaved)):
			if contentIds[i] is not None:
				searches.append({
					"contentId": contentIds[i],
					"createdOn": str(installedSearchesNotSaved[i]["updated"]),
					"name": str(installedSearchesNotSaved[i]["title"]),
				})

		contentKillChains = self.getKillChainsPhasesByContentIds(map(lambda search: search["contentId"], searches))
		for i in range(0, len(searches)):
			searches[i]["killChainPhases"] = contentKillChains[i]

		savedSearches += searches

		self.save(savedSearches)

	def getHistoricalData(self):
		savedSearches = self.loadAll()

		if len(savedSearches) > 0:
			startDate = min(map(lambda item: datetime.datetime.strptime(item["createdOn"][:10], "%Y-%m-%d"), savedSearches))
		else:
			startDate = datetime.datetime.today()
		endDate = datetime.datetime.today() + datetime.timedelta(days = 1)

		count = 0
		result = []
		for date in daterange(startDate, endDate):
			dateFormatted = date.strftime("%Y-%m-%d")

			createdCount = len(filter(lambda item: item["createdOn"][:10] == dateFormatted, savedSearches))
			deletedCount = len(filter(lambda item: item.has_key("deletedOn") and item["deletedOn"][:10] == dateFormatted, savedSearches))
			count = count + createdCount - deletedCount

			result.append({
				"_time": dateFormatted,
				"count": count,
			})

		return result

	def getKillChainPhases(self):
		return getApi("/api/content/getKillChainPhases", self.apiToken, self.sessionKey)

	def getContentById(self, contentId):
		result = getApi("/api/content?id=" + contentId, self.apiToken, self.sessionKey)

		try:
			with open("../local/modifiedsearch.json") as modifiedsearch:
				modifiedItems = json.load(modifiedsearch)
				if modifiedItems.has_key(contentId):
					result["syntax"] = modifiedItems[contentId]["syntax"]
					result["syntaxModifiedOn"] = modifiedItems[contentId]["syntaxModifiedOn"]
					result["syntaxModifiedBy"] = modifiedItems[contentId]["syntaxModifiedBy"]
		except:
			pass

		return result

	def updateContentSyntax(self, contentId, syntax, username):
		try:
			with open("../local/modifiedsearch.json") as modifiedsearchRead:
				items = json.load(modifiedsearchRead)
		except Exception as ex:
			items = {}

		items[contentId] = {
			"syntax": syntax,
			"syntaxModifiedOn": str(datetime.datetime.now()),
			"syntaxModifiedBy": username,
		}
		try:
			with open("../local/modifiedsearch.json", "w") as modifiedsearchWrite:
				json.dump(items, modifiedsearchWrite)
			return True
		except:
			return False

	def getContentIdsByNames(self, names):
		try:
			return requests.post(globals.API_HOST + "/api/content/getContentIdsByNames", data = json.dumps(names), headers = {
				"Accept": "application/json",
				"Authorization": "Bearer " + self.apiToken,
				"Content-Type": "application/json",
			}, proxies = globals.getProxiesByAuthString(self.sessionKey), verify = not '.smartru.com' in globals.API_HOST).json()
		except:
			return []

	def getKillChainsPhasesByContentIds(self, contentIds):
		try:
			return requests.post(globals.API_HOST + "/api/content/getKillChainsPhasesByContentIds", data = json.dumps(contentIds), headers = {
				"Accept": "application/json",
				"Authorization": "Bearer " + self.apiToken,
				"Content-Type": "application/json",
			}, proxies = globals.getProxiesByAuthString(self.sessionKey), verify = not '.smartru.com' in globals.API_HOST).json()
		except:
			return []

# helper functions
def getApi(path, apiToken, sessionKey):
	try:
		return requests.get(globals.API_HOST + path, headers = {
			"Accept": "application/json",
			"Authorization": "Bearer " + apiToken,
		}, proxies = globals.getProxiesByAuthString(sessionKey), verify = not '.smartru.com' in globals.API_HOST).json()
	except:
		return

def daterange(start_date, end_date):
	for n in range(int ((end_date - start_date).days)):
		yield start_date + datetime.timedelta(n)
