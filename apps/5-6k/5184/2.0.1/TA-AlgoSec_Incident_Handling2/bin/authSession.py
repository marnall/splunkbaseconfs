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
import re
import splunk.entity as entity

def getCredentials(sessionKey):
	myapp = 'TA-AlgoSec_Incident_Handling2'
	try:
		# list all credentials
		entities = entity.getEntities(['admin', 'passwords'], namespace=myapp, owner='nobody', sessionKey=sessionKey) 

	except Exception, e:
		raise Exception("Could not get %s credentials from splunk. Error: %s" % (myapp, str(e)))

	# return last password (in case there is more than one, for some reason)
	for i, c in entities.items(): 
		password = re.sub(".*``", "", c['clear_password'])

	return password

	raise Exception("No credentials have been found")  
