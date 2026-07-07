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
import time
import ssl
from suds.client import Client
from authSession import *

conf = splunk.clilib.cli_common.getConfStanza('TA-AlgoSec_Incident_Handling2_customized', 'AlgoSec_Server')
AlgoSec_IP = conf['content']
conf = splunk.clilib.cli_common.getConfStanza('TA-AlgoSec_Incident_Handling2_customized', 'AlgoSec_Username')
AlgoSec_user = conf['content']
conf = splunk.clilib.cli_common.getConfStanza('TA-AlgoSec_Incident_Handling2_customized', 'AlgoSec_Requestor_Email')
Requestor = conf['content']

@Configuration(local=True)
class AFFIsolateServer(GeneratingCommand):
	ServerToIsolate = Option(name='ip', require=True, doc="IP address of server to isolate")
	Title = Option(name='title', require=True, doc="Title of isolation change request")
	Details = Option(name='details', require=True, doc="Details of isolation change request")

	def generate(self):
		AlgoSec_pwd = getCredentials(sessionToken)

		TicketSource1=self.ServerToIsolate
		TicketDest1='*'
		TicketSource2='*'
		TicketDest2=self.ServerToIsolate
	
		# Action - 0 for drop, 1 for allow
		TicketAction='0'
		TicketService='*'

		ActionStr = 'Allow' if TicketAction == '1' else 'Drop'

		# bypass ssl verification - needed only if using self-signed certificates (demo machine, etc.)
		#ssl._create_default_https_context = ssl._create_unverified_context

		# ALGOSEC AFF WSDL is availble here 'https://AFFIP/WebServices/FireFlow.wsdl'
		AFF_WSDL = 'https://%s/WebServices/FireFlow.wsdl' % AlgoSec_IP

		# Setup client
		client = Client(AFF_WSDL)

		try:
			# Authenticate
			authenticate = client.service.authenticate(username=AlgoSec_user, password=AlgoSec_pwd)

			# Create ticket and traffic lines objects
  
			ticket = client.factory.create('ticket')

			ticket.description=self.Details
			ticket.requestor=Requestor
			ticket.subject=self.Title

			trafficLine1 = client.factory.create('trafficLine')
			src = client.factory.create('trafficAddress')
			src.address=TicketSource1
			trafficLine1.trafficSource.append(src)
  			dst = client.factory.create('trafficAddress')
			dst.address=TicketDest1
			trafficLine1.trafficDestination.append(dst)
			srv = client.factory.create('trafficService')
			srv.service=TicketService
			trafficLine1.trafficService.append(srv)
			trafficLine1.action=TicketAction

			ticket.trafficLines.append(trafficLine1)
			
			trafficLine2 = client.factory.create('trafficLine')
  			src = client.factory.create('trafficAddress')
			src.address=TicketSource2
			trafficLine2.trafficSource.append(src)
  			dst = client.factory.create('trafficAddress')
			dst.address=TicketDest2
			trafficLine2.trafficDestination.append(dst)
			srv = client.factory.create('trafficService')
			srv.service=TicketService
			trafficLine2.trafficService.append(srv)
			trafficLine2.action=TicketAction

			ticket.trafficLines.append(trafficLine2)
			

		except:
			temp = dict()
			temp['Status'] = "Failed to create Change Request in AlgoSec FireFlow"
			temp['_raw'] = str(temp)
		
			yield temp
			
		# Actually create the ticket
		ticket_added = client.service.createTicket(sessionId=authenticate.sessionId, ticket=ticket)

		temp = dict()
		temp['TicketURL'] = ticket_added.ticketDisplayURL
		temp['Status'] = "Change Request successfully created in AlgoSec FireFlow"
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

	dispatch(AFFIsolateServer, sys.argv, sys.stdin, sys.stdout, __name__)