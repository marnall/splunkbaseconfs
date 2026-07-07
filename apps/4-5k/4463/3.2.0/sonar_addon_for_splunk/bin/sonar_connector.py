import json
import os
import sys
import threading

from constants import (CONTENT_TYPE_HEADER, CONTENT_LENGTH_HEADER)

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.six.moves.urllib.request import Request, urlopen


class SonarConnector:
    service_configuration = None
    result_available = None

    def __init__(self, service_configuration):
        self.service_configuration = service_configuration
        self.result_available = threading.Event()

    def request_data(self):
        try:
            return self.__send()
        finally:
            self.result_available.set()

    def done(self, timeout):
        return self.result_available.wait(timeout=timeout)

    def __send(self):
        request_url = 'https://%s:%s/' % (
            self.service_configuration.get_address(), self.service_configuration.get_port())
        request_body = self.service_configuration.request_body()
        request_body_bytes = json.dumps(request_body).encode('utf-8')

        req = Request(request_url)
        req.add_header(CONTENT_TYPE_HEADER, 'application/json; charset=utf-8')
        req.add_header(CONTENT_LENGTH_HEADER, str(len(request_body_bytes)))

        return urlopen(url=req, data=request_body_bytes)
