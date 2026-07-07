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
dpList = {}
config_file = "ncircle"

_TIMEOUT = 5
for key in getMergedConf(config_file).keys():
        try:
                host = getMergedConf(config_file)[key]['host']
                user = getMergedConf(config_file)[key]['username']
                password = getMergedConf(config_file)[key]['password']

                try:
                        # Connect to the server and login
                        (server, session) = nCircleAPI._login(host, user, password)
                        for dp in deviceProfilers:
                                deviceProfilerDetail = nCircleAPI._getItem(server, session, dpList, dp)
                                deviceProfilerDetail['authenticationKey'] = 'anonymized'
                                print "{",
                                nCircleAPI._printJson(deviceProfilerDetail)
                                print "}"
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