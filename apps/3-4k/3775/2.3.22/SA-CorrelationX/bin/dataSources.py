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
	filterType = sys.argv[2].strip()

	results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
	authString = settings.get("authString", None)
	if authString == None:
		exit

	start = authString.find("<username>") + 10
	stop = authString.find("</username>")
	user = authString[start:stop]

	start = authString.find("<authToken>") + 11
	stop = authString.find("</authToken>")
	authToken = authString[start:stop]

	service = datamodel.DataModel(token, authToken)
	storage = datamodelstorage.DataModelStorage()

	try:
		if filterType == "0":
			items = requests.get(globals.API_HOST + "/api/datasource?hideEmpty=true", headers = {
				"Accept": "application/json"
			}, proxies = globals.getProxies(settings), verify = not '.smartru.com' in globals.API_HOST).json()
		elif filterType == "1":
			sourceTypes = service.getSplunkSourceTypes()
			items = requests.post(globals.API_HOST + "/api/datasource/matchSplunk", data = json.dumps(sourceTypes), headers = {
				"Accept": "application/json",
				"Authorization": "Bearer " + token,
				"Content-Type": "application/json",
			}, proxies = globals.getProxies(settings), verify = not '.smartru.com' in globals.API_HOST).json()
		elif filterType == "2":
			dataModels = map(lambda dataModel: dataModel["name"], filter(lambda dataModel: dataModel["type"] == 2, storage.load()))
			items = requests.post(globals.API_HOST + "/api/datasource/matchSplunkCim", data = json.dumps(dataModels), headers = {
				"Accept": "application/json",
				"Authorization": "Bearer " + token,
				"Content-Type": "application/json",
			}, proxies = globals.getProxies(settings), verify = not '.smartru.com' in globals.API_HOST).json()
		else:
			items = []

		output = csv.writer(sys.stdout)
		output.writerow(["DataSourceId", "Name"])

		for item in items:
			output.writerow([item["dataSourceId"], item["type"] + " - " + item["name"]])


	except Exception as e:
		splunk.Intersplunk.parseError(str(e))



main()
