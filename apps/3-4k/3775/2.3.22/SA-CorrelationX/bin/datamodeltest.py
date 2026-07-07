#!/usr/bin/python

import json
import sys,csv,splunk.Intersplunk,splunk.saved,string,re,os,platform
import splunk.entity,splunk.version
import requests
import globals
import datamodel


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
			"Entity",
			"Values",
		])

		service = datamodel.DataModel(token, authToken)

		output.writerow([
			"DataModels",
			map(lambda item: item.name, service.getSplunkDataModels()),
		])
		output.writerow([
			"SourceTypes",
			service.getSplunkSourceTypes(),
		])
		output.writerow([
			"EventTypes",
			map(lambda item: item.name, service.getSplunkEventTypes()),
		])
		output.writerow([
			"Fields",
			map(lambda item: item.name, service.getSplunkFields()),
		])
		output.writerow([
			"FieldAliases",
			map(lambda item: item.name, service.getSplunkFieldAliases()),
		])
		output.writerow([
			"FieldsBySourceType",
			map(lambda item: item.fields["field"], service.getSplunkSourceTypeFields("access_combined_wcookie")),
		])
		output.writerow([
			"SetFieldAlias",
			service.setSplunkFieldAlias("www1/secure", "hostt", "host"),
		])
		output.writerow([
			"RefreshDataModels",
			service.refreshDataModels(),
		])

	except Exception as e:
		splunk.Intersplunk.parseError(str(e))

main()
