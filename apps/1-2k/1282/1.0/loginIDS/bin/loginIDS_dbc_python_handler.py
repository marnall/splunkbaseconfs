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

'''

Taken from http://docs.splunk.com/Documentation/Splunk/4.3.2/Developer/SetupExampleCustom
and modified to be used with the LoginIDS-App

'''

class ConfigApp(admin.MConfigHandler):
  '''
  Set up supported arguments
  '''
  def setup(self):
    if self.requestedAction == admin.ACTION_EDIT:
      for arg in ['db_type', 'db_location', 'db_user', 'db_password']:
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
    confDict = self.readConf("loginIDS")
    if None != confDict:
      for stanza, settings in confDict.items():
        for key, val in settings.items():
          confInfo[stanza].append(key, val)
          
  '''
  After user clicks Save on setup screen, take updated parameters,
  normalize them, and save them somewhere
  '''
  def handleEdit(self, confInfo):
    name = self.callerArgs.id
    args = self.callerArgs
    
    if not self.callerArgs.data['db_type'][0] in ['SQLite', 'MySQL']:
      sys.stderr.write("Valid databasetypes are onle SQLite and MySQL.")
      exit(2)

    if self.callerArgs.data['db_user'][0] in [None, '']:
      self.callerArgs.data['db_user'][0] = ''  

    if self.callerArgs.data['db_password'][0] in [None, '']:
      self.callerArgs.data['db_password'][0] = ''  
        
    '''
    Since we are using a conf file to store parameters, 
write them to the [setupentity] stanza
    in <appname>/local/myappsetup.conf  
    '''
        
    self.writeConf('loginIDS', 'dbconnection', self.callerArgs.data)
      
# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
