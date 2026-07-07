import nCircleAPI
import xmlrpclib
import sys
import getpass

default_ip = "10.20.30.40"
default_user = "ip360@ncircle.com"

host = raw_input("Enter IP address of nCircle IP360: [default: " + default_ip + "]: ")
if not host:
	host = default_ip

user = raw_input("Enter username [default: " + default_user + "]: ")
if not user:
	user = default_user
	
password = getpass.getpass("Password: ")

results = []
dpList = {}
dpDict = []

try:
	(server, session) = nCircleAPI._login(host, user, password)			
	print 'ncircle.conf: update this file with following content:'
	print "[vne-host]"
	print "host=" + host
	print "username=" + user
	print "password=" + password
	print
	results = server.call(session, 'class.AuditLog', 'search', {'query':'id>0'})
	if results:					
		print 'getAuditLog: IDs in range from ' + results[0].rsplit('.')[1] + ' to ' + results[-1].rsplit('.')[1]
		print "\tupdate variable called latest_counter in getAuditLog.py by number in this range"
		print "\thint: use min value if you want to fetch all audit records"
		print "\thint: use max value if you want to fetch only new audit records"
		
	print ""	
	results = server.call(session, 'class.Audit', 'search', {'query':'id>0'})	
	if results:					
		print 'getAuditDetails.py: IDs in range from ' + results[0].rsplit('.')[1] + ' to ' + results[-1].rsplit('.')[1]
		print "\tupdate variable called blg in getAuditDetails.py by number in this range"
		print "\thint: use min value if you want to fetch all audit scan records"
		print "\thint: use max value if you want to fech only new audit scan records"
	
	results = server.call(session, 'class.DP', 'search', {'query':'id>0'})
	if results:				
		print 'Device profiler setup'
		for deviceProfiler in results:
			deviceProfilerDetail = nCircleAPI._getItem(server, session, dpList, deviceProfiler)
			
			for key in ['name', 'IPAddress']:
				print key + ": " + str(deviceProfilerDetail[key])
			toInclude = "n"
			toInclude = raw_input("Do you want to include this device profiler into the app? y/n: [default: n]: ")
			if toInclude is "y" :
				dpDict.append(deviceProfiler)
			print ""
		print 'getActiveScans.py, getAuditDetails.py, getDpStats.py: update variable called deviceProfilers by this string'
		print dpDict
		print
	
	
	nCircleAPI._logout(server, session)
except xmlrpclib.Fault, fault:
	print "xmlrpclib fault: %d %s" % (fault.faultCode, fault.faultString)
	sys.exit(1)
except xmlrpclib.ProtocolError, error:
	print "xmlrpclib protocol error: %d %s" % (error.errcode, error.errmsg)
	sys.exit(1)		
except:
	pass
	

sys.exit(0)