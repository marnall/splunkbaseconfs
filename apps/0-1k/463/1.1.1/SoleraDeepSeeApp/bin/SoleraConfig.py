#
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
import splunk.admin as admin
import splunk.entity as en

configArgs = []
scalarArgs = []
joinArgs = []

class SoleraConfig(admin.MConfigHandler):
	def setup(self):
		configArgs = []
		scalarArgs = []
		joinArgs = []

		if self.requestedAction == admin.ACTION_EDIT:
			scalarArgs = ['hostname','port','username','password']
			joinArgs = [
				'FieldsProtocol','FieldsSourceAddress','FieldsSourcePort',
				'FieldsDestinationAddress','FieldsDestinationPort'
			]
			configArgs = scalarArgs + joinArgs
			for arg in configArgs:
				self.supportedArgs.addOptArg(arg)
				
	'''
	Read the initial values of the parameters from the custom file solera.conf
	and write them to the setup screen. 
	If the app has never been set up, uses <appname>/default/solera.conf. 
	If app has been set up, looks at local/solera.conf first, then looks at 
	default/solera.conf only if there is no value for a field in local/solera.conf

	For boolean fields, may need to switch the true/false setting
	For text fields, if the conf file says None, set to the empty string.
	'''
	def handleList(self, confInfo):
		confDict = self.readConf("solera")
		if None != confDict:
			for stanza, settings in confDict.items():
				for key, val in settings.items():
					if key in scalarArgs and val in [None, '']:
						val = ''
					elif key in joinArgs and val in [None, '']:
						val = ''
					elif key in joinArgs:
						val = ','.join(val)

					confInfo[stanza].append(key, val)
					
	'''
	After user clicks Save on setup screen, take updated parameters, normalize them, and 
	save them somewhere
	'''
	def handleEdit(self, confInfo):
		name = self.callerArgs.id
		args = self.callerArgs

		if self.callerArgs.data['hostname'][0] in [None, '']:
			self.callerArgs.data['hostname'][0] = ''

		if self.callerArgs.data['port'][0] in [None, '']:
			self.callerArgs.data['port'][0] = ''

		if self.callerArgs.data['username'][0] in [None, '']:
			self.callerArgs.data['username'][0] = ''

		if self.callerArgs.data['password'][0] in [None, '']:
			self.callerArgs.data['password'][0] = ''

		if self.callerArgs.data['FieldsProtocol'][0] in [None, '']:
			self.callerArgs.data['FieldsProtocol'][0] = ''

		if self.callerArgs.data['FieldsSourceAddress'][0] in [None, '']:
			self.callerArgs.data['FieldsSourceAddress'][0] = ''

		if self.callerArgs.data['FieldsSourcePort'][0] in [None, '']:
			self.callerArgs.data['FieldsSourcePort'][0] = ''

		if self.callerArgs.data['FieldsDestinationAddress'][0] in [None, '']:
			self.callerArgs.data['FieldsDestinationAddress'][0] = ''

		if self.callerArgs.data['FieldsDestinationPort'][0] in [None, '']:
			self.callerArgs.data['FieldsDestinationPort'][0] = ''

		'''
		Since we are using a conf file to store parameters, write them to the [appliance] stanza
		in <appname>/local/solera.conf  
		'''
				
		self.writeConf('solera', 'appliance', self.callerArgs.data)
			
# initialize the handler
admin.init(SoleraConfig, admin.CONTEXT_NONE)
