import time, urllib, hashlib
import datetime
from GigamonAPI import GigamonAPIBase, ConfigurationError
from GigamonAPIv1 import GigamonAPIv1

class GigamonAPIv1_3(GigamonAPIv1):
        """ v1.3 Specific versions """
        _version = "v1.3"
        _valid_modules = ["inventory","domain","nodes","portConfig", "maps", "gsops","nodeCredentials","trending","system","auditLog","events","licensing","gsGroups","gsops","trafficAnalyzer"]
	_valid_license = [ "be7938e9a87618a98a7b6b47e12aa44b" ]
	_validLicense = False
	_licenseLevel = "Not Found"
	_checklicense = False


        def __init__(self, **kwargs):
                """ Intuit a v1.3 API Instance """
                GigamonAPIBase.__init__(self,**kwargs)
		self._validLicense = self.validate_license()

        #positional(2)
        def _buildUrl(self, module, submodule="", **kwargs):
		if ( not self._validLicense and module != "licensing" and self._checklicense):
			self._log.warn("Invalid license detected")
			raise Exception, "Invalid License - %s"%self._licenseLevel
		self._log.debug("Starting to build the url with module: %s submodule:%s and arguments:%s"%(module,submodule,kwargs))
                if (module not in self._valid_modules):
                        self._log.warn("Invalid Module Specified for Version %s: %s"%(self.get_version(),module))
                        raise ConfigurationError("missing parameter","Invalid Module Specified for Version %s: %s"%(self.get_version(),module))
                try:
			sepAlias = ""
			if ( "alias" in kwargs ):
                                if (len(kwargs["alias"]) > 0):
                                        sepAlias = "/%s"%kwargs["alias"]
                        if (module in ["inventory","nodes","domain","nodeCredentials"] and submodule not in ["ports", "chassis"]):
                                sepAlias = ""
				if "clusterId" in kwargs:
					kwargs["clusterId"] = ""
			if ("startTime" in kwargs):
				kwargs["startTime"] = datetime.datetime.fromtimestamp(kwargs["startTime"]).replace(microsecond=0).isoformat()
			if ("endTime" in kwargs):
				if (kwargs["endTime"] == "now"):
					kwargs["endTime"] = datetime.datetime.now().replace(microsecond=0).isoformat()
				else:
					kwargs["endTime"] = datetime.datetime.fromtimestamp(kwargs["endTime"]).replace(microsecond=0).isoformat()
			v1Args = "?%s"%(urllib.urlencode(kwargs))
                        BaseUrl = "https://%s/api/%s/%s/%s%s%s"%(self._hostname,self.get_version(), module, submodule,sepAlias,v1Args)
			BaseUrl = BaseUrl.replace("map_NAME_RPL","map").replace("max_NAME_RPL","max")
                except KeyError as ne:
                        self._log.warn("action=failure msg=\"required parameter not set\" parameter=\"%s\" "%ne)
                        raise ConfigurationError("missing parameter","Required Parameter not passed: %s"%ne)
                v1Url = "%s from %s"%(BaseUrl,kwargs)
                self._log.debug("URL: %s"%v1Url)
                return BaseUrl

	"""
		These are implemented in the v1.3 version of the API.
	"""

	def get_port_stats(self, clusterId,startTime,endTime,metric,boxport="*"):
		""" Pull Statistics for ports on clusterId """
		return self._read(self._buildUrl("trending","ports",alias="timeSeries",cluster=clusterId,startTime=startTime,metric=metric,boxPort=boxport,endTime=endTime))

	def get_port_metrics(self):
		return [ 'port.utilztn', 'port.packetDrop', 'port.packetDiscard','port.packetErr','port.packets','port.octets' ]

	def get_map_stats(self, clusterId,startTime,endTime,metric,mapname="*"):
		""" Pull statistics for maps on clusterId """
		return self._read(self._buildUrl("trending","maps",alias="timeSeries",clusterId=clusterId,startTime=startTime,endTime=endTime,metric=metric,map_NAME_RPL=mapname))

	def get_map_metrics(self):
		return ['map.octets','map.packets']

	def get_gigasmart_op_stats(self,clusterId,startTime,endTime,metric,gsop="*"):
		""" Get GigaSMART Operation Stats """
		return self._read(self._buildUrl("trending","gsops",alias="timeSeries",clusterId=clusterId,startTime=startTime,endTime=endTime,metric=metric,gsop=gsop))

	def get_gigasmart_op_metrics(self):
		return [ 'gsop.octets', 'gsop.packets', 'gsop.packetDrop', 'gsop.packetDropNoInit', 'gsop.packetTerm','gsop.packetParseErr']

	def get_gigasmart_portgroup_stats(self, clusterId, startTime, endTime, metric, gsGroup="*"):
		""" Get GigaSMART Port Group Stats """
		return self._read(self._buildUrl("trending","gsGroups",alias="timeSeries",clusterId=clusterId,startTime=startTime,endTime=endTime,metric=metric,gsGroup=gsGroup))

	def get_gigasmart_portgroup_metrics(self):
		return [ 'gsGroup.octets', 'gsGroup.packets','gsGroup.packetDrop','gsGroup.packetTerm','gsGroup.packetErr']

	def get_fm_events(self,ts=""):
		""" Get FM Admin Events """
		return self._read(self._buildUrl("events","",startTime=ts))

	def get_system_users(self, clusterId):
		""" Get System and Admin users for FM """
		return self._read(self._buildUrl("system","localUsers",clusterId=clusterId))

	def get_audit_logs(self,ts=""):
		""" Return the Audit Events for the System """
		
		return self._read(self._buildUrl("auditLog","", startTime=ts))
	
	def get_system_info(self,clusterId):
		""" Return system information """
		return self._read(self._buildUrl("system","syslog", clusterId=clusterId))

	def get_licensing(self):
		""" Return the Licensing State of the FM """
                self._log.debug("getting the license state of the fm")
		return self._read(self._buildUrl("licensing","fm"))

	def validate_license(self):
		""" Check the license level and deny incorrect level """
		self._log.info("checking license validation")
                licType = "None"
		try:
		  lic = self.get_licensing()
                  self._log.debug("my license: %s"%lic)
		  m = hashlib.md5()
		  licT = lic["licensingSummary"]["baseBundle"]["type"]
		  self._licenseLevel = licT
		  m.update("%s"%licT)
                  licType = m.hexdigest()
		except Exception, e:
		  self._log.error(e)
		  self._log.debug("exception on license")
		self._log.info("license Type: %s  valid_License: %s"%(licType,self._valid_license ))
		if ( licType in self._valid_license ):
			self._log.debug("valid license: true")
			self._isValidLicense = True
			return True
		else:
			self._log.debug("valid license: false")
			self._isValidLicense = False
			return False
		
	def get_trafficAnalyzer(self, endpoint="conversations", since="1-hour"):
		""" Get the traffic analyzer endpoint. Valid values are conversations, endpoints, apps, protocols """
		return self._read(self._buildUrl("trafficAnalyzer",endpoint, alias="top",since=since,max_NAME_RPL=100))
