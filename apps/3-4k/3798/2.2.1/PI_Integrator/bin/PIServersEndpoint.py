import splunk
from . import utils
from .rest import CustomRestHandler

class PI_Servers(CustomRestHandler):
	def __init__(self, method, requestInfo, responseInfo, sessionKey):
		CustomRestHandler.__init__(self, method, requestInfo, responseInfo, sessionKey)
		self.supportedArgs.addReqArgGrp('PI Servers',False,['DAServers', 'AFServers'],False)
	def handle_POST(self):
		try:
			if self.hasRole("admin") == False:
				return
			payload, isValid, argErrors = self.supportedArgs.validatePayload(self.request['payload'])
			if isValid:
				confObj = self.readGlobalConfig(True)
				confObj.beginBatch()
				for k, v in payload.items():
					if isinstance(v, list):
						confObj["PI_Servers"][k] = str.join(",", v)
					else:
						confObj["PI_Servers"][k] = v
				confObj.commitBatch()
			else:
				self.response.setStatus(400)
				self.response.write(utils.convertDictToJson(argErrors.getErrors()))
		except Exception, e:
			self.response.setStatus(500)
			self.response.write(str(e))
	def handle_GET(self):
		try:
			output = {}
			confObj = self.readUserConfig()
			for key, val in confObj["PI_Servers"].items():
				output[key] = val
			self.response.write(utils.convertDictToJson(output))
		except Exception, e:
			self.response.setStatus(500)
			self.response.write(str(e))