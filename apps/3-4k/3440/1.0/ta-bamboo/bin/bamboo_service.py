import base64
import json
import urllib2
from contextlib import closing

from common import logger


class BambooService(object):
    def __init__(self, username, password, host, port=443, protocol="https"):
        self.username = username
        self.password = password
        self.protocol = protocol
        self.port = port
        self.host = host

        self.auth = username + ':' + password
        self.encoded_auth = base64.b64encode(self.auth)

        self.bambooserver = protocol + '://' + host + ':' + port
        logger.info("Bamboo server:%s" % self.bambooserver)

    def make_url_request_obj(self, url):
        logger.info("req %s" % url)
        req = urllib2.Request(url)
        req.add_header('Content-Type', 'application/json; charset=utf-8')
        req.add_header('Authorization', 'Basic ' + self.encoded_auth)
        return req

    def request(self, path):
        path = self.bambooserver + path
        req = self.make_url_request_obj(path)
        with closing(urllib2.urlopen(req)) as raw_data:
            data = json.load(raw_data)

        return data
