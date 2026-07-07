import splunk.admin as admin
import splunk.entity as en
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

  def setup(self):
    if self.requestedAction == admin.ACTION_EDIT:
      for arg in ['token', 'argos_url']:
        self.supportedArgs.addOptArg(arg)


  def handleList(self, confInfo):
    confDict = self.readConf("config")
    if None != confDict:
      for stanza, settings in confDict.items():
        for key, val in settings.items():
          if key in ['token'] and val in [None, '']:
            val = ''
          if key in ['argos_url'] and val in [None, '']:
            val = ''
		  
          confInfo[stanza].append(key, val)

  def handleEdit(self, confInfo):
    name = self.callerArgs.id
    args = self.callerArgs

    if self.callerArgs.data['token'][0] in [None, '']:
      self.callerArgs.data['token'][0] = ''

    if self.callerArgs.data['argos_url'][0] in [None, '']:
     self.callerArgs.data['argos_url'][0] = ''

    self.writeConf('config', 'cyberint', self.callerArgs.data)

# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
