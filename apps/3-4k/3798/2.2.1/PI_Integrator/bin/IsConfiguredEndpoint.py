import splunk
from . import utils
from .rest import CustomRestHandler

class IsConfigured(CustomRestHandler):
	def __init__(self, method, requestInfo, responseInfo, sessionKey):
		CustomRestHandler.__init__(self, method, requestInfo, responseInfo, sessionKey)
		self.supportedArgs.addReqArg('Trial_Key')
		self.supportedArgs.addReqArg('Key')
		self.supportedArgs.addReqArg('Server')
		self.supportedArgs.addReqArg('Port')
		self.supportedArgs.addReqArg('Endpoint')
		self.supportedArgs.addReqArg('UseSSL')
		self.supportedArgs.addReqArg('AllowSelfSigned')
		self.supportedArgs.addReqArgGrp('Credentials',True,['Username', 'Password'],True)
		self.supportedArgs.addReqArgGrp('PI Servers',False,['DAServers', 'AFServers'],False)
	def handle_GET(self):
		try:
			output = {'isConfigured': True}
			try:
				confObj = self.readUserConfig()
				payload, isValid, argErrors = self.supportedArgs.validatePayload(confObj.findKeys('*'))
				output['isConfigured'] = isValid
			except splunk.ResourceNotFound:
				output['isConfigured'] = False
			self.response.write(utils.convertDictToJson(output))
		except Exception, e:
			self.response.setStatus(500)
			self.response.write(str(e))