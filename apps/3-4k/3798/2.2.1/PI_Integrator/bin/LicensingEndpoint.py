import splunk
from . import utils
from .rest import CustomRestHandler

class Licensing(CustomRestHandler):
	def __init__(self, method, requestInfo, responseInfo, sessionKey):
		CustomRestHandler.__init__(self, method, requestInfo, responseInfo, sessionKey)
		self.supportedArgs.addReqArg('Key')
	def handle_POST(self):
		try:
			if self.hasRole("admin") == False:
				return
			payload, isValid, argErrors = self.supportedArgs.validatePayload(self.request['payload'])
			if isValid:
				confObj = self.readGlobalConfig(True)
				if payload["Key"] != confObj["Licensing"]["Trial_Key"]:
					try:
						if not self.deconstructLicense(payload["Key"])["Details"]["UserId"]:
							isValid = False
							argErrors.addError('Key', 'User ID does not correspond with the supplied Licence key.')
					except Exception, e:
						isValid = False
						argErrors.addError('Key', 'Invaid licence key.')
					if isValid:
						confObj.beginBatch()
						for k, v in payload.items():
							if isinstance(v, list):
								confObj["Licensing"][k] = str.join(",", v)
							else:
								confObj["Licensing"][k] = v
						confObj.commitBatch()
			if not isValid:
				self.response.setStatus(400)
				self.response.write(utils.convertDictToJson(argErrors.getErrors()))
		except Exception, e:
			self.response.setStatus(500)
			self.response.write(str(e))
	def handle_GET(self):
		try:
			output = {}
			confObj = self.readUserConfig()
			for key, val in confObj["Licensing"].items():
				output[key] = val
				if key == 'Key' and not (val in [None, ''] or len(val) <= 0):
					try: 
						output["Details"] = self.deconstructLicense(val)["Details"]
					except Exception, e:
						output["Details"] = ''
			output["UserID"] = output["Details"]["UserId"];
			self.response.write(utils.convertDictToJson(output))
		except Exception, e:
			self.response.setStatus(500)
			self.response.write(str(e))
	def handle_DELETE(self):
		try:
			if self.hasRole("admin") == False:
				return
			confObj = self.readGlobalConfig(True)
			confObj["Licensing"]["Key"] = confObj["Licensing"]["Trial_Key"]
		except Exception, e:
			self.response.setStatus(500)
			self.response.write(str(e))
	def executeCmd(self, cmdArgs):
		import subprocess
		try:
			return subprocess.check_output(cmdArgs)
		except subprocess.CalledProcessError:
			return ''
	def parseCmdOutput(self, platform, result):
		resultLines = result.split('\n')
		if platform == 'Linux':
			if len(resultLines) >= 1:
				return resultLines[0].strip()
		elif platform == 'Windows':
			if len(resultLines) >= 2:
				return resultLines[1].strip()
	def deconstructLicense(self, license):
		import base64
		return utils.convertJsonToDict(base64.b64decode(license))