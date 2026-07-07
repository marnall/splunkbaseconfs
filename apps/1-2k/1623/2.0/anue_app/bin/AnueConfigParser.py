import ConfigParser
import os, sys
import json
import logging, logging.handlers
import base64
import ast

CONFIG_KEY_USERNAME = "username"
CONFIG_KEY_PASSWORD = "password"
CONFIG_KEY_WEB_API_PORT = "webapi_port"
CONFIG_KEY_HOST = "host"
CONFIG_KEY_TOOL_PORTS = "tool_ports"
CONFIG_KEY_NETWORK_PORTS = "network_ports"
CONFIG_KEY_BIDIRECTIONAL_PORTS = "bidirectional_ports"
CONFIG_KEY_DYNAMIC_FILTERS = "dynamic_filters"


# ------------Log for configuration reads errors ---------------------------------------------
LOG_FILE = os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','AnueConfigParser.log')
def initLogger():
    # Setup logging
    logger = logging.getLogger('AnueConfigParser')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    fileHandler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    fileHandler.setFormatter(formatter)
    logger.addHandler(fileHandler)
    return logger

logger = initLogger()


# ---- AnueChassisData class. Responsibile for holding chassis configuration before each poll ---- 
class AnueChassisData:
	host = None
	username = None
	password = None
	webApiPort = None
	toolPorts = None
	networkPorts = None
	bidirectionalPorts = None
	dynamicFilters = None
	
	def __init__(self, mHost, mUsername, mPassword, mPort="8000"):
		self.host = mHost
		self.username = mUsername
		self.password = mPassword
		self.webApiPort = mPort

		self.toolPorts = list()
		self.networkPorts = list()
		self.bidirectionalPorts = list()
		self.dynamicFilters = list()
		
	def __str__ (self):
		return "Host= "+self.host+" ,User= "+self.username+ " ,Pass= "+self.password +" ,Webapi port= "+self.webApiPort
		
	def getHost(self):
		return self.host
	
	def getUsername(self):
		return self.username
		
	def getPassword(self):
		return self.password
	
	def getWebApiPort(self):
		return self.webApiPort
		
	def getToolPortsList(self):
		return self.toolPorts
		
	def getNetworkPortsList(self):
		return self.networkPorts
		
	def getBidirectionalPortsList(self):
		return self.bidirectionalPorts
		
	def getDynamicFiltersList(self):
		return self.dynamicFilters
		
	def isValid(self):
		if (not self.host) or (not self.username ) or (not self.password ) or (not self.webApiPort):
			return False
		else:
			return True

	def parsePollSetting(self,setting, addToList):
		jdata = json.loads(setting)
		for port in jdata:
			addToList.append(port)
			
	def getPortsToQuery(self):
		pIdsSet = set()
		for pDictTool in self.toolPorts:
			pId = pDictTool.get('id')
			if(pId != None):
				temp = ast.literal_eval(pId)
				pIdsSet.add(temp)
				
		for pDictNetwork in self.networkPorts:
			pId = pDictNetwork.get('id')
			if(pId != None):
				temp = ast.literal_eval(pId)
				pIdsSet.add(temp)
				
		for pDictBid in self.bidirectionalPorts:
			pId = pDictBid.get('id')
			if(pId != None):
				temp = ast.literal_eval(pId)
				pIdsSet.add(temp)
		
		pIdsList = list(pIdsSet)
		return pIdsList
		
	def getDynamicFiltersToQuery(self):
		dFiltersList = list()
		for pDict in self.dynamicFilters:
			pId = pDict.get('id')
			if(pId != None):
				temp = ast.literal_eval(pId)
				dFiltersList.append(temp)
		
		return dFiltersList
	
	def getJsonBodyQuery(self):
		jsonBody = {}
		pIdsList = self.getPortsToQuery()
		dFiltersList = self.getDynamicFiltersToQuery()
		
		if(len(pIdsList) > 0):
			jsonBody['port'] = pIdsList
		if(len(dFiltersList) > 0):
			jsonBody['filter'] = dFiltersList
		
		return str(json.dumps(jsonBody))
	
	def needsToPoll(self):
		hasToolPortsToQuery = (len(self.toolPorts) > 0)
		hasNetworkPortsToQuery = (len(self.networkPorts) > 0)
		hasBidirectionalPortsToQuery = (len(self.bidirectionalPorts) > 0)
		hasDynamicFiltersToQuery = (len(self.dynamicFilters) > 0)
		
		return (hasToolPortsToQuery or hasNetworkPortsToQuery or hasBidirectionalPortsToQuery or hasDynamicFiltersToQuery)
	
# ---- Responsabile for reading chassis configurations --------  	
def readAnueChassisData():
	listChConfigs = list()
	try:
		chassis_conf_file = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','anue_app','default','chassis.conf')
		
		parser = ConfigParser.SafeConfigParser()
		parser.read(chassis_conf_file)
		
		
		
		for section_name in parser.sections():
			if parser.has_option(section_name, CONFIG_KEY_HOST):
				host = parser.get(section_name,CONFIG_KEY_HOST)
			if parser.has_option(section_name, CONFIG_KEY_USERNAME):
				username = parser.get(section_name,CONFIG_KEY_USERNAME)
			if parser.has_option(section_name, CONFIG_KEY_PASSWORD):
				encodedPassword = parser.get(section_name,CONFIG_KEY_PASSWORD)
				password = base64.b64decode(encodedPassword)
			if parser.has_option(section_name, CONFIG_KEY_WEB_API_PORT):
				webapi_port = parser.get(section_name,CONFIG_KEY_WEB_API_PORT)
				
				
			if (webapi_port):
				ch = AnueChassisData(host, username, password, webapi_port)
			else:
				ch = AnueChassisData(host, username, password)
				
			if parser.has_option(section_name, CONFIG_KEY_TOOL_PORTS):
				toolPortsString = parser.get(section_name,CONFIG_KEY_TOOL_PORTS)
				ch.parsePollSetting(toolPortsString, ch.getToolPortsList())
				
			if parser.has_option(section_name, CONFIG_KEY_NETWORK_PORTS):
				networkPortsString = parser.get(section_name,CONFIG_KEY_NETWORK_PORTS)
				ch.parsePollSetting(networkPortsString, ch.getNetworkPortsList())
				
			if parser.has_option(section_name, CONFIG_KEY_BIDIRECTIONAL_PORTS):
				bidirectionalPortsString = parser.get(section_name,CONFIG_KEY_BIDIRECTIONAL_PORTS)
				ch.parsePollSetting(bidirectionalPortsString, ch.getBidirectionalPortsList())
				
			if parser.has_option(section_name, CONFIG_KEY_DYNAMIC_FILTERS):
				dynamicFiltersString = parser.get(section_name,CONFIG_KEY_DYNAMIC_FILTERS)
				ch.parsePollSetting(dynamicFiltersString, ch.getDynamicFiltersList())
				
			listChConfigs.append(ch)
			
	except  Exception as e:
		logger.exception(str(e))
		pass

	return listChConfigs
	
	
	