import fix_path
import os
import json
import urllib2

workato_app_name = os.path.basename(os.path.dirname(os.path.dirname(__file__)))

class Request(urllib2.Request):
    def set_method(self,method):
        self.__method=method
    def get_method(self):
        return self.__method

def call_json_service(url, method, payload, authorization_header):
    req = Request(url, json.dumps(payload), {
        "Content-Type": "application/json",
        "Authorization": authorization_header,
    })
    req.set_method(method)
    res = urllib2.urlopen(req)
    if res.code!=200:
        raise Exception('response code %s' % res.code)
    body = res.read()
    return json.loads(body)
