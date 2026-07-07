import splunk
from . import utils
from .rest import CustomRestHandler

class MeetsSystemRequirements(CustomRestHandler):
	def __init__(self, method, requestInfo, responseInfo, sessionKey):
		CustomRestHandler.__init__(self, method, requestInfo, responseInfo, sessionKey)
	def handle_GET(self):
		output = []
		try:
			javaVersion = self.getJavaVersion()
			if (javaVersion in [None, ''] or len(javaVersion.strip()) <= 0):
				output.append({"requirement": "Java Runtime Environment", "valid": False})
			else :
				output.append({"requirement": "Java Runtime Environment", "valid": True})
			self.response.setStatus(200)
			self.response.write(utils.convertDictToJson(output))
		except Exception, e:
			self.response.setStatus(500)
			self.response.write(str(e))
	def getJavaVersion(self):
		import platform
		import subprocess
		try:
			#have to use check_output as splunk comes with python 2.7
			cmdOutput = subprocess.check_output(["java", "-version"], stderr=subprocess.STDOUT)
			result = cmdOutput.split('\n')[0].strip()
			if ('version' in result):
				return result[::-1][1:result.find('"',1)][::-1]
			return ''
		except Exception, e:
			return ''