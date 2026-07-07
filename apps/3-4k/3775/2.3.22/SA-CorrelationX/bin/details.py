#!/usr/bin/python

import json
import sys,csv,splunk.Intersplunk,splunk.saved,string,re,os,platform
import requests
import globals

from savedsearchstorage import SavedSearchStorage


def main():
	results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
	(isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
	if len(sys.argv) < 3:
		splunk.Intersplunk.parseError("No arguments provided")
		sys.exit(0)

	token = sys.argv[1].strip()
	contentId = sys.argv[2].strip()

	authString = settings.get("authString", None)
	if authString == None:
		output.writerow(["False"])
		exit

	start = authString.find('<username>') + 10
	stop = authString.find('</username>')
	user = authString[start:stop]

	start = authString.find('<authToken>') + 11
	stop = authString.find('</authToken>')
	authToken = authString[start:stop]

	try:
		savedSearchStorage = SavedSearchStorage(token, authToken)
		savedSearches = savedSearchStorage.load()

		content = savedSearchStorage.getContentById(contentId)

		fields = []
		try:
			#if content.has_key("dataModelFields"):
			#	fields += map(lambda dataModelField: dataModelField["fieldName"], content["dataModelFields"])
			if content.has_key("fieldsToGroupBy"):
				fields += map(lambda dataModelField: dataModelField["fieldName"], content["fieldsToGroupBy"])
		except:
			pass

		output = csv.writer(sys.stdout)
		output.writerow([
			"ContentId",
			"Name",
			"Description",
			"Platform",
			"DataSources",
			"Protocols",
			"Type",
			"Syntax",
			"LookbackStartTime",
			"LookbackEndTime",
			"CronSchedule",
			"AuthorNotes",
			"Throttling",
			"ThrottlingTiming",
			"DataModelFields",
			"NotableEventTitle",
			"NotableEventDescription",
			"ContentSecurityDomain",
			"ContentSeverity",
			"DrillDownName",
			"DrillDownSearch",
			"KillChainPhases",
			"IsSaved",
			"Rate",
			"AttachmentsCount",
			"SyntaxModifiedOn",
			"SyntaxModifiedBy",
			"DownloadsCount",
		])
		output.writerow([
			content["contentId"],
			content["name"],
			content["description"],
			content["platform"]["name"],
			", ".join(map(lambda x: x["type"] + " - " + x["name"], content["dataSources"])) if content.has_key("dataSources") and len(content["dataSources"]) > 0 else "Not defined",
			", ".join(map(lambda x: x["name"], content["protocols"])) if content.has_key("protocols") and len(content["protocols"]) > 0 else "Not defined",
			content["type"]["name"],
			content["syntax"] if content.has_key("syntax") and len(content["syntax"]) > 0 else None,
			content["lookbackStartTime"] if content.has_key("lookbackStartTime") else "Not defined",
			content["lookbackEndTime"] if content.has_key("lookbackEndTime") else "Not defined",
			content["cronSchedule"] if content.has_key("cronSchedule") else "Not defined",
			content["authorNotes"] if content.has_key("authorNotes") else "None",
			content["throttling"] if content.has_key("throttling") else "",
			content["throttlingTiming"] if content.has_key("throttlingTiming") else "",
			",".join(fields),
			content["notableEventTitle"] if content.has_key("notableEventTitle") else "",
			content["notableEventDescription"] if content.has_key("notableEventDescription") else "",
			content["contentSecurityDomain"] if content.has_key("contentSecurityDomain") else "",
			content["contentSeverity"] if content.has_key("contentSeverity") else "",
			content["drillDownName"] if content.has_key("drillDownName") else "",
			content["drillDownSearch"] if content.has_key("drillDownSearch") else "",
			",".join(map(lambda killChainPhase: str(killChainPhase["killChainPhaseId"]), content["killChainPhases"])) if content.has_key("killChainPhases") and len(content["killChainPhases"]) else "",
			len(filter(lambda savedSearch: savedSearch["contentId"] == content["contentId"], savedSearches)) > 0,
			content["rate"] if content.has_key("rate") else 0,
			len(content["contentResources"]) if content.has_key("contentResources") else 0,
			content["syntaxModifiedOn"] if content.has_key("syntaxModifiedOn") else "",
			content["syntaxModifiedBy"] if content.has_key("syntaxModifiedBy") else "",
			content["downloadsCount"] if content.has_key("downloadsCount") else 0,
		])

	except Exception as e:
		splunk.Intersplunk.parseError(str(e))

main()
