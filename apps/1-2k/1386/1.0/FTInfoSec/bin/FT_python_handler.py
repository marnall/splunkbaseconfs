import splunk.admin as admin
import splunk.entity as en
#import splunk.clilib.app as app
# import your required python modules

class FTConfigApp(admin.MConfigHandler):
  '''
  Set up supported arguments
  '''
  def setup(self):
    if self.requestedAction == admin.ACTION_EDIT:
      for arg in ['url']:
        self.supportedArgs.addOptArg(arg)

  '''
  Read the initial values of the parameters from the custom file
      myappsetup.conf, and write them to the setup screen. 

  If the app has never been set up,
      uses .../<appname>/default/myappsetup.conf. 

  If app has been set up, looks at 
      .../local/myappsetup.conf first, then looks at 
  .../default/myappsetup.conf only if there is no value for a field in
      .../local/myappsetup.conf

  For boolean fields, may need to switch the true/false setting.

  For text fields, if the conf file says None, set to the empty string.
  '''

  def handleList(self, confInfo):
    confDict = self.readConf("ftsetup")
    if None != confDict:
      for stanza, settings in confDict.items():
        for key, val in settings.items():
          if key in ['url'] and val in [None, '']:
            val = 'https://<yourservername>'
          confInfo[stanza].append(key, val)

  '''
  After user clicks Save on setup screen, take updated parameters,
  normalize them, and save them somewhere
  '''
  def handleEdit(self, confInfo):
    name = self.callerArgs.id
    args = self.callerArgs

    if self.callerArgs.data['url'][0] in [None, '']:
      self.callerArgs.data['url'][0] = ''


    '''
    Since we are using a conf file to store parameters, 
write them to the [setupentity] stanza
    in <appname>/local/myappsetup.conf  
    '''

    self.writeConf('ftsetup', 'filetrekserver', self.callerArgs.data)
#    app.disableApp("FileTrek")
#    app.enableApp("FileTrek")
    

# initialize the handler
admin.init(FTConfigApp, admin.CONTEXT_NONE)

