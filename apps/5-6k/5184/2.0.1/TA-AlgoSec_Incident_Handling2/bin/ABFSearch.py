#!/usr/bin/python

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

# Parts of this have been copied from Splunks DNSLookup and other examples.
import re, collections, json, csv, sys, urllib, urllib2, splunk.Intersplunk, string

import sys
from tab_splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
import datetime
import splunk.clilib.cli_common
from splunk import Intersplunk as si
import time
import ssl, re
import requests
import urllib, urllib2
from authSession import *

# Search for business applications in ABF

conf = splunk.clilib.cli_common.getConfStanza('TA-AlgoSec_Incident_Handling2_customized', 'AlgoSec_Server')
AlgoSec_IP = conf['content']
conf = splunk.clilib.cli_common.getConfStanza('TA-AlgoSec_Incident_Handling2_customized', 'AlgoSec_Username')
AlgoSec_user = conf['content']


@Configuration(local=True)
class ABFSearch(GeneratingCommand):
	IPtoCheck = Option(name='ip', require=True, doc="IP address to search for in ABF business applications")
	Mode = Option(name='mode', require=False, doc="app_names|criticality|link|full_list")

	def generate(self):

		AlgoSec_pwd = getCredentials(sessionToken)

		response = requests.get('https://'+AlgoSec_IP+'/BusinessFlow/rest/v1/login', auth=(AlgoSec_user, AlgoSec_pwd), verify=False).json()
		#response = requests.get('https://'+AlgoSec_IP+'/BusinessFlow/rest/v1/login', auth=(AlgoSec_user, AlgoSec_pwd)).json()
		cookies = dict(JSESSIONID=response.get('jsessionid'))

		response = requests.get('https://'+AlgoSec_IP+'/BusinessFlow/rest/v1/network_objects/find/applications?address='+self.IPtoCheck, cookies=cookies, verify=False).json()
		#response = requests.get('https://'+AlgoSec_IP+'/BusinessFlow/rest/v1/network_objects/find/applications?address='+self.IPtoCheck, cookies=cookies).json()
        		
		Relevant_apps = ()
		Is_some_critical = "No critical applications impacted"
		
		for app in response:
			temp = dict()
			contacts=''
			if 'contacts' in app:
				contacts = str(app['contacts'])
		
			is_critical='Not Critical'
			if 'labels' in app:
				for label in app['labels']:
					if label['name'] == 'Critical':
						is_critical = 'Critical!!!'
						Is_some_critical = "Some of the impacted applications are Critical!"
					break
		
			Relevant_apps += (app['name'],)

			temp['server_ip'] = self.IPtoCheck
			temp['business_application'] = app['name']
			temp['ABF_application_ID'] = app['applicationID']
			temp['critical'] = is_critical
			temp['contacts'] = contacts
			temp['_time'] = int(time.time())
			temp['_raw'] = str(temp)
	
			if self.Mode == "full_list":
				yield temp
			
		response = requests.get('https://'+AlgoSec_IP+'/BusinessFlow/rest/v1/logout', cookies=cookies, verify=False).json()
		#response = requests.get('https://'+AlgoSec_IP+'/BusinessFlow/rest/v1/logout', cookies=cookies).json()
		
		tmp = dict()
		all = dict()
		
		tmp['Applications'] = ", ".join(Relevant_apps)
		all['Applications'] = ", ".join(Relevant_apps)
		tmp['_raw'] = str(tmp)
		if self.Mode == "app_names":
			yield tmp
		
		tmp = dict()
		tmp['Criticality'] = Is_some_critical
		all['Criticality'] = Is_some_critical
		tmp['_raw'] = str(tmp)
		if self.Mode == "criticality":
			yield tmp
		
		tmp = dict()
		tmp['Details'] = "https://"+AlgoSec_IP+"/BusinessFlow/#!applications/query?q=%7B%22addresses%22%3A%5B%7B%22address%22%3A%22"+self.IPtoCheck+"%22%7D%5D%2C%22devices%22%3A%5B%5D%7D"
		all['Details'] = "https://"+AlgoSec_IP+"/BusinessFlow/#!applications/query?q=%7B%22addresses%22%3A%5B%7B%22address%22%3A%22"+self.IPtoCheck+"%22%7D%5D%2C%22devices%22%3A%5B%5D%7D"
		tmp['_raw'] = str(tmp)
		if self.Mode == "link":
			yield tmp

		all['_raw'] = str(all)
		if self.Mode == "all":
			yield all
		

if __name__ == '__main__':
	
	sessionXml = sys.stdin.read()
	start = sessionXml.find('<authToken>') + 11
	stop = sessionXml.find('</authToken>')
	sessionToken = sessionXml[start:stop]
	sessionToken = urllib2.unquote(sessionToken.encode('ascii')).decode('utf-8')
	
	if len(sessionToken) == 0:
		sys.stderr.write("Did not receive a session key from splunkd. Please enable passauth in commands.conf for this script\n")
		exit(2)

	dispatch(ABFSearch, sys.argv, sys.stdin, sys.stdout, __name__)
	