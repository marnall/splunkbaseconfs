import splunk.admin as admin
import splunk.entity as en
import re

# import your required python modules

'''
Copyright (C) 2005 - 2010 Splunk Inc. All Rights Reserved.
Description:  This skeleton python script handles the parameters in the configuration page.

handleList method: lists configurable parameters in the configuration page
corresponds to handleractions = list in restmap.conf

handleEdit method: controls the parameters and saves the values 
corresponds to handleractions = edit in restmap.conf

'''

class ConfigApp(admin.MConfigHandler):
	'''
	Set up supported arguments
	'''
	def setup(self):
		if self.requestedAction == admin.ACTION_EDIT:
			for arg in ['param.teamSecret']:
				self.supportedArgs.addOptArg(arg)
        
	'''
	Read the initial values of the parameters from the custom file
	alert_actions.conf, and write them to the setup page. 

	If the app has never been set up,
	uses .../app_name/default/alert_actions.conf. 

	If app has been set up, looks at 
	.../local/alert_actions.conf first, then looks at 
	.../default/alert_actions.conf only if there is no value for a field in
	.../local/alert_actions.conf

	For boolean fields, may need to switch the true/false setting.

	For text fields, if the conf file says None, set to the empty string.
	'''

	def handleList(self, confInfo):
		confDict = self.readConf("alert_actions")
		if None != confDict:
			for stanza, settings in confDict.items():
				for key, val in settings.items():
					if key in ['param.teamSecret']:	
						confInfo[stanza].append(key, val)
          
	'''
	After user clicks Save on setup page, take updated parameters,
	normalize them, and save them somewhere
	'''
	def handleEdit(self, confInfo):
       
		'''
		Since we are using a conf file to store parameters, 
		write them to the [signl4] stanza
		in app_name/local/signl4_setup.conf  
		'''
        
		# Make sure that the input we save is valid
		s4teamId = str(self.callerArgs.data['param.teamSecret'][0])
		matchObj = re.search('^[a-zA-Z0-9]+$', s4teamId, flags=0)
		
		if (matchObj is None):
			# Invalid entry, reset to default value
			self.callerArgs.data['param.teamSecret'][0] = 'yourSecret'
		
		self.writeConf('alert_actions', 'signl4', self.callerArgs.data)
      
# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)