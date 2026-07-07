### Copyright 2017 RTP Technology Inc. - Full details found here: $SPLUNK_HOME/etc/apps/Splunk_TA_RTP-Health-Checker/defaut/LICENSE.txt

import ConfigParser
import errno
import os
import requests
import splunk.admin as admin
import splunk.mining.dcutils as dcu
#import splunk.Intersplunk
import sys
import uuid

logger = dcu.getLogger()

class rtpHealthCheckerConf(admin.MConfigHandler):
  CONF_FILE = 'rtpHealthChecker'
  APP_NAME = 'Splunk_TA_RTP-Health-Checker'
  

  def setup(self):
    if self.requestedAction in (admin.ACTION_CREATE,admin.ACTION_EDIT):
      self.supportedArgs.addReqArg("company")
      self.supportedArgs.addReqArg("contact_first_name")
      self.supportedArgs.addReqArg("contact_last_name")
      self.supportedArgs.addReqArg("contact_email")
      self.supportedArgs.addReqArg("contact_phone")
      self.supportedArgs.addReqArg("admin_user")
      self.supportedArgs.addReqArg("send_capacity_data")
      self.supportedArgs.addReqArg("send_general_data")
      self.supportedArgs.addReqArg("send_health_data")
      self.supportedArgs.addReqArg("no_internet")
      self.supportedArgs.addReqArg("license_agreement")

  def handleEdit(self, confInfo):
    sessionKey = self.getSessionKey()
    scriptDir = sys.path[0]
    confPath = os.path.join(scriptDir,'..','etc','apps',self.APP_NAME,'local','rtpHealthChecker.conf')
    inputsConfPath = os.path.join(scriptDir,'..','etc','apps',self.APP_NAME,'local','inputs.conf')

    if not 'company' in self.callerArgs.data.keys() and self.callerArgs['company']:
      raise admin.ArgValidationException, "A value for company must be provided"
    if not 'contact_first_name' in self.callerArgs.data.keys() and self.callerArgs['contact_first_name']:
      raise admin.ArgValidationException, "A value for contact_first_name must be provided"
    if not 'contact_last_name' in self.callerArgs.data.keys() and self.callerArgs['contact_last_name']:
      raise admin.ArgValidationException, "A value for contact_last_name must be provided" 
    if not 'contact_email' in self.callerArgs.data.keys() and self.callerArgs['contact_email']:
      raise admin.ArgValidationException, "A correct value for contact_email must be provided"
    if not 'contact_phone' in self.callerArgs.data.keys() and self.callerArgs['contact_phone']:
      raise admin.ArgValidationException, "A value for contact_phone must be provided"
    if not 'admin_user' in self.callerArgs.data.keys() and self.callerArgs['admin_user']:
      raise admin.ArgValidationException, "A value for admin user must be provided"
    if not 'send_capacity_data' in self.callerArgs.data.keys() and self.callerArgs['send_capacity_data']:
      raise admin.ArgValidationException, "A value for send_capacity_data must be provided"
    if not 'send_general_data' in self.callerArgs.data.keys() and self.callerArgs['send_general_data']:
      raise admin.ArgValidationException, "A value for send_general_data must be provided"
    if not 'send_health_data' in self.callerArgs.data.keys() and self.callerArgs['send_health_data']:
      raise admin.ArgValidationException, "A value for send_health_data must be provided"
    if not 'no_internet' in self.callerArgs.data.keys() and self.callerArgs['no_internet']:
      raise admin.ArgValidationException, "A value for internet access must be provided"
    if not 'license_agreement' in self.callerArgs.data.keys() and self.callerArgs['license_agreement']:
      raise admin.ArgValidationException, "The license agreement must be accepted"
    # try to setup the vars & uid
    try:
      company = self.callerArgs['company'][0]
      contact_first_name = self.callerArgs['contact_first_name'][0]
      contact_last_name = self.callerArgs['contact_last_name'][0]
      contact_email = self.callerArgs['contact_email'][0]
      contact_phone = self.callerArgs['contact_phone'][0]
      admin_user = self.callerArgs['admin_user'][0]
      send_capacity_data = bool(int(self.callerArgs['send_capacity_data'][0]))
      send_general_data = bool(int(self.callerArgs['send_general_data'][0]))
      send_health_data = bool(int(self.callerArgs['send_health_data'][0]))
      no_internet = bool(int(self.callerArgs['no_internet'][0]))
      license_agreement = bool(int(self.callerArgs['license_agreement'][0]))
      uid = uuid.uuid4()
      payload = '{"uid":"' + str(uid) + '","company":"' + company + '","contact_first_name":"' + \
      contact_first_name + '","contact_last_name":"' + contact_last_name + '","contact_email":"' + \
      contact_email + '","contact_phone":"' + contact_phone + '","send_capacity_data":' + \
      str(send_capacity_data).lower() + ',"send_general_data":' + str(send_general_data).lower() + \
      ',"send_health_data":' + str(send_health_data).lower() + ',"no_internet":' + str(no_internet).lower() + ',"license_agreement":' + str(license_agreement).lower()
    except Exception as e:
      logger.error(str(e))

    #modify & write rtpHealthChecker.conf
    if not os.path.exists(os.path.dirname(confPath)):
     try:
      os.makedirs(os.path.dirname(confPath))
     except OSError as exc: 
      if exc.errno != errno.EEXIST:
       raise

    try:
     config = ConfigParser.RawConfigParser()
     config.optionxform = str
     config.read(confPath)
     if not config.has_section("settings"):
      config.add_section("settings")
     config.set("settings","send_capacity_data",send_capacity_data)
     config.set("settings","send_general_data",send_general_data)
     config.set("settings","send_health_data",send_health_data)
     config.set("settings","no_internet",no_internet) 
     config.set("settings","license_agreement",license_agreement)	 
     config.set("settings","payload",payload)
     with open(confPath,"wb") as confFile:
      config.write(confFile)
    except Exception as e:
     logger.error(str(e))

    #modify & write inputs.conf
    if not os.path.exists(os.path.dirname(inputsConfPath)):
     try:
      os.makedirs(os.path.dirname(inputsConfPath))
     except OSError as exc: 
      if exc.errno != errno.EEXIST:
       raise

    try:
     # if send data was selected, enable the input that triggers the data generation searches
     if send_capacity_data == True or send_general_data == True or send_health_data == True:
      config = ConfigParser.RawConfigParser()
      config.optionxform = str
      config.read(inputsConfPath)
      if not config.has_section("script://$SPLUNK_HOME/etc/apps/Splunk_TA_RTP-Health-Checker/bin/rtpHealthChecker.py"):
       config.add_section("script://$SPLUNK_HOME/etc/apps/Splunk_TA_RTP-Health-Checker/bin/rtpHealthChecker.py")
      config.set("script://$SPLUNK_HOME/etc/apps/Splunk_TA_RTP-Health-Checker/bin/rtpHealthChecker.py","disabled",0)
      config.set("script://$SPLUNK_HOME/etc/apps/Splunk_TA_RTP-Health-Checker/bin/rtpHealthChecker.py","passAuth",admin_user)
      with open(inputsConfPath,"wb") as confFile:
       config.write(confFile)
    except Exception as e:
     logger.error(str(e))

    #prompt user to restart splunk web
    headers = {'Authorization':''}
    headers['Authorization'] = 'Splunk ' + sessionKey  
    data = {'name':'restart_link','value':'Splunk must be restarted for changes to take effect.  [[/manager/search/control| Click here to restart from the Manager.]]','severity':'warn'}
    r = requests.post("https://localhost:8089/services/messages/new", headers=headers, data=data, verify=False)
    data = {'name':'restart_reason','value':'A user triggered the create action on app rtpHealthChecker, and the following objects required a restart.','severity':'warn'}
    r = requests.post("https://localhost:8089/services/messages/new", headers=headers, data=data, verify=False)
    pass

  def handleList(self, confInfo):
   confDict = self.readConf(self.CONF_FILE)
   if None != confDict:
    for stanza, settings in confDict.items():
     for key, val in settings.items():
      if val is None:
       confInfo[stanza].append(key, "")
      else:
       confInfo[stanza].append(key, val)

   def handleReload(self, confInfo):
    pass

admin.init(rtpHealthCheckerConf, admin.CONTEXT_NONE)
