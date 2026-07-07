import splunk.admin as admin
import splunk.entity as en

class ConfigApp(admin.MConfigHandler):
	def setup(self):
		if self.requestedAction == admin.ACTION_EDIT:
			for arg in ['dm5_path']:
				self.supportedArgs.addOptArg(arg)

	def handleList(self, confInfo):
		confDict = self.readConf("dm5")
		if None != confDict:
			for stanza, settings in confDict.items():
				for key, val in settings.items():
					if key in ['dm5_path'] and val in [None, '']:
						val = ''
					confInfo[stanza].append(key, val)

	def handleEdit(self, confInfo):
		name = self.callerArgs.id
		args = self.callerArgs

		if self.callerArgs.data['dm5_path'][0] in [None, '']:
			self.callerArgs.data['dm5_path'][0] = ''

		self.writeConf('dm5', 'setupentity', self.callerArgs.data)

# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
