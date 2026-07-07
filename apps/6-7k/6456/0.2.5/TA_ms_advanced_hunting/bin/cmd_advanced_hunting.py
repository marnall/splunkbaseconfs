import json
import sys
from datetime import datetime

import import_declare_test  # noqa
import ms_advhunt_utils
import ta_ms_advanced_hunting_declare
from ms_client import MSClient
from splunklib.searchcommands import Configuration, GeneratingCommand, Option, dispatch
from splunktaucclib.rest_handler import util as rest_handler_util

APP_NAME = ta_ms_advanced_hunting_declare.APP_NAME
REST_REALM = ta_ms_advanced_hunting_declare.REST_REALM
TOKEN_REALM = ta_ms_advanced_hunting_declare.TOKEN_REALM

# annotation for splunk
@Configuration(type='events', generates_timeorder=True)
class MsAdvancedHuntingCommand(GeneratingCommand):

  query = Option(require=True)
  renew = Option(require=False)
  plan = Option(require=False)
  cred = Option(require=False)

  def prepare(self):

    # sometimes session expired error occurs.. 
    try:
      log_level = ms_advhunt_utils.get_settings_loglevel(self.logger, self.service.token)
    except Exception:
      log_level = 'INFO'

    ms_advhunt_utils.setup_logger(self.logger, log_level)

    # proxy settings
    proxy_dict = ms_advhunt_utils.get_settings_proxy(self.logger, self.service.token)
    proxy_enabled = proxy_dict.get("proxy_enabled", False)
    proxy_uri = rest_handler_util.get_proxy_uri(proxy_dict if proxy_enabled == '1' else {})
    proxies = {"http": proxy_uri, "https": proxy_uri}

    account_conf_file = ms_advhunt_utils.get_account_config()

    # restrict the passwords to fetch with REALM
    # strage_password mode
    # storage_passwords = self.service.storage_passwords.list(search=f"realm={REST_REALM}")

    # change storage_passwords to CredentialManager
    account_passwords = ms_advhunt_utils.get_secrets(self.logger, self.service.token, REST_REALM)
    tokens = ms_advhunt_utils.get_secrets(self.logger, self.service.token, TOKEN_REALM)

    credentials = []
    for key, value in account_conf_file.items():
      if key == 'default':
        continue

      # format 
      # {'name': '__REST_CREDENTIAL__#TA_ms_advanced_hunting#configs/conf-ta_ms_advanced_hunting_account:WindowsDefenderATP:', 'realm': '__REST_CREDENTIAL__#TA_ms_advanced_hunting#configs/conf-ta_ms_advanced_hunting_account', 'username': 'WindowsDefenderATP', 'clear_password': '{"password": "~~"}'}
      client_secret = [ account_password.get('clear_password') for account_password in account_passwords
                        if account_password.get('username') is not None and account_password.get('username') == key 
                      ]
      
      try: 
        client_secret = json.loads(client_secret[0]).get('password')
      except Exception:
        # something wrong
        self.logger.error({'message': 'No client secret'})
        continue
    
      # format 
      # {'name': 'ms_advhunt_token:WindowsDefenderATP:', 'realm': 'ms_advhunt_token', 'username': 'WindowsDefenderATP', 'clear_password': '~~~~'}
      access_token =  [ token.get('clear_password') for token in tokens
                        if token.get('username') is not None and token.get('username') == key 
                      ]
      try: 
        access_token = access_token[0]
      except Exception:
        # get new token
        access_token = None
      
      credential = {
        'cred_name': key,
        'tenant_id': value.get('tenant_id'),
        'client_id': value.get('username'),
        'default': value.get('default_credential'),
        'client_secret': client_secret,
        'access_token': access_token,
        'read_timeout': float(value.get('read_timeout', ta_ms_advanced_hunting_declare.READ_TIMEOUT)),
        'connection_timeout': float(value.get('connection_timeout', ta_ms_advanced_hunting_declare.CONNECTION_TIMEOUT)),
        'retry_num': int(value.get('retry_num', ta_ms_advanced_hunting_declare.RETRY_NUM)),
      }

      credentials.append(credential)
    
    # cred: pattern none, single, array, all
    # if cred option is not set, value is None
    # if cred option exsits but value is not set, value is ''

    self.credential_list = []
    if self.cred is None or len(self.cred) == 0:
      # get default credential from config file
      self.credential_list = [cred for cred in credentials if cred.get('default') is not None and cred.get('default') == '1']

    elif self.cred == "all":
      # use all credentials
      self.credential_list = credentials
    else:
      cred_names = [ c.strip() for c in self.cred.split(',') ]
      self.logger.debug({'message': f'cred_names::{cred_names}'})
      self.credential_list = [cred for cred in credentials if cred.get('cred_name') in cred_names]
    
    if len(self.credential_list) == 0:
      self.logger.error({'message': 'There is no credential'})
      sys.exit(1)

    # for MS Graph
    # earliest_time = datetime.fromtimestamp(self.metadata.searchinfo.earliest_time, timezone.utc).isoformat()
    # latest_time = datetime.fromtimestamp(self.metadata.searchinfo.latest_time, timezone.utc).isoformat()
    # self.timespan = earliest_time + '/' + latest_time

    self.app_options = {
      'force_token_renewal': True if self.renew == 'True' else False,
      'proxies': proxies
    }

  
  def generate(self):
    query = { 'Query' : self.query }
     
    # create MSClient for each credential
    ms_clients = []
    for credential in self.credential_list:
      self.app_options['credential'] = credential
      
      try:
        ms_client = MSClient(self.service, self.logger, self.app_options)

        ms_clients.append(ms_client)

        # update access token
        if ms_client.token_changed is True:
          # [credential:ms_app_token:WindowsDefenderATP_token:]
          # [credential:REALM:name:]
          ms_advhunt_utils.create_secret(self.logger, self.service.token, TOKEN_REALM, credential.get('cred_name'), ms_client.access_token) 

      except Exception as e:
        self.logger.error(e)

    # fetch data
    for ms_client in ms_clients:

      # for MS Graph
      # if ms_client.API_TYPE == 'ThreatHunting':
      #   query['Timespan'] = self.timespan

      data = ms_client.query_advanced_hunting(query)

      if data is None:
        raise Exception("No data")

      self.logger.info({'message': 'API Status', 'Data': data.get('Stats')})
      results = data.get("Results")
      if results is None:
        results = data.get("results")

      for d in results:
        record = {
          '_raw': d,
          'tenant_id': ms_client.tenant_id,
          'client_id': ms_client.client_id,
          'cred': ms_client.cred_name,
        }

        if d.get('Timestamp') is not None:
          record['_time'] =  format_datetime(d.get('Timestamp'))
        elif d.get('LastModifiedTime') is not None:
          record['_time'] =  format_datetime(d.get('LastModifiedTime'))
        elif d.get('LastSeenTime') is not None:
          record['_time'] =  format_datetime(d.get('LastSeenTime'))

        yield record

def format_datetime(input_datetime):
  """
  Timestamp patterns
  - 2022-08-12T10:58:38.1031214Z
  - 2022-08-12T01:28:22.202553Z
  - 2022-08-12T10:58:38.10Z
  - 2022-08-12T10:58:38Z
  """

  dt = input_datetime.split('.')[0]
  dt = dt.split('Z')[0]
  try:
    ms = input_datetime.split('.')[1]
    ms = ms.replace('Z', '')
    ms = ms.ljust(6, '0')[:6]
  except Exception:
    ms = ""

  dt = dt + "." + ms + '+00:00'
  dte =  datetime.fromisoformat( dt ).timestamp()
  return dte 

if __name__ == "__main__":
  dispatch(MsAdvancedHuntingCommand, sys.argv, sys.stdin, sys.stdout, __name__)
