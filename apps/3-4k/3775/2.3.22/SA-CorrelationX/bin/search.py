#!/usr/bin/python

import json
import sys,csv,splunk.Intersplunk,string,re,os,platform
import requests
import urllib
import globals

from datamodelstorage import DataModelStorage
from savedsearchstorage import SavedSearchStorage

def main():
	(isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
	if len(sys.argv) < 11:
		splunk.Intersplunk.parseError("No arguments provided")
		sys.exit(0)

	page = sys.argv[1].strip()
	token = sys.argv[2].strip()
	onlyFavorites = sys.argv[3].strip()
	dataSources = sys.argv[4].strip()
	protocols = sys.argv[5].strip()
	contentType = sys.argv[6].strip()
	submittedBy = sys.argv[7].strip()
	keyword = sys.argv[8].strip()
	killchains = sys.argv[9].strip()
	filterType = sys.argv[10].strip()
	hideDataModel = sys.argv[11].strip()

	results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
	authString = settings.get("authString", None)
	if authString == None:
		exit

	start = authString.find('<authToken>') + 11
	stop = authString.find('</authToken>')
	authToken = authString[start:stop]

	try:
		datamodelstorage = DataModelStorage()
		savedSearchStorage = SavedSearchStorage(token, authToken)
		savedSearches = savedSearchStorage.load()

		url = "/api/content/splunk/search?"
		params = {}

		if len(page) > 0:
			params["page"] = page
		if len(onlyFavorites) > 0:
			params["onlyFavorites"] = onlyFavorites
		if len(hideDataModel) > 0:
			params["hideDataModel"] = hideDataModel
		if len(dataSources) > 0:
			params["dataSources"] = dataSources
		if len(protocols) > 0:
			params["protocols"] = protocols
		if len(contentType) > 0:
			params["type"] = contentType
		if len(submittedBy) > 0:
			params["submittedBy"] = submittedBy
		if len(keyword) > 0:
			params["keyword"] = keyword
		if savedSearches is not None and len(savedSearches) > 0:
			params["savedSearches"] = ','.join(map(lambda savedSearch: str(savedSearch["contentId"]), savedSearches))
		if filterType == "2":
			params["dataModels"] = ",".join(map(lambda dataModel: str(dataModel["dataModelId"]), filter(lambda dataModel: dataModel["type"] == 2, datamodelstorage.load())))
		if len(killchains) > 0:
			params["killchains"] = killchains

		items = requests.post(globals.API_HOST + url + urllib.urlencode(params), headers = {
			"Accept": "application/json",
			"Authorization": "Bearer " + token,
			"Content-Type": "application/json"
		}, proxies = globals.getProxies(settings), verify = not '.smartru.com' in globals.API_HOST).json()

		output = csv.writer(sys.stdout)
		output.writerow(["Id", "Name", "Description", "DataSources", "AuthorNotes", "DataModel"])
		output.writerow(["0", "", items["total"], "", "", ""])

		for item in items["items"]:
			output.writerow([
				item["contentId"],
				item["name"],
				item["description"],
				", ".join(map(lambda x: x["type"] + " - " + x["name"], item["dataSources"])) if item.has_key("dataSources") and len(item["dataSources"]) > 0 else "Not defined",
				item["authorNotes"] if item.has_key("authorNotes") else "None",
				item["dataModel"]["name"] if item.has_key("dataModel") else "",
			])

	except Exception as e:
		#splunk.Intersplunk.parseError(str(e))
		splunk.Intersplunk.parseError("Unable to load Content" + globals.API_HOST + url + json.dumps(items))



main()
