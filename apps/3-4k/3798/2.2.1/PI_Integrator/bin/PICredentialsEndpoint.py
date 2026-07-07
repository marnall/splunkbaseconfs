import splunk
from . import utils
from .rest import CustomRestHandler

class PI_Credentials(CustomRestHandler):
	def __init__(self, method, requestInfo, responseInfo, sessionKey):
		CustomRestHandler.__init__(self, method, requestInfo, responseInfo, sessionKey)
		self.supportedArgs.addReqArg('Username')
		self.supportedArgs.addReqArg('Password')
	def handle_POST(self):
		try:
			if (self.hasRole("admin") or self.hasRole("pi_integrator")) == False:
				return
			payload, isValid, argErrors = self.supportedArgs.validatePayload(self.request['payload'])
			if isValid:
				confObj = self.readUserConfig(True)
				credentials = utils.convertJsonToDict(confObj["PI_Credentials"]["Credentials"])
				if payload["Password"] != credentials["Password"]:
					confObj.beginBatch()
					confObj["PI_Credentials"]["Credentials"] = str(self.request['payload'])
					confObj.commitBatch()
			else:
				self.response.setStatus(400)
				self.response.write(utils.convertDictToJson(argErrors.getErrors()))
		except Exception, e:
			self.response.setStatus(500)
			self.response.write(str(e))
	def handle_GET(self):
		try:
			try:
				confObj = self.readUserConfig()
				self.response.write(str(confObj["PI_Credentials"]["Credentials"]))
			except splunk.ResourceNotFound:
				self.response.write(utils.convertDictToJson({'Username':'','Password':''}))
		except Exception, e:
			self.response.setStatus(500)
			self.response.write(str(e))