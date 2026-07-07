#!/usr/bin/python

import sys,csv,splunk.Intersplunk,string,re,os,platform
import json
import splunk.search

from savedsearchstorage import SavedSearchStorage

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

		savedSearchStorage = SavedSearchStorage(token, authToken)

		output = csv.writer(sys.stdout)
		output.writerow([
			"_time",
			"count",
		])

		items = savedSearchStorage.getHistoricalData()
		for item in items:
			output.writerow([
				item["_time"],
				item["count"],
			])

	except Exception as e:
		splunk.Intersplunk.parseError(str(e))


main()
