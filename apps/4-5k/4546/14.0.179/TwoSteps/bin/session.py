from splunk import auth, search
import splunk.rest
import time
import logging as logger

class Send(splunk.rest.BaseRestHandler):

   def handle_GET(self):
       sessionKey = self.sessionKey

       self.response.setStatus(200)
       self.response.setHeader('content-type', 'application/json')
       self.response.write('{ "session_key": "' + sessionKey + '" }')
