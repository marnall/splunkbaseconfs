import base64
import urllib2
import urllib
from contextlib import closing
import json

import common
from common import logger

class JiraService(object):
    def __init__(self, username, password, host, port=443, protocol="https"):
        self.username = username
        self.password = password
        self.protocol = protocol
        self.port = port
        self.host = host

        self.auth = username + ':' + password
        self.encoded_auth = base64.b64encode(self.auth)

        self.jiraserver = protocol + '://' + host + ':' + port
        logger.info("jira server:%s" % self.jiraserver)

    def make_url_request_obj(self, url):
        logger.info("req %s" % url)
        req = urllib2.Request(url)
        req.add_header('Content-Type', 'application/json; charset=utf-8')
        req.add_header('Authorization', 'Basic ' + self.encoded_auth)
        return req

    def request(self, path):
        path = self.jiraserver + path
        req = self.make_url_request_obj(path)
        with closing(urllib2.urlopen(req)) as raw_data:
            data = json.load(raw_data)

        return data