import splunk.admin as admin
import splunk.entity as en

class ConfigApp(admin.MConfigHandler):

  def setup(self):
    if self.requestedAction == admin.ACTION_EDIT:
      for arg in ['host', 'interval', 'username', 'password']:
        self.supportedArgs.addOptArg(arg)

  def handleList(self, confInfo):
    confDict = self.readConf("login_pi")
    if None != confDict:
      for stanza, settings in confDict.items():
        for key, val in settings.items():
          if key in ['host'] and val in [None, '']:
            val = ''
          if key in ['username'] and val in [None, '']:
            val = ''
          if key in ['password'] and val in [None, '']:
            val = ''
          confInfo[stanza].append(key, val)

  def handleEdit(self, confInfo):
    name = self.callerArgs.id
    args = self.callerArgs
    
    if int(self.callerArgs.data['interval'][0]) < 5:
      self.callerArgs.data['interval'][0] = '5'

    if self.callerArgs.data['host'][0] in [None, '']:
      self.callerArgs.data['host'][0] = ''  

    if self.callerArgs.data['username'][0] in [None, '']:
      self.callerArgs.data['username'][0] = ''  
      
    if self.callerArgs.data['password'][0] in [None, '']:
      self.callerArgs.data['password'][0] = ''  

    self.writeConf('login_pi', 'setup', self.callerArgs.data)

admin.init(ConfigApp, admin.CONTEXT_NONE)