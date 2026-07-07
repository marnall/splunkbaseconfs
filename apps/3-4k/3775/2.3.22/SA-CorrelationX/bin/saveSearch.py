#!/usr/bin/python

import json
import sys,csv,splunk.Intersplunk,splunk.saved,string,re,os,platform
import splunk.entity,splunk.version
import requests
import globals
import ConfigParser
import datetime

from savedsearchstorage import SavedSearchStorage

NON_ES_ALERT = '1'
ES_ALERT = '2'

CONTENT_SECURITY_DOMAIN = [ 'network', 'endpoint', 'access', 'threat', 'identity', 'audit' ]
CONTENT_SEVERITY = [ 'critical', 'high', 'medium', 'low', 'informational' ]
ADMIN = "admin"

def checkEsImports(sessionKey, user):
	try:
		update_es = splunk.entity.getEntity("data/inputs/app_imports_update", "update_es", namespace = "SplunkEnterpriseSecuritySuite", owner = ADMIN, sessionKey = sessionKey)
		if "(SA-CorrelationX)" not in update_es["app_regex"]:
			update_es["app_regex"] += "|(SA-CorrelationX)"
			update_es["disabled"] = None
			update_es["host_resolved"] = None
			splunk.entity.setEntity(update_es, sessionKey = sessionKey)
	except:
		pass

def getVersionHash(version):
	parts = version.split('.')
	return float(str(int(parts[0]) * 100 + int(parts[1])) + '.' + (parts[2] if len(parts) > 2 else '0'))

def getThrottlingInSeconds(throttling, throttlingTiming):
	if throttlingTiming == 0:
		return throttling
	elif throttlingTiming == 1:
		return throttling * 60
	elif throttlingTiming == 2:
		return throttling * 60 * 60
	elif throttlingTiming == 3:
		return throttling * 60 * 60 * 24
	elif throttlingTiming == 4:
		return throttling * 60 * 60 * 24 * 7
	elif throttlingTiming == 5:
		return throttling * 60 * 60 * 24 * 30
	elif throttlingTiming == 6:
		return throttling * 60 * 60 * 24 * 365

def main():
	(isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
	if len(sys.argv) < 4:
		splunk.Intersplunk.parseError("No arguments provided")
		sys.exit(0)

	token = sys.argv[1].strip()
	contentId = sys.argv[2].strip()
	searchType = sys.argv[3].strip()

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

	storage = SavedSearchStorage(token, authToken)

	try:
		config = ConfigParser.RawConfigParser()
		config.read('../local/proxy.conf')
		try:
			defaultSharingForDataModel = config.get('corx', 'install_datamodels_globally')
		except:
			defaultSharingForDataModel = "True"

		if searchType == ES_ALERT:
			checkEsImports(authToken, user)

		content = storage.getContentById(contentId)

		searchName = content["name"] if content.has_key("name") else None
		startTime = content["lookbackStartTime"] if content.has_key("lookbackStartTime") else None
		endTime = content["lookbackEndTime"] if content.has_key("lookbackEndTime") else None

		#abc = splunk.saved.listSavedSearches(None, authToken, user, None, 1)

		# check existing search
		output = csv.writer(sys.stdout)
		output.writerow([
			"Result",
		])

		try:
			result = splunk.entity.getEntity(splunk.saved.SAVED_SEARCHES_ENDPOINT_ENTITY_PATH, content["name"], namespace = "SA-CorrelationX", owner = ADMIN, sessionKey = authToken)
		except:
			try:
				result = splunk.entity.Entity(splunk.saved.SAVED_SEARCHES_ENDPOINT_ENTITY_PATH, content["name"], namespace = "SA-CorrelationX", owner = ADMIN)
			except:
				output.writerow([
					"True"
				])
				output.writerow([
					splunk.version.__version__
				])

		result['search'] = content["syntax"]
		result['dispatch.earliest_time'] = startTime
		result['dispatch.latest_time'] = endTime

		if getVersionHash(splunk.version.__version__) < getVersionHash('6.6.0'):
			result['description'] = content["name"]
		else:
			result['description'] = content["description"]
			result['action.email.useNSSubject'] = '1'

		if searchType == NON_ES_ALERT:
			result['name'] = content["name"]
			result['is_scheduled'] = '1'
			result['alert.suppress'] = '0'
			result['cron_schedule'] = content["cronSchedule"] if content.has_key("cronSchedule") else ""
			if getVersionHash(splunk.version.__version__) < getVersionHash('6.6.0'):
				result['auto_summarize.dispatch.earliest_time'] = startTime
			else:
				result['alert_comparator'] = 'greater than'
				result['alert_threshold'] = '0'
				result['alert_type'] = 'number of events'
				result['alert.track'] = '1'
		elif searchType == ES_ALERT:
			result['action.correlationsearch.label'] = content["name"]
			result['schedule_window'] = 'auto'
			result['schedule_priority'] = 'default'
			result['realtime_schedule'] = '1'
			result['is_scheduled'] = '1'
			result['request.ui_dispatch_app'] = 'SplunkEnterpriseSecuritySuite'
			result['actions'] = 'notable'
			result['action.correlationsearch.enabled'] = '1'
			result['action.notable.param.drilldown_name'] = content['drillDownName'] if content.has_key("drillDownName'") else ""
			result['action.notable.param.drilldown_search'] = content['drillDownSearch'] if content.has_key("drillDownSearch'") else ""
			result['cron_schedule'] = content["cronSchedule"] if content.has_key("cronSchedule") else ""

			fields = []
			try:
				#if content.has_key("dataModelFields"):
				#	fields += map(lambda dataModelField: dataModelField["fieldName"], content["dataModelFields"])
				if content.has_key("fieldsToGroupBy"):
					fields += map(lambda dataModelField: dataModelField["fieldName"], content["fieldsToGroupBy"])
			except:
				pass

			result['alert.suppress'] = '1'
			result['alert.suppress.fields'] = ",".join(fields)
			result['alert.suppress.period'] = str(getThrottlingInSeconds(content["throttling"], content["throttlingTiming"])) + "s" if content.has_key("throttling") else "0s"
			#result['alert.suppress.fields'] = 'field1,field2,field3' need to add in database (Fields to group by)

			# need to add events table in database
			# result['action.notable.param.next_steps'] = '{"version":1,"data":"[[action|ping]]"}'
			result['action.notable.param.rule_description'] = content["notableEventDescription"] if content.has_key("notableEventDescription") else ""
			result['action.notable.param.rule_title'] = content["notableEventTitle"] if content.has_key("notableEventTitle") else ""
			result['action.notable.param.security_domain'] = CONTENT_SECURITY_DOMAIN[content["contentSecurityDomain"]] if content.has_key("contentSecurityDomain") else ""
			result['action.notable.param.severity'] = CONTENT_SEVERITY[content["contentSeverity"]] if content.has_key("contentSeverity") else ""
			result['action.notable.param.drilldown_name'] = content["drillDownName"] if content.has_key("drillDownName") else ""
			result['action.notable.param.drilldown_search'] = content["drillDownSearch"] if content.has_key("drillDownSearch") else ""

			result['alert.digest_mode'] = '1'
			result['alert.expires'] = '24h'
			result['alert.severity'] = '3'
			result['alert.track'] = '0'
			result['alert_comparator'] = 'greater than'
			result['alert_threshold'] = '0'
			result['alert_type'] = 'number of events'
			result['dispatchAs'] = 'owner'
			result['dispatch_rt_backfill'] = '1'
			result['action.customsearchbuilder.enabled'] = '0'

		splunk.entity.setEntity(result, sessionKey=authToken)

		if searchType != ES_ALERT: #and getVersionHash(splunk.version.__version__) >= getVersionHash('6.6.0'):
			acl = splunk.entity.Entity(splunk.saved.SAVED_SEARCHES_ENDPOINT_ENTITY_PATH + '/' + content["name"].replace("/", "%2F"), 'acl', namespace="SA-CorrelationX", owner=ADMIN)
			acl['owner'] = ADMIN
			acl['sharing'] = 'global' if defaultSharingForDataModel == 'True' else 'app'
			splunk.entity.setEntity(acl, sessionKey=authToken)

		if searchType == ES_ALERT: #and getVersionHash(splunk.version.__version__) >= getVersionHash('6.6.0'):
			acl = splunk.entity.Entity(splunk.saved.SAVED_SEARCHES_ENDPOINT_ENTITY_PATH + '/' + content["name"].replace("/", "%2F"), 'acl', namespace="SA-CorrelationX", owner=ADMIN)
			acl['owner'] = ADMIN
			acl['sharing'] = 'global' if defaultSharingForDataModel == 'True' else 'app'
			acl['app'] = 'SplunkEnterpriseSecuritySuite'
			splunk.entity.setEntity(acl, sessionKey=authToken)

		storage.saveSavedSearch(content)
		output.writerow([
			"True",
		])
		output.writerow([
			splunk.version.__version__
		])

	except Exception as e:
		splunk.Intersplunk.parseError(str(e))

main()
