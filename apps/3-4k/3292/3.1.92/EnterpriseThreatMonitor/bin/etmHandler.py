# Enterprise Threat Monitor for Splunk
# (c) 2017 ESNC GmbH, Germany.


import splunk.admin as admin
import splunk.entity as en
import urlparse 
import re

class ConfigApp(admin.MConfigHandler):

	def setup(self):
		if self.requestedAction == admin.ACTION_EDIT:
			for arg in [ 'portal_url']:
				self.supportedArgs.addOptArg(arg)


	def handleList(self, confInfo):
		confDict = self.readConf("apisettings")
		if None != confDict:
			for stanza, settings in confDict.items():
				for key, val in settings.items():
					confInfo[stanza].append(key, val)


	def handleEdit(self, confInfo):
		name = self.callerArgs.id
		args = self.callerArgs




		if self.callerArgs.data['portal_url'][0] in [None, '']:
			self.callerArgs.data['portal_url'][0]  = ''


		portal_url = self.callerArgs.data['portal_url'][0].lower()
		if portal_url not in ['', '[Required]']:
			pieces = urlparse.urlparse(portal_url)
			if pieces.scheme != 'https' :
				self.callerArgs.data['portal_url'][0] =''
						

		self.writeConf('apisettings', 'api_config', self.callerArgs.data)
      
admin.init(ConfigApp, admin.CONTEXT_NONE)