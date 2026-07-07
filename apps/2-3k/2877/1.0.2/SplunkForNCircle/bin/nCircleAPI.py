import xmlrpclib
import sys
import os
import json

# Get Item from the server, all attributes - no filtering
def _getItem(server, session, list, item):
    if not list.get(item):
        list[item] = server.call(session, item, 'getAttributes', {})
    return list[item]

# Print dict output, filter out non printable characters
def _printJson(output):
    i = 0
    for name,data in output.items():
        i += 1
        if type(data) == unicode or type(data) == str:
            data = data.encode('ascii','ignore')
        data = str(data).replace("\n", ':')
        print "\"%s\": \"%s\"" % (name, data),
	if i<len(output):
		print ",",

# Login to nCircle API
def _login(host, user, password):
	try:
		server = xmlrpclib.ServerProxy('https://' + host + '/api2xmlrpc')
		session = server.login(2, 0, user, password)
		return (server, session)
		
	except xmlrpclib.Fault, fault:
		print "xmlrpclib fault: %d %s" % (fault.faultCode, fault.faultString)
		sys.exit(1)
	except xmlrpclib.ProtocolError, error:
		print "xmlrpclib protocol error: %d %s" % (error.errcode, error.errmsg)
		sys.exit(1)
	
# Logout from nCircle API	
def _logout(server, session):
	server.logout(session)
	
# Get config file where values are stored in json format
def _getConfigFile(configFile):
	jsonStruct = {}

	try:
		f = open(configFile, "r")
		data = f.readline()
		#print data
		jsonStruct = json.loads(data)
		f.close()			
	
	except:
		print "getConfigFile: Warning: Cannot read config file or wrong json structure!"		
	return jsonStruct

# Store config file in plain text file in json structure		
def _putConfigFile(configFile, jsonStruct):

	try:
		data = json.dumps(jsonStruct)		
		f = open(configFile,"w+")		
		f.write(data)
		f.close()	
	except:
		print "putConfigFile: Warning: Cannot write config file or wrong json structure!"
		
