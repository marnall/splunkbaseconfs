# Import the required libraries
import xmlrpclib
import sys
import os
import nCircleAPI
from splunk.clilib.cli_common import getMergedConf

# nCircle Variables
config_file = 'ncircle'
counter_file = '/opt/splunk/etc/apps/SplunkForNCircle/bin/counter_file.txt'

latest_counter = 211000

_TIMEOUT = 5
for key in getMergedConf(config_file).keys():
	try:
		host = getMergedConf(config_file)[key]['host']
		user = getMergedConf(config_file)[key]['username']
		password = getMergedConf(config_file)[key]['password']
		
		#print host
		#print user
		#print password

		jsonStruct = nCircleAPI._getConfigFile(counter_file)
		if not jsonStruct.get(host + user + "_maxId"):
			jsonStruct[host + user + "_maxId"] = latest_counter

		try:
			# Connect to the server and login
			(server, session) = nCircleAPI._login(host, user, password)
			
			# Construct query to get latest audit records
			result = server.call(session, 'SESSION', 'getUserObject', {})
			params = {}
			params['query'] = "id > \'%s\'" % (jsonStruct[host + user + "_maxId"])
				
			newAuditRecords = server.call(session, 'class.AuditLog', 'search', params)
			if newAuditRecords:
				for newAuditRecord in newAuditRecords:
					result = ''
					result = server.call(session, newAuditRecord, 'getAttributes', {})
					print "{",
					nCircleAPI._printJson(result)
					print "}"
					#print result
			
				# Max ID is stored in latest result
				jsonStruct[host + user + "_maxId"] = result['id']
			
			# Safe Logout
			nCircleAPI._logout(server, session)

		except xmlrpclib.Fault, fault:
			print "xmlrpclib fault: %d %s" % (fault.faultCode, fault.faultString)
			sys.exit(1)
		except xmlrpclib.ProtocolError, error:
			print "xmlrpclib protocol error: %d %s" % (error.errcode, error.errmsg)
			sys.exit(1)
			
			
		nCircleAPI._putConfigFile(counter_file, jsonStruct)
	except:
		pass
# exit
sys.exit(0)
