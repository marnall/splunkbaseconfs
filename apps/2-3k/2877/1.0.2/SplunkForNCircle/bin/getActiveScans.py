# Import the required libraries
import xmlrpclib
import xmltodict
import json
import sys
import os
import nCircleAPI
import time
from splunk.clilib.cli_common import getMergedConf

deviceProfilers = ['DP.9','DP.10','DP.11','DP.13','DP.23','DP.25','DP.26','DP.27','DP.28','DP.29','DP.33','DP.35']
config_file = "ncircle"

scanList = {}
networkList = {}

_TIMEOUT = 5
for key in getMergedConf(config_file).keys():
        try:
                host = getMergedConf(config_file)[key]['host']
                user = getMergedConf(config_file)[key]['username']
                password = getMergedConf(config_file)[key]['password']

                try:
                        # Connect to the server and login
                        (server, session) = nCircleAPI._login(host, user, password)
                        ScanConfigurations = []
                        for dp in deviceProfilers:
                                params = {}
                                params['query'] = "active = \'true\' AND dp = \'%s\'" % (dp)
                                ScanConfiguration = server.call(session, 'class.ScanConfiguration', 'search', params)
                                if ScanConfiguration:
                                        for ScanConfigurationItem in ScanConfiguration:
                                                ScanConfigurations.append(ScanConfigurationItem)

                        if ScanConfigurations:
				timestamp = str(time.time())
                                for ScanConfigurationItem in ScanConfigurations:
                                        scanProfile = server.call(session, ScanConfigurationItem, 'getAttributes', {})                 
                                        scanProfileDetail = nCircleAPI._getItem(server, session, scanList, scanProfile['scanProfile'])
                                        networkDetail = nCircleAPI._getItem(server, session, networkList, scanProfile['network'])

                                        print '{"timestamp": "' + timestamp + '", ',
                                        nCircleAPI._printJson(scanProfile)

                                        print ', "scanProfile" : ',
					scanProfileDetail['profile'] = json.dumps(xmltodict.parse(scanProfileDetail['profile']))
					#scanProfileDetail['profile'] = str(data).replace('\'','"')
					#data = str(data).replace('"{','{')
					#data = str(data).replace('}"','}')
					#scanProfileDetail['profile'] = data
					
                                        #data = nCircleAPI._printJson(scanProfileDetail)
					scanProfileDetail = str(scanProfileDetail).replace('\'','"')
					scanProfileDetail = str(scanProfileDetail).replace('"{','{')
					scanProfileDetail = str(scanProfileDetail).replace('}"','}')
					scanProfileDetail = str(scanProfileDetail).replace('True','1')				
					scanProfileDetail = str(scanProfileDetail).replace('False','0')
					print scanProfileDetail,
					#data = str(data).replace('"{','{').str(data).replace('}"','}')
					#print data

                                        print ', "network" : {',
                                        nCircleAPI._printJson(networkDetail)
                                        print "} ",

                                        print "}"
                                        # Safe Logout
                        nCircleAPI._logout(server, session)

                except xmlrpclib.Fault, fault:
                        print "xmlrpclib fault: %d %s" % (fault.faultCode, fault.faultString)
                        sys.exit(1)
                except xmlrpclib.ProtocolError, error:
                        print "xmlrpclib protocol error: %d %s" % (error.errcode, error.errmsg)
                        sys.exit(1)
                

        except:
                pass
# exit
sys.exit(0)

