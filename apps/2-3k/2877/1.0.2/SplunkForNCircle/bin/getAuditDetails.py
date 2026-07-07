# Get audit records from nCircle
# - we need to have list of deviceProfilers defined from which the audit records will be fetched
# - max IDs are fetched from audit_file to fetch only latest audit records for each profiler

import nCircleAPI
import xmlrpclib
import sys
import os
import json
from splunk.clilib.cli_common import getMergedConf

# nCircle Variables
audit_file = '/opt/splunk/etc/apps/SplunkForNCircle/bin/audit.json'
blg = 6445

deviceProfilers = ['DP.9','DP.10','DP.11','DP.13','DP.23','DP.25','DP.26','DP.27','DP.28','DP.29','DP.33','DP.35']

# Internal dicts
storedAuditIDs = {}
vulnList = {}
hostList = {}
osList = {}
config_file = 'ncircle'


# Get the audit records
_TIMEOUT = 5
for key in getMergedConf(config_file).keys():
	try:
		host = getMergedConf(config_file)[key]['host']
		user = getMergedConf(config_file)[key]['username']
		password = getMergedConf(config_file)[key]['password']
		
		# Get the latest Audit IDs for each device profiler
		storedAuditIDs = nCircleAPI._getConfigFile(audit_file)

		try:
			# Connect to the server and login
			(server, session) = nCircleAPI._login(host, user, password)

			# Find new audits for each device profilers
			for deviceProfiler in deviceProfilers:
			
				#get latest AuditID into the condition for fetching the audit records
				if not storedAuditIDs.get(deviceProfiler):			
					storedAuditIDs[deviceProfiler] = blg	#bulgarian constant to get audits from ID 5000
					storedAuditID = blg
				else:
					storedAuditID = storedAuditIDs[deviceProfiler]
					
				params = {}
				params['query'] = "id>%s AND dp=\'%s\'" % (storedAuditID, deviceProfiler)
				
				# Audit results are stored under IDs
				auditResultIDs = server.call(session, 'class.Audit', 'search', params)
				if auditResultIDs:
					for auditResultID in auditResultIDs:
			
						# Store max audit ID for future - fetch only new records in next run
						if auditResultID.split(".")[1] > storedAuditIDs[deviceProfiler]:
							storedAuditIDs[deviceProfiler] = auditResultID.split(".")[1]
								
						params = {}
						params['query'] = "audit=\'%s\'" % (auditResultID)
						
						# Vulnerabilities for particular hosts are stored under VulnResult IDs
						vulnResultIDs = server.call(session, 'class.VulnResult', 'search', params)
									
						if vulnResultIDs:
							for vulnResultID in vulnResultIDs:
							
								vulnResult = {}
								vulnDetail = {}
								hostDetail = {}
								osDetail = {}
								
								vulnResult = server.call(session, vulnResultID, 'getAttributes', {})
								
								# Get additional details that are being referenced in the vulnResult
								vulnDetail = nCircleAPI._getItem(server, session, vulnList, vulnResult['vuln'])
								hostDetail = nCircleAPI._getItem(server, session, hostList, vulnResult['host'])
								osDetail = nCircleAPI._getItem(server, session, osList, hostDetail['os'])
								print "{",
								nCircleAPI._printJson(vulnResult)

								print ', "VulnDetail" : {',
								nCircleAPI._printJson(vulnDetail)
								print "},",

								print '"hostDetail" : {',
								nCircleAPI._printJson(hostDetail)
								print "},",
								
								print '"osDetail" : {',
								nCircleAPI._printJson(osDetail)
								print "}",
								print "}"
								
						# Store the latest Audit IDs for each device profiler
						nCircleAPI._putConfigFile(audit_file, storedAuditIDs)
						
			# Logout from server
			nCircleAPI._logout(server, session)
			

		except xmlrpclib.Fault, fault:
			print "xmlrpclib fault: %d %s" % (fault.faultCode, fault.faultString)
			sys.exit(1)
		except xmlrpclib.ProtocolError, error:
			print "xmlrpclib protocol error: %d %s" % (error.errcode, error.errmsg)
			sys.exit(1)

			
		# Store the latest Audit IDs for each device profiler
		nCircleAPI._putConfigFile(audit_file, storedAuditIDs)

	except:
		pass

# Exit
sys.exit(0)
