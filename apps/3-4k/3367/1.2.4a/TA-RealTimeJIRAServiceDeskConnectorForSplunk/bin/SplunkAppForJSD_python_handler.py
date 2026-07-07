import splunk.admin as admin
import splunk.entity as en
# import your required python modules

class ConfigApp(admin.MConfigHandler):
  def setup(self):
    if self.requestedAction == admin.ACTION_EDIT:
      for arg in ['auth_token','server_id','server_url','project_key']:
        self.supportedArgs.addOptArg(arg)

  def handleList(self, confInfo):
    confDict = self.readConf("jsd_plugin_props")
    if None != confDict:
      for stanza, settings in confDict.items():
        for key, val in settings.items():
          if key in ['auth_key'] and val in [None, '']:
            val = ''
          if key in ['server_id'] and val in [None, '']:
            val = ''
          if key in ['server_url'] and val in [None, '']:
            val = ''
          if key in ['project_key'] and val in [None, '']:
            val = ''
          confInfo[stanza].append(key, val)

  def handleEdit(self, confInfo):
    name = self.callerArgs.id
    args = self.callerArgs
    self.writeConf('jsd_plugin_props', 'jsd_plugin', self.callerArgs.data)

# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
