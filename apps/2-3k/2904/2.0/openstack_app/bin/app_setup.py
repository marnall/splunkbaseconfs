#!/usr/bin/python
'''
This script stores and lists domain and baseurl information into myconf.conf
'''

#Import from standard libraries
import splunk.admin as admin
import splunk.entity as en

class ConfigApp(admin.MConfigHandler):
  def setup(self):
    if self.requestedAction == admin.ACTION_EDIT:
      for arg in ['baseurl','tenant']:
        self.supportedArgs.addOptArg(arg)

  def handleList(self, confInfo):
    confDict = self.readConf("myconf")
    if None != confDict:
      for stanza, settings in confDict.items():
        for key, val in settings.items():
          if key in ['baseurl'] and val in [None, '']:
            val = ''
          if key in ['tenant'] and val in [None, '']:
            val = ''
          confInfo[stanza].append(key, val)
          
  def handleEdit(self, confInfo):
    name = self.callerArgs.id
    args = self.callerArgs  
    self.writeConf('myconf', 'userinfo', self.callerArgs.data)
      
admin.init(ConfigApp, admin.CONTEXT_NONE)
