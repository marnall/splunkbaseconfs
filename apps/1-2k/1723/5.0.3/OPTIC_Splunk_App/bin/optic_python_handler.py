import splunk.admin as admin
import splunk.entity as en
# import your required python modules
from cred_store import TSCredStoreManager
from settings import APP_NAME, APP_OWNER, get_app_home, get_conf_file, get_working_dir, get_mgmt_port, get_backfill_checkpoint
import os, shutil, sys, re
from summary.ts_bundle import SummaryConfig
from summary.optic_client2 import OpticClient
from logger import setup_logger
logger = setup_logger('optic_install')

'''
Copyright (C) 2005 - 2010 Splunk Inc. All Rights Reserved.
Description:  This skeleton python script handles the parameters in the configuration page.

      handleList method: lists configurable parameters in the configuration page
      corresponds to handleractions = list in restmap.conf

      handleEdit method: controls the parameters and saves the values
      corresponds to handleractions = edit in restmap.conf

'''

class ConfigApp(admin.MConfigHandler):
  CRED_STORE_NAME = "ts_optic_cred"
  TS_OPTIC_USERNAME_KEY = 'username'
  TS_OPTIC_APIKEY_KEY = 'apikey'
  TS_OPTIC_PROXY_HOST = 'proxy_host'
  TS_OPTIC_PROXY_PORT = 'proxy_port'
  TS_OPTIC_PROXY_USERNAME = 'proxy_username'
  TS_OPTIC_PROXY_PASSWORD = 'proxy_password'
  STANZA = 'setupentity'
  APP_OWNER = 'nobody'
  APP_NAME = 'OPTIC_Splunk_App'
  PROXY_NAME = 'ts_proxy_cred'

  '''
  Get an instance of TSCredStore (TS Credential Store)
  '''
  def get_credStore(self):
    return TSCredStoreManager(self.getSessionKey(), self.APP_NAME, self.APP_OWNER, "")

  '''
  Set up supported arguments
  '''
  def setup(self):
    if self.requestedAction == admin.ACTION_EDIT:
      for arg in [self.TS_OPTIC_USERNAME_KEY, self.TS_OPTIC_APIKEY_KEY, self.TS_OPTIC_PROXY_HOST, self.TS_OPTIC_PROXY_PORT, self.TS_OPTIC_PROXY_USERNAME, self.TS_OPTIC_PROXY_PASSWORD, 'exist_cust', 'signupUrl', "new_cust", "url", "user_firstname", "user_lastname", "user_email", "user_phone", "user_country", "user_password", "eula_ack", "proxy_enabled"]:
        self.supportedArgs.addOptArg(arg)

  def handleList(self, confInfo):
    confDict = self.readConf("ts_optic_setup")
    if None != confDict:
      for stanza, settings in confDict.items():
        for key, val in settings.items():
          confInfo[stanza].append(key, val)
      username, apikey = self.get_credStore().get_raw_creds(self.CRED_STORE_NAME)
      confInfo[self.STANZA].append(self.TS_OPTIC_USERNAME_KEY, username)
      confInfo[self.STANZA].append(self.TS_OPTIC_APIKEY_KEY, apikey)

      proxy_username, proxy_password = self.get_credStore().get_raw_creds(self.PROXY_NAME)
      confInfo[self.STANZA].append(self.TS_OPTIC_PROXY_USERNAME, proxy_username)
      confInfo[self.STANZA].append(self.TS_OPTIC_PROXY_PASSWORD, proxy_password)

  '''
  After user clicks Save on setup screen, take updated parameters,
  normalize them, and save them somewhere
  '''
  def handleEdit(self, confInfo):
    name = self.callerArgs.id
    data = self.callerArgs
    if not data:
        logger.warn("No data")
        return
    new_cust = data['new_cust'][0]
    if new_cust and new_cust in ['1', 1]:
        user_firstname = data['user_firstname'][0]
        user_lastname = data['user_lastname'][0]
        user_email = data['user_email'][0]
        if user_email and re.search(r'[\w.-]+@[\w.-]+.\w+', user_email):
            logger.info("valid email address")
        else:
            logger.warn("invalid email address")
        user_phone = data['user_phone'][0]
        user_country = data['user_country'][0]
        user_password = data['user_password'][0]
        root_url = data['url'][0]
        try:
            client = OpticClient(user_email, '', root_url)
            user = dict(email=user_email,name=user_firstname + " " + user_lastname,
                    organization=user_email,phone=user_phone,country=user_country if user_country else 'us',password=user_password)
            (ts_optic_username, ts_optic_apikey) = client.signUp(user, logger)
            logger.info("registered a new user")
        except Exception as e:
            logger.exception(e)
            logger.error("Failed to register user")
    else:
        ts_optic_username = data[self.TS_OPTIC_USERNAME_KEY][0]
        ts_optic_apikey = data[self.TS_OPTIC_APIKEY_KEY][0]
    proxy_user = data[self.TS_OPTIC_PROXY_USERNAME][0]
    proxy_passwd = data[self.TS_OPTIC_PROXY_PASSWORD][0]
    try:
      if ts_optic_username and ts_optic_apikey:
        self.get_credStore().save(self.CRED_STORE_NAME, ts_optic_username, ts_optic_apikey)
      if proxy_user and proxy_passwd:
        self.get_credStore().save(self.PROXY_NAME, proxy_user, proxy_passwd)
    except Exception as e:
      raise Exception('Failed to save OPTIC credentials')

    # Save the settings except the credentails
    for key in data:
      if data[key][0] is None:
        data[key][0] = ''
    data[self.TS_OPTIC_USERNAME_KEY] = ''
    data[self.TS_OPTIC_APIKEY_KEY] = ''
    data[self.TS_OPTIC_PROXY_USERNAME] = ''
    data[self.TS_OPTIC_PROXY_PASSWORD] = ''
    logger.info("clean up user profile")
    data['new_cust'] = ''
    data['exist_cust'] = ''
    data['user_firstname']=''
    data['user_lastname']=''
    data['user_email']=''
    data['user_phone']=''
    data['user_country']=''
    data['user_password'] = ''
    self.writeConf('ts_optic_setup', 'setupentity', data)
    
        # Create client.conf
    try:
        #add user to ts_optic_username to ts_client.conf
        default_client_conf_file = os.path.join(get_app_home(), 'default', 'ts_client.conf')
        default_config = SummaryConfig(default_client_conf_file, logger=logger)
        options = default_config.get_options('myclient')
        options['encrypt'] = True
        options['user'] = ts_optic_username
        src = os.path.join(get_app_home(), 'local', 'ts_client.conf')
        new_config = SummaryConfig(src, logger=logger)
        new_config.create('myclient', options)
        dest = get_conf_file()
        if not os.path.exists(get_working_dir()):
            os.mkdir(get_working_dir())
        logger.info("Copy %s to %s" % (src, dest))
        shutil.copyfile(src, dest)
    except Exception as e:
        logger.exception(e)

# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
