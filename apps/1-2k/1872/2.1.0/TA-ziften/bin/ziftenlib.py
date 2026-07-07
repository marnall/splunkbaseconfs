import os
import json
import os.path
import base64
import urllib
import urllib2
import time
import sys
import ssl

class ZiftenConnector:
    def __init__(self,username, token, ip, version = False):

        self.username = username
        self.token = token
        self.ip = ip

    def callAPI(self, method, url, data = {}, download = False):

        if url[0:1] == '/':
            url = url[1:]
        baseUrl = "https://" + self.ip + "/external/api/"+url
        #print "baseUrl: " + baseUrl
        return self._request(method, baseUrl, data, download)

    def _request(self, method, url, data = {}, download = False):
        request=urllib2.Request(url)
        request.add_header("Authorization", "Bearer %s" % self.token)
        #print "Method: " + method
        #print "Token:" + self.token
        try:
            if(method == "POST"):
                response=urllib2.urlopen(request,data="")
            elif(method == "GET"):
                response=urllib2.urlopen(request,data=None)
            #print "Response Code: " 
            #print response.getcode()
        except urllib2.HTTPError as e:
            print "%s status=error, msg='Server failed to fulfill the request' code='%s'" % (time.strftime("%Y-%m-%d %H:%M:%S") , str(e.code))
            sys.stderr.write('%s - ERROR - Server failed to fulfill the request %s\n' % (time.strftime("%Y-%m-%d %H:%M:%S"), str(e.code)))
            exit(-1)
        except urllib2.URLError as e:
            print "%s status=error, msg='Failed to reach server' reason='%s'" % (time.strftime("%Y-%m-%d %H:%M:%S") , str(e.reason))
            sys.stderr.write('%s - ERROR - Failed to reach server %s\n' % (time.strftime("%Y-%m-%d %H:%M:%S"), str(e.reason)))
            exit(-1)

        return response
