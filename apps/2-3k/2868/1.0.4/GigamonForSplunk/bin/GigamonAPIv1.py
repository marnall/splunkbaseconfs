import time, urllib
from GigamonAPI import GigamonAPIBase, ConfigurationError

class GigamonAPIv1(GigamonAPIBase):
        """ v1 Specific versions """
        _version = "v1"
        _valid_modules = ["inventory","domain","nodes","portConfig", "maps", "gsops","nodeCredentials"]
        def __init__(self, **kwargs):
                """ Intuit a v1 API Instance """
                GigamonAPIBase.__init__(self,**kwargs)

        #positional(2)
        def _buildUrl(self, module, submodule="", **kwargs):
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
			v1Args = "?%s"%(urllib.urlencode(kwargs))
                        BaseUrl = "https://%s/api/v1/%s/%s%s%s"%(self._hostname, module, submodule,sepAlias,v1Args)
                except KeyError as ne:
                        self._log.warn("action=failure msg=\"required parameter not set\" parameter=\"%s\" "%ne)
                        raise ConfigurationError("missing parameter","Required Parameter not passed: %s"%ne)
                v1Url = "%s from %s"%(BaseUrl,kwargs)
                self._log.debug("URL: %s"%v1Url)
                return BaseUrl

        def get_nodes(self, flat=True):
                """ Query the API for the nodes. """
                self._log.debug("starting get_nodes v1")
                submodule = ""
                if ( flat ):
                        submodule = "flat"
                return self._read(self._buildUrl("nodes",submodule))

        def get_chassis_inventory(self, clusterId,ports="true"):
                """ Query the API for the chassis inventories """
		#self._validateIP(clusterId)
                return self._read(self._buildUrl("inventory","chassis",clusterId=clusterId,ports=ports))

        def get_ports(self, clusterId, alias="",ports=True):
                """ Query the inventory module for ports """
                return self._read(self._buildUrl("inventory","ports",alias=alias,clusterId=clusterId,ports=ports))

        def get_port_groups(self, clusterId, alias=""):
                """ Query the port config for the port groups """
                return self._read(self._buildUrl("portConfig","portGroups",alias=alias,clusterId=clusterId))

        def get_gigastreams(self,clusterId, alias=""):
                """ Query the gigastreams for the giga(ty) giga(ty) goo! """
                return self._read(self._buildUrl("portConfig","gigastreams",alias=alias,clusterId=clusterId))

        def get_maps(self,clusterId, alias=""):
                """ Query for the maps """
                return self._read(self._buildUrl("maps","",alias=alias,clusterId=clusterId))

	def get_domain(self):
		""" Query for Domain Information """
		return self._read(self._buildUrl("domain",""))

	def get_node_credentials(self,deviceAddress=""):
		""" Return the credentials for the specified Nodes """
		return self._read(self._buildUrl("nodeCredentials",deviceAddress))

	def get_port_neighbors(self,clusterId):
		""" Get port neighbors """
		return self._read(self._buildUrl("inventory","ports",alias="neighbors",clusterId=clusterId))

	def get_port_config(self, clusterId, portId=""):
		""" Port Configurations """
		return self._read(self._buildUrl("portConfig","portConfigs",clusterId=clusterId, portId=portId))

	def get_tunneled_ports(self, clusterId, portId=""):
		""" Tunneled Ports Configuration"""
		return self._read(self._buildUrl("portConfig","tunneledPorts",clusterId=clusterId,alias=portId))

	def get_gigasmart_ops(self, clusterId,alias=""):
		""" Retrieve GigaSMART Operations """
		return self._read(self._buildUrl("gsops","",clusterId=clusterId,alias=alias))

	def get_gigasmart_portgroups(self, clusterId, alias=""):
		""" Retrieve GigaSMART Port Groups """
		return self._read(self._buildUrl("gsGroups","",clusterId=clusterId, alias=alias))
