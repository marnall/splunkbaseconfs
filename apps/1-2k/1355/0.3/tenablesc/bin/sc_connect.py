#!/usr/bin/python
# copyright Satisnet Ltd.   2013
# Licensed LGPL v3

import sys
import httplib2
import re
import urllib
import json
import pprint



class sc_connect:
	def __init__(self, user, password, url):
		try:
			self.user     = user
			self.password = password
			self.url      = url
			self.headers  = {"Content-type": "application/x-www-form-urlencoded"}
			self.Login()
		except Exception, e:
			raise Exception, "Error connecting to Security Center: %s" % str(e)	

	def HttpRequest(self, data):
		try:
			http = httplib2.Http(disable_ssl_certificate_validation=True)
			response, content = http.request(self.url, 'POST', headers=self.headers, 
						body=urllib.urlencode(data))
	
			if 'set-cookie' in response:
				self.headers['Cookie'] = response['set-cookie']
			return response, content
		except Exception, e:
			raise Exception, "Error performing POST: %s" % str(e)

		
	def Login(self):
		try:
			input = {'password': self.password,
				 'username': self.user}
				
			inputjson = json.dumps(input)
	
			data = {"request_id": "1",
			        "module": "auth",
			        "action": "login",
			        "input": inputjson}
	
			response, content = self.HttpRequest(data)
	
			result = json.loads(content)
	
			if result["error_code"] == 0:
				self.token = result['response']['token']
			else:
				raise Exception, "Bad error_code: %s" % str(result["error_code"])

		except Exception, e:
			raise Exception, "Error Logging into Security Center, %s" % str(e)
			

	def get_token(self):
		return self.token

	def vulnipdetail(self):
		try:
	                endOffset = 0
	                # the initial parse gets the number of records 
	                # to populate the the endOffset
	                while True:
				input = {"tool": "vulndetails", "startOffset": "0", 
					 "endOffset": endOffset,
					 "sourceType": "cumulative"}

				inputjson = json.dumps(input)
 	 
       		         	data = {"request_id": "1",
					"module": "vuln",
					"action": "query",
					"input": inputjson,
					"token": self.token}

				response, content = self.HttpRequest(data)

				result = json.loads(content)
	                        endOffset = result['response']['totalRecords']
                        	if result['response']['returnedRecords'] == int(result['response']['totalRecords']):
                			print content
					break		
		except Exception, e:
			raise Exception, "Error performing vuln::query::vulndetails : %s" % str(e)

			
			
                    

if __name__ == '__main__':
	if len(sys.argv) == 3:
                username=sys.argv[1]
                password=sys.argv[2]
                url=sys.argv[3]

		sc = sc_connect(username, password, url)
        	sc.vulnipdetail() 
	else:
		print "Usage $SPLUNK_HOME/bin/splunk cmd python %s \"username\" \"password\" \"url\"" % sys.argv[0]
		print "\n\n"
		print "Where:-"
		print "    username		is a valid Security Center Username"
		print "    password		is the password for the Security Center Username"
		print "    url			is a valid Security Center request URL, example:- https://192.168.1.2/request.php"
		print "\n\n"
		print "Running this script directly is for testing purposes only."

