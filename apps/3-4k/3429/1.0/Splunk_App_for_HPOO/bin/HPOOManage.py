import os
import sys
import time
import base64
import urllib
import json
from urllib2 import Request, urlopen, URLError, HTTPError
import urllib2
import base64

debug=0
class BetterHTTPErrorProcessor(urllib2.BaseHandler):
	# a substitute/supplement to urllib2.HTTPErrorProcessor
	# that doesn't raise exceptions on status codes 201,204,206
	def http_error_201(self, request, response, code, msg, hdrs):
		return response
	def http_error_204(self, request, response, code, msg, hdrs):
		return response
	def http_error_206(self, request, response, code, msg, hdrs):
		return response

class HPOOManage:

	def __init__(self, customerName, hpoo_url, hpoo_user, hpoo_password, globconf = None):
		self.oo_url = '%s/oo/rest/v1' % hpoo_url
		self.oo_user=hpoo_user
		self.oo_pass=hpoo_password
		self.base64string = base64.encodestring(hpoo_user+':'+hpoo_password).replace('\n', '')
		self.BetterHTTPErrorProcessor=BetterHTTPErrorProcessor()
		opener = urllib2.build_opener(self.BetterHTTPErrorProcessor)
		urllib2.install_opener(opener)
		self.flowmap={}
		self.globconf=globconf
		if globconf != None:
			if globconf.confmap.has_key("flowmap"):
				self.flowmap=globconf.confmap.get("flowmap")
			else:
				self.flowmap=self.getFlowMap()
				globconf.confmap["flowmap"]=self.flowmap

	def getStatusOfFlows(self, executionlist):
		if len(executionlist) < 1:
			return []
		req_url='%s/executions/%s/summary'% (self.oo_url, ",".join(executionlist))
		#req_url='%s/executions'% (self.oo_url)
		#res_log().debug("=== req_url: %s" % req_url)
		request = Request(req_url)
		request.add_header("Authorization", "Basic %s" % self.base64string)
		respinfo=""
		try:
			response = urlopen(request)
			respinfo = response.read()
			#print respinfo
                except HTTPError, e:
                        #res_log().debug("=== HTTPError: %s" % e)
                        if e.code == 201:
                                respinfo=response.read()
                                #res_log().debug("=== resinfo:%s" % respinfo)
                        else:
				return []
		except URLError, e:
			#res_log().debug('==== URLError:%s' % e)
			return {}
		return json.loads(respinfo)


	def getStatusOfFlowsByRunName(self, runName):
		req_url='%s/executions?runName=%s' % (self.oo_url, runName)
		#res_log().debug("=== req_url: %s" % req_url)
		request = Request(req_url)
		request.add_header("Authorization", "Basic %s" % self.base64string)
		respinfo=""
		try:
			response = urlopen(request)
			respinfo = response.read()
			#res_log().debug("=== %s" % respinfo)
                except HTTPError, e:
                        #res_log().debug("=== HTTPError: %s" % e)
                        if e.code == 201:
                                respinfo=response.read()
                                #res_log().debug("=== resinfo:%s" % respinfo)
                        else:
				return None
		except URLError, e:
                        #res_log().debug('==== URLError:%s' % e)
			return None
		return json.loads(respinfo)

        def getStatusOfFlowsByDtRange(self, stDate, endDate):
                req_url='%s/executions?startedAfter=%s' % (self.oo_url, stDate)
		if debug:
                	print "=== req_url: %s" % req_url
                request = Request(req_url)
                request.add_header("Authorization", "Basic %s" % self.base64string)
                respinfo=""
                try:
                        response = urlopen(request)
                        respinfo = response.read()
			if debug:
                        	print("=== %s" % respinfo)
                except HTTPError, e:
			if debug:
                        	print("=== HTTPError: %s" % e)
                        if e.code == 201:
                                respinfo=response.read()
                                #res_log().debug("=== resinfo:%s" % respinfo)
                        else:
                                return None
                except URLError, e:
			if debug:
                        	print '==== URLError:%s' % e
                        return None
                return json.loads(respinfo)


	def getExecutionLogByExecutionId(self, executionId):
		req_url='%s/executions/%s/execution-log' % (self.oo_url, executionId)
		#res_log().debug("=== req_url: %s" % req_url)
		request = Request(req_url)
		request.add_header("Authorization", "Basic %s" % self.base64string)
		respinfo=""
		try:
			response = urlopen(request)
			respinfo = response.read()
			#res_log().debug("=== %s" % respinfo)
                except HTTPError, e:
                        #res_log().debug("=== HTTPError: %s" % e)
                        if e.code == 201:
                                respinfo=response.read()
                                #res_log().debug("=== resinfo:%s" % respinfo)
                        else:
				return None
		except URLError, e:
                        #res_log().debug('==== URLError:%s' % e)
			return None
		return json.loads(respinfo)


        def getExecutionStepsByExecutionId(self, executionId):
                req_url='%s/executions/%s/steps' % (self.oo_url, executionId)
                #res_log().debug("=== req_url: %s" % req_url)
                request = Request(req_url)
                request.add_header("Authorization", "Basic %s" % self.base64string)
                respinfo=""
                try:
                        response = urlopen(request)
                        respinfo = response.read()
                        #res_log().debug("=== %s" % respinfo)
                except HTTPError, e:
                        #res_log().debug("=== HTTPError: %s" % e)
                        if e.code == 201:
                                respinfo=response.read()
                                #res_log().debug("=== resinfo:%s" % respinfo)
                        else:
                                return None
                except URLError, e:
                        #res_log().debug('==== URLError:%s' % e)
                        return None
                return json.loads(respinfo)


	def getFlowMap(self, ):
		flowmap={}
		allflows=self.getFlows()
		if allflows==None:
			return flowmap
		for f in allflows:
			if f.get("path").startswith("Library/Actions") and f.get('leaf') == True:
				flowmap[f.get("name")] = f.get("id")
			if f.get("path").startswith("Library/Sungard AS/RES/RES_ACTIONS") and f.get('leaf') == True:
				flowmap[f.get("name")] = f.get("id")
			if f.get("name") == "action_list_with_res_post" and f.get('parentId') == "Library/RES/ActionMapper/Actions":
				flowmap[f.get("name")] = f.get("id")
		#res_log().debug("FlowMap: %s" % flowmap)
		return flowmap
		
	def getFlows(self, ):
		req_url='%s/flows/library/' % (self.oo_url)
                #res_log().debug("=== req_url: %s" % req_url)
                request = Request(req_url)
                request.add_header("Authorization", "Basic %s" % self.base64string)
                respinfo=""
                try:
                        response = urlopen(request)
                        respinfo = response.read()
                        #res_log().debug("=== %s" % respinfo)
                except HTTPError, e:
                        #res_log().debug("=== HTTPError: %s" % e)
                        if e.code == 201:
                                respinfo=response.read()
                                #res_log().debug("=== resinfo:%s" % respinfo)
                        else:
                                return None
                except URLError, e:
                        #res_log().debug('==== URLError:%s' % e)
                        return None
		except Exception, e:
			#res_log().debug('==== Exception %s' % e)
			return None
                return json.loads(respinfo)

        def getContentPacks(self, ):
                req_url='%s/content-packs' % (self.oo_url)
                #res_log().debug("=== req_url: %s" % req_url)
                request = Request(req_url)
                request.add_header("Authorization", "Basic %s" % self.base64string)
                respinfo=""
                try:
                        response = urlopen(request)
                        respinfo = response.read()
                        #res_log().debug("=== %s" % respinfo)
                except HTTPError, e:
                        #res_log().debug("=== HTTPError: %s" % e)
                        if e.code == 201:
                                respinfo=response.read()
                                #res_log().debug("=== resinfo:%s" % respinfo)
                        else:
                                return None
                except URLError, e:
                        #res_log().debug('==== URLError:%s' % e)
                        return None
                except Exception, e:
                        #res_log().debug('==== Exception %s' % e)
                        return None
                return json.loads(respinfo)

        def getCPDetails(self, cpid):
                req_url='%s/content-packs/%s/content-tree' % (self.oo_url, cpid)
                #res_log().debug("=== req_url: %s" % req_url)
                request = Request(req_url)
                request.add_header("Authorization", "Basic %s" % self.base64string)
                respinfo=""
                try:
                        response = urlopen(request)
                        respinfo = response.read()
                        #res_log().debug("=== %s" % respinfo)
                except HTTPError, e:
                        #res_log().debug("=== HTTPError: %s" % e)
                        if e.code == 201:
                                respinfo=response.read()
                                #res_log().debug("=== resinfo:%s" % respinfo)
                        else:
                                return None
                except URLError, e:
                        #res_log().debug('==== URLError:%s' % e)
                        return None
                except Exception, e:
                        #res_log().debug('==== Exception %s' % e)
                        return None
                return json.loads(respinfo)

