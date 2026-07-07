'''
Class GigamonAPI
Author: Kyle Smith
Company: Aplura, LLC
API Credit: Gigamon, Inc.
Copyright 2015
'''
import logging, json, requests, os, time
import logging  as logger

class Error(Exception):
	pass

class ConfigurationError(Exception):
	def __init__(self, expr, msg):
		self.expr = expr
		self.msg = json.dumps(msg)
	def __str__(self):
		return repr(self.msg)

class HTTPError(Exception):
	def __init__(self, *args, **kwargs):
		response = kwargs.pop('response',None)
		self.response = response
		self.request = kwargs.pop('request',None)
		if (response is not None and not self.request and hasattr(response,'request')):
			self.request = self.response.request
		super(Exception,self).__init__(*args,**kwargs)

class GigamonAPIBase:
	""" Base Class for Gigamon FM API : Should not be instantiated directly """
	_session = None
	_hostname = None
        _log = logger
	_isDebugMode = False
	_useJson = False
	_lastUrl = None
	
	def __init__(self, **kwargs):
                """Construct an instance of the GigamonAPIBase"""
                self._log.debug("starting __init__ base")
                try:
                        username = kwargs["username"]
                        password = kwargs["password"]
                        hostname = kwargs["hostname"]
                except KeyError as ne:
                        self._log.warn("action=failure msg=\"required argument not passed\" argument=\"%s\" "%ne)
                        raise ValueError("Required argument not passed: %s"%ne)
                self._session = requests.session()
                self._session.auth = (username, password)
                self._hostname = hostname
		try:
			self._useJson = kwargs["useJson"]
		except:
			pass

	def _toggleDebug(self):
		if(self._isDebugMode):
			self._isDebugMode = False
		else:	
			self._isDebugMode = True

	def _formatReturn(self, obj):
		if (self._useJson ):
			return json.loads(obj)
		else:
			return obj

	def _read(self, url):
                self._log.debug("starting %s read from url:%s"%(self._version, url))
		self._lastUrl = url
		#return "I would have returned. But I was delayed."
                r = self._session.get(url, verify=False)
                if r.status_code == 200:
                        return self._formatReturn(r.content)
                else:
                        self._log.error(" action=read api_version=%s status=%s content=\"%s\" "%(self._version, r.status_code, r.content) )
			self._raise_for_status(r)

	def _raise_for_status(self,r):
        	"""Raises stored :class:`HTTPError`, if one occurred."""
		myJson = {}
		try:
			myJson = json.loads(r.content)
		except:
			pass
		additional_info = ""
		if "errors" in myJson:
			additional_info = myJson["errors"][0]["msg"]
	        http_error_msg = ''
        	if 400 <= r.status_code < 500:
	            http_error_msg = '%s Client Error: reason="%s" url="%s" additional_info="%s"' % (r.status_code, r.reason, r.url, additional_info)
        	elif 500 <= r.status_code < 600:
		    http_error_msg = '%s Server Error: reason="%s" url="%s" additional_info="%s"' % (r.status_code, r.reason, r.url, additional_info)
        	if http_error_msg:
	            raise HTTPError(http_error_msg, response=r)

	def _gen_date_time(self):
		""" Generate a timestamp """
		st = time.localtime()
		tm = time.mktime(st)
		return time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime(tm))
		
	def _validateIP(self, ipAddr):
		""" Test and Validate an IP """
		from IPy import IP
		IP(ipAddr)
	
	def get_last_url(self):
		return self._lastUrl

	def ConnectionTest(self):
                """Test the Connection to make sure it is up and running"""
                return self._read(self._buildUrl("", ""))

	def get_version(self):
		return self._version

################################################
###### Add additional version classes here #####
################################################
global _API
from GigamonAPIv1 import GigamonAPIv1
from GigamonAPIv1_1 import GigamonAPIv1_1
from GigamonAPIv1_2 import GigamonAPIv1_2
from GigamonAPIv1_3 import GigamonAPIv1_3
################################################
### To add a new Version, first import it      #
### above, and then add the version number and #
### classname to _API below.                   #
################################################
_API = {
        "v1" : GigamonAPIv1,
	"v1.1" : GigamonAPIv1_1,
	"v1.2" : GigamonAPIv1_2,
	"v1.3" : GigamonAPIv1_3
       }

######
## Begin Function call to build required class
######
def GigamonAPI(api_version="v1",**kwargs):
	'''
	Interface with the Gigamon FM API
	'''
	global _API
	_valid_apis = [] # Which versions will we accept?
	_version = None
	[ _valid_apis.append(x) for x in _API ]
	if (api_version not in _valid_apis):
		_log.warn("action=failure msg=\"invalid api specified\" api_version=\"%s\" "%api_version)
		raise ConfigurationError("api_version","Invalid API Version Specified: %s"%api_version)
	return _API[api_version](**kwargs)
