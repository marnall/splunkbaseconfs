import splunk.admin as admin
import splunk.entity as en

class ConfigApp(admin.MConfigHandler):

  def setup(self):
    if self.requestedAction == admin.ACTION_EDIT:
      #for arg in ['url', 'key', 'secret', 'verify_ssl']:
      for arg in ['url', 'key', 'verify_ssl']:
        self.supportedArgs.addOptArg(arg)

  def handleList(self, confInfo):
    confDict = self.readConf("scalr")
    if None != confDict:
      for stanza, settings in confDict.items():
        for key, val in settings.items():
          if key in ['url'] and val in [None, '']:
            val = ''
          if key in ['key'] and val in [None, '']:
            val = ''
          #if key in ['secret'] and val in [None, '']:
            #val = ''
          if key in ['verify_ssl']:
            if int(val) == 0:
              val = '0'
            else:
              val = '1'
          confInfo[stanza].append(key, val)

  def handleEdit(self, confInfo):
    name = self.callerArgs.id
    args = self.callerArgs
    if self.callerArgs.data['url'][0] in [None, '']:
      self.callerArgs.data['url'][0] = ''
    if self.callerArgs.data['key'][0] in [None, '']:
      self.callerArgs.data['key'][0] = ''
    #if self.callerArgs.data['secret'][0] in [None, '']:
      #self.callerArgs.data['secret'][0] = ''
    if int(self.callerArgs.data['verify_ssl'][0]) == 0:
      self.callerArgs.data['verify_ssl'][0] = '0'
    else:
      self.callerArgs.data['verify_ssl'][0] = '1'
    self.writeConf('scalr', 'api', self.callerArgs.data)
 
# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
