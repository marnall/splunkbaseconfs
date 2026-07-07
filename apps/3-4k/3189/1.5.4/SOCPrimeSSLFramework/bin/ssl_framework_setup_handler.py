import splunk.admin as admin
import splunk.entity as en
import re

# import your required python modules
import os

'''
Copyright (C) 2005 - 2010 Splunk Inc. All Rights Reserved.
Description:  This skeleton python script handles the parameters in the configuration page.

      handleList method: lists configurable parameters in the configuration page
      corresponds to handleractions = list in restmap.conf

      handleEdit method: controls the parameters and saves the values
      corresponds to handleractions = edit in restmap.conf

'''

currentdir = os.path.dirname(os.path.abspath(__file__))

class ConfigApp(admin.MConfigHandler):
  '''
  Set up supported arguments
  '''
  def setup(self):
    if self.requestedAction == admin.ACTION_EDIT:
      for arg in ['domainslist','proxy_host','proxy_port','proxy_used','proxy_auth_used','proxy_user','proxy_password']:
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
    confDict = self.readConf("sslframework")
    if None != confDict:
      for stanza, settings in confDict.items():
        for key, val in settings.items():
	    if key in ['domainslist'] and val in [None, '']:
	        val = ''
            if key in ['proxy_host','proxy_port','proxy_user','proxy_password'] and val in [None, '']:
                val = ''
	    if key in ['proxy_used','proxy_path_used']:
                val = '0'
            else:
                val = '1'
            confInfo[stanza].append(key, val)

  '''
  After user clicks Save on setup screen, take updated parameters,
  normalize them, and save them somewhere
  '''
  def handleEdit(self, confInfo):
    name = self.callerArgs.id
    args = self.callerArgs
    #print name
    #print args

    if self.callerArgs.data['domainslist'][0] in [None, '']:
      self.callerArgs.data['domainslist'][0] = ''
      
    if self.callerArgs.data['proxy_host'][0] in [None, '']:
      self.callerArgs.data['proxy_host'][0] = 'empty'

    if self.callerArgs.data['proxy_port'][0] in [None, '']:
      self.callerArgs.data['proxy_port'][0] = 'empty'

    if int(self.callerArgs.data['proxy_used'][0]) == 1:
      self.callerArgs.data['proxy_used'][0] = '1'
    else:
      self.callerArgs.data['proxy_used'][0] = '0'

    if int(self.callerArgs.data['proxy_auth_used'][0]) == 1:
      self.callerArgs.data['proxy_auth_used'][0] = '1'
    else:
      self.callerArgs.data['proxy_auth_used'][0] = '0'

    if self.callerArgs.data['proxy_user'][0] in [None, '']:
      proxy_name = 0
      self.callerArgs.data['proxy_user'][0] = 'empty'
    else:
      proxy_name = self.callerArgs.data['proxy_user'][0]
      self.callerArgs.data['proxy_user'][0] = 'configured'

    if self.callerArgs.data['proxy_password'][0] in [None, '']:
      proxy_pass = 0
      self.callerArgs.data['proxy_password'][0] = 'empty'
    else:
      proxy_pass = self.callerArgs.data['proxy_password'][0]
      self.callerArgs.data['proxy_password'][0] = 'configured' 

    validDomainRegex = re.compile("[^()]")
    validDomain = re.search(validDomainRegex, self.callerArgs.data['domainslist'][0])
    if not validDomain:
                     raise admin.ArgValidationException, "SOCPRIME_SSLFARMEWORK_SETUP-INPUT_ERROR: Empty domains list"

    filename = os.path.normpath(currentdir +'/../local/domainlist.txt')
    with open(filename, 'w') as f:
        domainlist = self.callerArgs.data['domainslist'][0].split(',')
        for row in domainlist:
            f.write(row.strip()+'\n')

       
    '''
    Since we are using a conf file to store parameters,
write them to the [setupentity] stanza
    in <appname>/local/myappsetup.conf
    '''
    self.writeConf('sslframework', 'main', self.callerArgs.data)


#################################################################################
    if proxy_pass != 0 and proxy_name != 0:
    	sessionKey = self.getSessionKey()
    	if len(sessionKey) == 0:
    		raise admin.ArgValidationException, "Did not receive a session key from splunkd."
    	try:
		if len(proxy_name) != 0 or len(proxy_pass) != 0:
			creds = en.getEntity('/storage/passwords/','_new', sessionKey=sessionKey)
			creds["name"] = proxy_name
			creds["password"] = proxy_pass
			creds.namespace = 'SOCPrimeSSLFramework'
			en.setEntity(creds, sessionKey=sessionKey)
		else:
			creds = en.getEntity('/storage/passwords/','_new', sessionKey=sessionKey)
    	except Exception as e:
		raise admin.ArgValidationException, "Failed to create credential!" 
##################################################################################
# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
