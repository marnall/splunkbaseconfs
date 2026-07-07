import datetime
import os

import import_declare_test  # noqa
import jwt
import requests
import ta_ms_advanced_hunting_declare
from urllib3.util import Retry

TOKEN_REALM = ta_ms_advanced_hunting_declare.TOKEN_REALM

# When MS_MOCK_BASE_URL is set, all Microsoft API calls are redirected to the
# local mock server (see tests/mock_ms_server.py).
_MOCK_BASE = os.environ.get("MS_MOCK_BASE_URL", "").rstrip("/")
_AUTH_BASE = _MOCK_BASE or "https://login.microsoftonline.com"


def _endpoint(real_url: str) -> str:
    if not _MOCK_BASE:
        return real_url
    # Replace the scheme+host with the mock base, keep the path
    from urllib.parse import urlparse
    path = urlparse(real_url).path
    return f"{_MOCK_BASE}{path}"


class MSClient:

  API_SETTINGS = {
    'WindowsDefenderATP': {
      'resource': 'https://api.securitycenter.microsoft.com',
      'endpoint': _endpoint('https://api.securitycenter.microsoft.com/api/advancedqueries/run'),
      'ver': ''
    },
    'MicrosoftThreatProtection': {
      'scope': 'https://api.security.microsoft.com/.default',
      'endpoint': _endpoint('https://api.security.microsoft.com/api/advancedhunting/run'),
      'ver': '/v2.0'
    },
    'ThreatHunting': {
      'scope': 'https://graph.microsoft.com/.default',
      'endpoint': _endpoint('https://graph.microsoft.com/v1.0/security/runHuntingQuery'),
      'ver': '/v2.0'
    },

  }

  ELAPSED_TIME = 60

  def __init__(self, splunk_service, logger, options):
    
    # cred = ms_advhunt_utils.get_secret(splunk_service, SECRET_REALM, options.get('cred_name'))
    # if cred is None:
    #   logger.error(f"Credential name: {options.get('cred_name')}. No such credentail.")
    #   sys.exit(1)
    self.logger = logger
    self.credential = options.get('credential')

    self.client_id = self.credential.get('client_id')
    self.client_secret = self.credential.get('client_secret')
    self.tenant_id = self.credential.get('tenant_id')
    self.cred_name = self.credential.get('cred_name')
    
    self.splunk_service = splunk_service
    self.force_token_renewal = options.get('force_token_renewal')
    self.proxies = options.get('proxies')
    self.session = requests.Session()
    retries = Retry(
      total = options.get('retry_num'),
      backoff_factor=1,
      status_forcelist=[502, 503, 504],
      allowed_methods=Retry.DEFAULT_ALLOWED_METHODS.union({"POST"}),
    )
    self.session.mount('https://', requests.adapters.HTTPAdapter(max_retries=retries))
    self.session.mount('http://', requests.adapters.HTTPAdapter(max_retries=retries)) # for mock usage
    self.timeout=(self.credential.get('connection_timeout'), self.credential.get('read_timeout'))
                
    self.API_TYPE = ""

    self.token_changed = False
    self.access_token = self.credential.get('access_token')
    self.__set_access_token()
    self.__set_api_type(self.access_token)
  
    
  def __check_access_token_expired(self, access_token):
    try:
      claims = jwt.decode(access_token, options={"verify_signature": False})
    except Exception as e:
      self.logger.error(e)
      return False  

    exp = datetime.datetime.fromtimestamp(claims.get('exp'))
    now = datetime.datetime.now()
    return now + datetime.timedelta(seconds=self.ELAPSED_TIME) > exp

  def __check_client_id_is_same(self, access_token):
    try:
      claims = jwt.decode(access_token, options={"verify_signature": False})
    except Exception as e:
      self.logger.error(e)
      return False

    return self.client_id == claims.get('appid')

  def __set_api_type(self, access_token):
    try:
      claims = jwt.decode(access_token, options={"verify_signature": False})
    except Exception as e:
      raise(e)

    for k,v in self.API_SETTINGS.items():
      aud = v.get('resource') if v.get('resource') is not None else v.get('scope')
      if claims.get('aud') in aud:
        self.API_TYPE = k

    self.logger.info({'message': f'{self.API_TYPE} permissions found.'})
  
  def __get_api_roles(self, access_token):
    try:
      claims = jwt.decode(access_token, options={"verify_signature": False})
    except Exception as e:
      raise(e)
    
    return claims.get('roles', None)


  def __get_new_token(self):
    
    for _k,v in self.API_SETTINGS.items():
      url = f"{_AUTH_BASE}/{self.tenant_id}/oauth2{v.get('ver')}/token"
      body = {
          'client_id' : self.client_id,
          'client_secret' : self.client_secret,
          'grant_type' : 'client_credentials'
      }

      if v.get('resource', None) is not None:
        body['resource'] = v.get('resource')

      if v.get('scope', None) is not None:
        body['scope'] = v.get('scope')

      r = self.session.post(url, data=body, proxies=self.proxies)
      response_json = r.json()

      if response_json.get("access_token") is not None and \
        self.__get_api_roles(response_json.get("access_token")):
        return response_json.get("access_token")
      
      self.logger.debug({'message': f'get_new_token::{self.client_id}'})
    
    return False


  def __set_access_token(self):

    flag_renewal = False
    
    if self.force_token_renewal is True:
      flag_renewal = True

    elif self.access_token is None:
      flag_renewal = True

    elif self.__check_access_token_expired(self.access_token) is True:
      flag_renewal = True

    elif self.__check_client_id_is_same(self.access_token) is not True:
      flag_renewal = True

    # reset access_token

    if flag_renewal is True:

      self.access_token = self.__get_new_token()

      if self.access_token is False or self.access_token is None:
        raise Exception('Failed to get a new access token')

      self.token_changed = True
 

  def execute_rest(self, method='post', r_format='json', endpoint='', body=None):
    if body is None:
      body = {}

    headers={
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'Authorization': f"Bearer {self.access_token}",
    } 
    
    try:
      if method == 'post':
        r = self.session.post(endpoint, headers=headers, json=body, timeout=self.timeout, proxies=self.proxies)
      else:
        r = self.session.get(endpoint, headers=headers, timeout=self.timeout, proxies=self.proxies)

    except Exception as e:
      self.logger.error(e)
      raise

    self.logger.info({'API_Status_Code': r.status_code, 'endpoint': endpoint})

    if r.status_code == 429:
      message = "You've reached a quota, either by number of requests sent, or by allotted running time"
      self.logger.error({'message': message})
      raise Exception(message)

    if r.status_code < 200 or r.status_code >= 300:
      try:
        message = r.json().get('error').get('message')
        raise Exception(message)
      except Exception as e:
        self.logger.error({'message': r.content})
        raise Exception(e) from e

    if r_format == 'json':
      return r.json()
    elif r_format == 'text':
      return r.text()
    else:
      return r

  def query_advanced_hunting(self, query):

    endpoint = self.API_SETTINGS.get(self.API_TYPE).get('endpoint')
    try:
      data = self.execute_rest(
                  method='post', 
                  r_format='json', 
                  endpoint=endpoint, 
                  body=query)
    except Exception as e:
      self.logger.error(e)
      raise

    return data
