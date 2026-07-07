import splunk
from . import utils
from .logs import LogHandler

class NotImplementedException(Exception):
	def __init__(self, msg):
		Exception.__init__(self, msg)
class CustomRestHandler(splunk.rest.BaseRestHandler):
	def __init__(self, method, requestInfo, responseInfo, sessionKey):
		splunk.rest.BaseRestHandler.__init__(self, method, requestInfo, responseInfo, sessionKey)
		self.supportedArgs = utils.ArgSpecList()
		self.logger = LogHandler().getLogger("CustomRestHandler")
	def handle_POST(self):
		self.actionNotImplemented()
	def handle_GET(self):
		self.actionNotImplemented()
	def handle_DELETE(self):
		self.actionNotImplemented()
	def handle_PUT(self):
		self.actionNotImplemented()
	def actionNotImplemented(self):
		raise NotImplementedException("This handler claims to support this action (%d), but has not implemented it." % self.method)
	def readGlobalConfig(self, createMissing = False):
		return self.__readConfig("config", "-", createMissing)
	def readUserConfig(self, createMissing = False):
		return self.__readConfig("config", self.request['userName'], createMissing)
	def __readConfig(self, confName, ownerName, createMissing = False):
		import splunk.bundle as bundle
		try:
			return bundle.getConf(
				confName,
				sessionKey=self.sessionKey,
				namespace="PI_Integrator",
				owner=ownerName
			)
		except splunk.ResourceNotFound:
			if createMissing:
				return bundle.createConf(
					confName,
					sessionKey=self.sessionKey,
					namespace="PI_Integrator",
					owner=ownerName
				)
		return
	def hasRole(self, role):
		try:
			serverResponse, serverContent = splunk.rest.simpleRequest(
				'authentication/current-context/context?output_mode=json', 
				sessionKey=self.sessionKey, 
				method='GET', 
				raiseAllErrors=True
			)
			serverContent = utils.convertJsonToDict(serverContent)
			return role in serverContent["entry"][0]["content"]["roles"]
		except Exception, e:
			self.response.setStatus(500)
			self.response.write(str(e))