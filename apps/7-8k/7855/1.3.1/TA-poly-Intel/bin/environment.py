import sys,os
import os.path
import requests.compat as rco
import splunklib.client as splunkclient # pylint: disable=import-error

class psEnv:
    '''Class for Polyl Environment.'''
    _api_key = None
    _client = None
    _service = None

    def __init__(self, session_key) -> None:
        self._service = splunkclient.connect(token=session_key,app="TA-poly-Intel")
        self._service.namespace['owner'] = 'Nobody'
        self._session_key = session_key



    @property
    def api_key(self):
        api_key = "invalid"
        try:
            secrets = self._service.storage_passwords
            i=0
            for secret in secrets.list():
                i+=1
                relamname = secret.name
                if relamname.startswith('PolySwarm'):
                    api_key=secret.clear_password
                    break
            return api_key
        except Exception as erorr:
            api_key="invalid"
            return api_key


    @property
    def client(self):
        if not self._client:
            community_name = "default"
            #self._psapi = PolyswarmAPI(key=self._api_key,community=community_name)
            return self._client
        return self._client

    @property
    def service(self):
        return self._service
    
class SplunkEnv:
  '''Class for Splunk Environment.'''
  _service = None

  def __init__(self, session_key) -> None:
    self._service = splunkclient.connect(token=session_key)
    self._service.namespace['owner'] = 'Nobody'
    self._session_key = session_key

  @property
  def service(self):
      return self._service
