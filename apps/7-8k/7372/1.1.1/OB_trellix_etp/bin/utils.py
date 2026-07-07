import requests
from datetime import datetime, timedelta
import json
import os
import sys
import configparser
import os
import logging, logging.handlers

from dateutil import tz

import splunk

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import splunk.clilib.cli_common as cli_c
from splunk_aoblib.setup_util import Setup_Util
from solnlib import utils as solnlib_utils
from solnlib.server_info import ServerInfo
from solnlib import conf_manager
from solnlib import credentials

UTC = tz.gettz('UTC')
SECRET_REALM = 'etp_iam_realm'

GLOBAL_API_KEY_NAME = 'api_key'
GLOBAL_SERVICE_REGION_NAME = 'etp_service_region'
TA_NAME = 'OB_trellix_etp'
CONF_NAME = f'{TA_NAME.lower()}_settings'

def setup_logging():
  logger = logging.getLogger(f'splunk.{TA_NAME.lower()}')    
  SPLUNK_HOME = os.environ['SPLUNK_HOME']
  
  LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
  LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
  LOGGING_STANZA_NAME = 'python'
  LOGGING_FILE_NAME = f'{TA_NAME.lower()}.log'
  BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
  LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
  splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a') 
  splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
  logger.addHandler(splunk_log_handler)
  splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
  return logger


def get_secret(client, secret_realm, secret_name):
  secrets = client.service.storage_passwords

  try:
    return next(secret for secret in secrets if (secret.realm == secret_realm and secret.username == secret_name)).clear_password
  except StopIteration: 
    return None


def create_secret(client, secret_realm, secret_name, secret):
  storage_password = client.service.storage_passwords.create(secret, secret_name, secret_realm)
  logger.info( {'message': f"Created storage password with name: {storage_password.name}"} )
  
  
def update_secret(client, secret_realm, secret_name, secret):
  try:
    client.service.storage_passwords.delete(secret_name, realm=secret_realm)
  except Exception as e:
    logger.error(e)
  
  try: 
    storage_password = client.service.storage_passwords.create(secret, secret_name, realm=secret_realm)
  except Exception as e:
    logger.error(e)

  logger.info({ 'message': f"Update storage password with name: {storage_password.name}"})
  

def change_datetime_to_utc(input_datetime, default_hour):

  # if input_datetime is ISO format
  try:
    input_datetime_dt = datetime.fromisoformat(input_datetime)
  except Exception as e:
    # set default datetime
    input_datetime_dt = datetime.now() - timedelta(hours=default_hour)
  finally:
    input_datetime_ts = input_datetime_dt.timestamp()
    user_datetime_utc = datetime.fromtimestamp(input_datetime_ts, UTC)
  
  # if input_datetime is epoch format(float)
  # float
  try:
    user_datetime_utc = datetime.fromtimestamp(float(input_datetime), UTC)
  except:
    pass
  
  # if input_datetime is epoch format(int)
  try:
    user_datetime_utc = datetime.fromtimestamp(int(input_datetime), UTC)
  except:
    pass

  # convert ISO format
  # delete "+00:00" (2022-04-20T01:02:04.000+00:00)
  converted_datetime_iso = user_datetime_utc.isoformat(timespec='milliseconds')[:-6]

  return converted_datetime_iso


def get_user_timezone(splunk_client):

  tz_name = splunk_client.search_results_info.tz_name

  if tz_name == 'None':
    tz_name = 'UTC'
    
  return tz.gettz(tz_name)


def get_etp_instance():
  data = cli_c.getConfStanza('etpconf', 'instance')
  etp_instance = data.get("etp_instance")
  if etp_instance is None:
    etp_instance = "us.etp.trellix.com"
  
  return etp_instance


# def get_secret_global(client, var_name):
def get_secret_global(splunkd_uri, session_key, var_name):

  # uri = f"{client.service.scheme}://{client.service.host}:{client.service.port}"
  # session_key = client.service.token

  setup_util = Setup_Util(splunkd_uri, 
                          session_key, 
                          logger)

  var_value = setup_util.get_customized_setting(var_name)

  if var_value is None:
    raise Exception(f'Failed to get a global variable: {var_name}')
  else:
    return var_value


def get_clear_passwords(session_key, realm):
  # realm='__REST_CREDENTIAL__#OB_trellix_etp#configs/conf-ob_trellix_etp_settings'
  cm = credentials.CredentialManager(
    session_key,
    'OB_trellix_etp',
    realm=realm
    )
    
  p = cm.get_clear_passwords_in_realm()
  raw = json.loads(p[0].get('clear_password'))
  return raw


def get_requests_proxies(splunkd_uri, session_key):
  setup_util = Setup_Util(splunkd_uri, 
                        session_key, 
                        logger)

  proxy_settings = setup_util.get_proxy_settings()
  proxies = {}
  if proxy_settings:
    proxy_uri = get_proxy_uri(proxy_settings)
    proxies = {
      'http': proxy_uri,
      'https': proxy_uri,
    }
  
  return proxies


def get_proxy_uri(proxy):
  """
  :proxy: dict like, proxy information are in the following
          format {
              'proxy_url': zz,
              'proxy_port': aa,
              'proxy_username': bb,
              'proxy_password': cc,
              'proxy_type': http,sock4,sock5,
              'proxy_rdns': 0 or 1,
          }
  :return: proxy uri or None
  """
  # from solnlib import utils as solnlib_utils

  uri = None
  if proxy and proxy.get('proxy_url') and proxy.get('proxy_type'):
    uri = proxy['proxy_url']

    # socks5 causes the DNS resolution to happen on the client
    # socks5h causes the DNS resolution to happen on the proxy server
    if proxy.get('proxy_type') == 'socks5' and solnlib_utils.is_true(proxy.get('proxy_rdns')):
      proxy['proxy_type'] = 'socks5h'

    # setting default value of proxy_type to 'http' if
    # its value is not from ['http', 'socks4', 'socks5']
    if proxy.get('proxy_type') not in ['http', 'https', 'socks4', 'socks5']:
      proxy['proxy_type'] = 'http'

    if proxy.get('proxy_port'):
      uri = f"{uri}:{proxy.get('proxy_port')}"

    if proxy.get('proxy_username') and proxy.get('proxy_password'):
      uri = f"{proxy['proxy_type']}://{proxy['proxy_username']}:{proxy['proxy_password']}@{uri}/"
    else:
      uri = f"{proxy['proxy_type']}://{uri}"

  return uri


def check_within_timedelta(helper, current_time, state_dt, opt_time_lag_guard):
  time_difference = current_time - state_dt
  
  if time_difference <= timedelta(minutes=opt_time_lag_guard):
    helper.log_info( { 'current_time': f'{current_time}', 'state': f'{state_dt}', 
          'diff': f'{time_difference}', 'timelag': opt_time_lag_guard} )
    helper.log_info( { 'message': f"Retrieved up to {opt_time_lag_guard} minutes ago."} )
    return True

  return False


def is_enable_ssl_verify(instance_type, ssl_verify):

  ssl_verify = solnlib_utils.is_true(ssl_verify)
  if instance_type == 'cloud':
    ssl_verify = True
  
  return ssl_verify


def get_conf_data(session_key):
  realm = f'__REST_CREDENTIAL__#{TA_NAME}#configs/conf-{CONF_NAME}'

  cfm = conf_manager.ConfManager(session_key,
                                TA_NAME,
                                realm=realm)

  conf_file = cfm.get_conf(CONF_NAME)
  conf_data = conf_file.get_all()

  return conf_data


def get_server_info(session_key):
  # server_info.is_cloud_instance()
  return ServerInfo(session_key)


logger = setup_logging()