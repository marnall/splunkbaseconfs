################################################################################
# Copyright (c) 2016 <AlgoSec Systems Ltd.>                                    #
# All Rights Reserverd.                                                        #
#                                                                              #
# Permission is hereby granted, free of charge, to any person obtaining a copy #
# of this software and associated documentation files (the "Software"), to     #
# deal in the Software without restriction, including without limitation the   #
# rights to use, copy, modify, merge, publish, distribute and/or sublicense,   #
# and to permit persons to whom the Software is furnished to do so, subject to #
# the following conditions:                                                    #
#                                                                              #
# The above copyright notice and this permission notice shall be included in   #
# all copies or substantial portions of the Software.                          #
#                                                                              #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR   #
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,     #
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE  #
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER       #
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING      #
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS #
# IN THE SOFTWARE.                                                             #
################################################################################

import re, collections, json, csv, sys, urllib, urllib2, splunk.Intersplunk, string

import sys
from tab_splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
import datetime
import splunk.clilib.cli_common
import time
import json
import ssl
import requests
from SOAPpy import SOAPProxy
from authSession import *


# Issue queries in AFA

# Skip SSL certificate verification (to allow self-signed certificates on AlgoSec server)
ssl._create_default_https_context = ssl._create_unverified_context

conf = splunk.clilib.cli_common.getConfStanza('TA-AlgoSec_Incident_Handling2_customized', 'AlgoSec_Server')
AlgoSec_IP = conf['content']
conf = splunk.clilib.cli_common.getConfStanza('TA-AlgoSec_Incident_Handling2_customized', 'AlgoSec_Username')
AlgoSec_user = conf['content']

AFA_WSDL = "https://"+AlgoSec_IP+"/AFA/php/ws.php?wsdl"
namespace = 'https://www.algosec.com/afa-ws'


@Configuration(local=True)
class AFAQuery(GeneratingCommand):
	QuerySource = Option(name='src', require=True, doc="Traffic Simulation Query Source IP or range")
	QueryDest = Option(name='dst', require=True, doc="Traffic Simulation Query Desintation IP or range")

	QueryService='*'

	def generate(self):
		AlgoSec_pwd = getCredentials(sessionToken)

		server = SOAPProxy(AFA_WSDL, namespace)
		SessionID = server.ConnectRequest(UserName=AlgoSec_user, Password=AlgoSec_pwd, Domain='')

		Results = ()
		
		QueryParams = {'Source': self.QuerySource, 'Destination': self.QueryDest, 'Service': self.QueryService}
		QueryResult = server.QueryRequest(SessionID=SessionID, QueryInput=QueryParams).QueryResult

		no_results = False
		if (QueryResult == None):
			no_results = True
		elif type(QueryResult.QueryItem.Device) is list:
			for FW in QueryResult.QueryItem.Device:
				Results += ("Device [" + FW.DeviceName + "]: " + FW.IsAllowed,)
		else:
			FW = QueryResult.QueryItem.Device
			Results = ("Device [" + FW.DeviceName + "]: " + FW.IsAllowed,)

		response = server.DisconnectRequest(SessionID=SessionID)

		temp = dict()
		if no_results:
			temp['Results'] = "No Results Found"
			temp['Details'] = ""
		else:
			temp['Results'] = ", ".join(Results)
			temp['Details'] = QueryResult.QueryHTMLPath
		
		temp['_raw'] = str(temp)
		yield temp


if __name__ == '__main__':
	sessionXml = sys.stdin.read()
	start = sessionXml.find('<authToken>') + 11
	stop = sessionXml.find('</authToken>')
	sessionToken = sessionXml[start:stop]
	sessionToken = urllib2.unquote(sessionToken.encode('ascii')).decode('utf-8')
	
	if len(sessionToken) == 0:
		sys.stderr.write("Did not receive a session key from splunkd. Please enable passauth in commands.conf for this script\n")
		exit(2)

	dispatch(AFAQuery, sys.argv, sys.stdin, sys.stdout, __name__)
	


