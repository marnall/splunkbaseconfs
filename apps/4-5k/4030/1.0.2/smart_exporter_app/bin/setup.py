import splunk.admin as admin
import splunk.entity as en

class ConfigApp(admin.MConfigHandler):
  '''
  Set up supported arguments
  '''

  def setup(self):
    if self.requestedAction == admin.ACTION_EDIT:
      for arg in ['phantomjs_path', 'temp_output', 'email_host', 'email_port','email_pwd','email_user']:
        self.supportedArgs.addOptArg(arg)
        
  

  def handleList(self, confInfo):
    confDict = self.readConf("smartexporter")
    if None != confDict:
      for stanza, settings in confDict.items():
        for key, val in settings.items():
          if key in ['phantomjs_path'] and val in [None, '']:
            val = ''
          if key in ['temp_output'] and val in [None, '']:
            val = ''
          if key in ['email_host'] and val in [None, '']:
            val = ''
          if key in ['email_port'] and val in [None, '']:
            val = ''

          if key in ['email_pwd'] and val in [None, '']:
            val = ''
          if key in ['email_user'] and val in [None, '']:
            val = ''

          confInfo[stanza].append(key, val)
          
  '''
  After user clicks Save on setup page, take updated parameters,
  normalize them, and save them somewhere
  '''
  def handleEdit(self, confInfo):
    name = self.callerArgs.id
    args = self.callerArgs
    
    
    if self.callerArgs.data['phantomjs_path'][0] in [None, '']:
      self.callerArgs.data['phantomjs_path'][0] = ''

    if self.callerArgs.data['email_port'][0] in [None, '']:
      self.callerArgs.data['email_port'][0] = ''

    if self.callerArgs.data['temp_output'][0] in [None, '']:
      self.callerArgs.data['temp_output'][0] = ''

    if self.callerArgs.data['email_host'][0] in [None, '']:
      self.callerArgs.data['email_host'][0] = '' 

    if self.callerArgs.data['email_user'][0] in [None, '']:
      self.callerArgs.data['email_user'][0] = '' 

    if self.callerArgs.data['email_pwd'][0] in [None, '']:
      self.callerArgs.data['email_pwd'][0] = '' 

        
    '''
    Since we are using a conf file to store parameters, 
write them to the [setupentity] stanza
    in app_name/local/myappsetup.conf  
    '''
        
    self.writeConf('smartexporter', 'setup', self.callerArgs.data)
      
# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)