import splunk.admin as admin
import splunk.entity as en
class ConfigApp(admin.MConfigHandler):
  def setup(self):
    if self.requestedAction == admin.ACTION_EDIT:
      for arg in ['apikey']:
        self.supportedArgs.addOptArg(arg)

  def handleList(self, confInfo):
    confDict = self.readConf("sdgsetup")
    if None != confDict:
      for stanza, settings in confDict.items():
        for key, val in settings.items():
          if key in ['apikey'] and val in [None, '']:
            val = ''
          confInfo[stanza].append(key, val)
          
  def handleEdit(self, confInfo):
    name = self.callerArgs.id
    args = self.callerArgs
     
    self.writeConf('sdgsetup', 'sdg_config', self.callerArgs.data)
      
admin.init(ConfigApp, admin.CONTEXT_NONE)
