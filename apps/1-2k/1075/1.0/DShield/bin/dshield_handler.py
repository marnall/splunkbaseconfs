import splunk.admin as admin
import splunk.entity as en
import logging as logger
import os.path

class ConfigDShieldApp(admin.MConfigHandler):

	def setup(self):
		if self.requestedAction == admin.ACTION_EDIT:
			for arg in ['interval']:
				self.supportedArgs.addOptArg(arg)

	def handleList(self, confInfo):
		confDict = self.readConf("dshield")
		if None != confDict:
			for stanza, settings in confDict.items():
				for key, val in settings.items():
					if key in ['interval']:
						val = '10 5 * * *'
					confInfo[stanza].append(key, val)

	def handleEdit(self, confInfo):
		name = self.callerArgs.id
		args = self.callerArgs

		if self.callerArgs.data['interval'][0] in [None, '']:
			self.callerArgs.data['interval'][0] = ''

		self.writeConf('dshield', 'dshield_settings', self.callerArgs.data)

		sysPlatform = sys.platform

		# Set fields
		self.callerArgs.data['index'] = 'dshield'
		self.callerArgs.data['sourcetype'] = 'getdshield_log'

		if not sysPlatform.lower() in ('win32','win64'):
			self.writeConf('inputs', 'script://$SPLUNK_HOME/etc/apps/DShield/bin/get_dshield_ips.py', self.callerArgs.data)
		else:
			self.writeConf('inputs', r'script://$SPLUNK_HOME\etc\apps\DShield\bin\get_dshield_ips.py', self.callerArgs.data)

		self.callerArgs.data['interval'] = '*/20 * * * *'
		self.callerArgs.data['sourcetype'] = 'getdiaries_log'

		if not sysPlatform.lower() in ('win32','win64'):
			self.writeConf('inputs', 'script://$SPLUNK_HOME/etc/apps/DShield/bin/get_isc_diaries.py', self.callerArgs.data)
		else:
			self.writeConf('inputs', r'script://$SPLUNK_HOME\etc\apps\DShield\bin\get_isc_diaries.py', self.callerArgs.data)

		en.getEntities('data/inputs/monitor/_reload', sessionKey = self.getSessionKey())
		en.getEntities('data/inputs/script/_reload', sessionKey = self.getSessionKey())
		
# initialize the handler
admin.init(ConfigDShieldApp, admin.CONTEXT_NONE)

