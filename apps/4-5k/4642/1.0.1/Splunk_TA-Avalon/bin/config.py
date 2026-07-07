import splunk.admin as admin
import splunk.entity as en


class ConfigApp(admin.MConfigHandler):
  def setup(self):
    if self.requestedAction == admin.ACTION_EDIT:
      for arg in ['url']:
        self.supportedArgs.addOptArg(arg)

  def handleList(self, confInfo):
    confDict = self.readConf("avalon")
    if confDict is not None:
      for stanza, settings in list(confDict.items()):
        for key, val in list(settings.items()):
          if val in [None, '']:
            val = ''
          confInfo[stanza].append(key, val)

  def handleEdit(self, confInfo):
    for key, value in list(self.callerArgs.data.items()):
      if value in [None, '']:
        self.callerArgs.data[key][0] = ''
      else:
        self.callerArgs.data[key][0] = str(value[0] or '')
    self.writeConf('avalon', 'avalon', self.callerArgs.data)


# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)

