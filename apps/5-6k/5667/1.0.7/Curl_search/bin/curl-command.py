#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Splunk specific dependencies
# Splunk cloud version

import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib")) # Much cleaner than put splunklib in bin
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators, splunklib_logger as logger

# Command specific dependencies
import requests
from requests.auth import HTTPDigestAuth
import json

@Configuration(type='reporting')
class curlCommand(GeneratingCommand):
  url        = Option(require=True)
  paramMap   = Option(require=False)
  output     = Option(require=False, default='json')
  timeout    = Option(require=False, default=10, validate=validators.Integer())
  auth       = Option(require=False)
  headers    = Option(require=False)
  proxies    = Option(require=False)
  unsetProxy = Option(require=False, validate=validators.Boolean())
  # For splunk cloud vetting, allow only secure connections
  #verify     = Option(require=False, default="False") # Does not support verify = True for now, because we have to specify cert path and im not aware about how to deal with certs path in splunk apps. HINT : Put them ../static ? or os path ( problem with rights ? )
  method     = Option(require=False, default="get") 
  
  def generate(self):
    # For splunk cloud vetting, allow only https
    url = self.url
    if url.startswith("https://"):
      url        = self.url
    else:
      record = ({"Error:": "Url must start with HTTPS, HTTP is not supported in splunk cloud. If you are running this app on splunk enterprise, please downgrade to 1.0.5"})
      yield record

    paramMap   = self.parse_to_json(self.paramMap) if self.paramMap != None else None
    output     = self.output
    timeout    = self.timeout if self.timeout != None else None
    auth       = self.parseAuth(self.auth) if self.auth != None else None
    headers    = self.parse_to_json(self.headers) if self.headers != None else None
    proxies    = self.parseProxies(self.proxies) if self.proxies != None else None
    unsetProxy = self.unsetProxy
    method     = str.lower(self.method)
    verify = True
    #Splunk cloud does not allow insecure connection
    #if self.verify == "True" or self.verify == "true":
    #  verify = True
    #if self.verify == "False" or self.verify == "false":
    #  verify = False
    
    # Unset proxy, if unsetProxy = True
    if unsetProxy == True:
      if 'HTTP' in list(os.environ.keys()):
        del os.environ['HTTP']
      if 'HTTPS' in list(os.environ.keys()):
        del os.environ['HTTPS']

    # Load data from REST API
    record = {}    
    try:
      if method=="post":
        request = requests.post(
        url,
        params=paramMap,
        auth=auth,
        headers=headers,
        timeout=timeout,
        proxies=proxies,
        verify=verify
        )
      elif method=="get":
        request = requests.get(
        url,
        params=paramMap,
        auth=auth,
        headers=headers,
        timeout=timeout,
        proxies=proxies,
        verify=verify
        )
      # Choose right output format
      if output == 'json':
        record = request.json()

        if isinstance(record,list):
          for item in record:
            # Some api might returns [{a,b},{c,d}], then we return a single json response per list index
            yield {"reponse": item}
          return
      else:
        record = {'reponse': request.content}

    except requests.exceptions.RequestException as err:
      record = ({"Error:": err})
    
    yield record

  ''' HELPERS '''
  '''
    Old parse param map
    @paramMap string: Pattern 'foo=bar&hello=world, ...'
    @return dict
  '''
  def parseParamMap(self, paramMap):
    paramStr = ''

    # Check, if params contain \, or \= and replace it with placeholder
    paramMap = paramMap.replace(r'\,', '&#44;')
    paramMap = paramMap.split(',')

    for param in paramMap:
      paramStr += param.replace('&#44;', ',').strip() + '&'

    # Delete last &
    return paramStr[:-1]

  '''
    Parse proxy into python dict
    @proxy string: Comma separated proxies -> http,https
    @return dict
  '''
  def parseProxies(self, proxies):
    proxies = proxies.split(',')

    return {
      'http': proxies[0].strip(),
      'https' : proxies[1].strip()
    }

  '''
    Parse auth into python dict with correct method
    @proxy string: Comma separated auth params -> method,user,pass
    @return object/bool
  '''
  def parseAuth(self, auth):
    # Password could use commas, so just split 2 times
    auth = auth.rsplit(',', 2)

    # Use correcht auth method
    if auth[0].lower() == 'basic':
      return (auth[1].strip(), auth[2].strip())
    elif auth[0].lower() == 'digest':
      return HTTPDigestAuth(auth[0].strip(), auth[1].strip())

    # Return false in case of no valid method
    return False
    
  '''
    Convert string into dict
    @headers string: Parameters as json string
    @return dict
  '''
  def parse_to_json(self, string):
    return json.loads(string.replace('\'', '"'))

dispatch(curlCommand, sys.argv, sys.stdin, sys.stdout, __name__)
