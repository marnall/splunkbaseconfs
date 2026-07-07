import splunk.admin as admin
import splunk.entity as en

class ConfigApp(admin.MConfigHandler):
  def setup(self):
      if self.requestedAction == admin.ACTION_EDIT:
          for arg in ['http_proxy', 'https_proxy', 'useragent']:
              self.supportedArgs.addOptArg(arg)

  def handleList(self, confInfo):
    confDict = self.readConf("urlexpander")
    if None != confDict:
      for stanza, settings in confDict.items():
        for key, val in settings.items():
          confInfo[stanza].append(key,val)

  def handleEdit(self, confInfo):
    name = self.callerArgs.id
    args = self.callerArgs

    if self.callerArgs.data['http_proxy'][0] in [None,'']:
      self.callerArgs.data['http_proxy'][0] = ''

    if self.callerArgs.data['https_proxy'][0] in [None,'']:
      self.callerArgs.data['https_proxy'][0] = ''

    if self.callerArgs.data['useragent'][0] in [None,'']:
      self.callerArgs.data['useragent'][0] = ''

    self.writeConf('urlexpander', 'settings', self.callerArgs.data)

admin.init(ConfigApp, admin.CONTEXT_NONE)
