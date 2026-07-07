import fix_path
from splunk import auth, search
import splunk.rest
import logging as logger
import splunk.bundle as bundle
import httplib2, urllib, urllib2
import json
import splunklib.client as client
from splunklib.binding import _spliturl as spliturl
from splunklib.binding import namespace as namespace
import base64
import random
from .utils import Request, call_json_service

import os
app_name = os.path.basename(os.path.dirname(os.path.dirname(__file__)))

class BaseRestHandler(splunk.rest.BaseRestHandler):
    def create_service(self):
        management_url = "https://"+self.request["headers"]["host"]+"/"
        scheme, host, port, path = spliturl(management_url)
        token = self.request["headers"].get("authorization", "")[6:]
        username, password = base64.b64decode(token).split(':')
        s = client.Service(
            username=username,
            password=password,
            port=port,
            scheme=scheme,
            host=host,
            app=app_name)
        s.login()
        return s
    def call_json_service(self, method, path, payload):
        management_url = "https://"+self.request["headers"]["host"]+path
        return call_json_service(management_url, method, payload, self.request["headers"].get("authorization", ""))
    def send_json_response(self,object):
        self.response.setStatus(200)
        self.response.setHeader('content-type', 'application/json')
        self.response.write(json.dumps(object))
