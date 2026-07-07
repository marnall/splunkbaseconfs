#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Splunk specific dependencies
import sys, os
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators, splunklib_logger as logger

# Command specific dependencies
import requests
import json


@Configuration(type='reporting')
class dbdata(GeneratingCommand):
  # Authorization : Bearer cn389ncoiwuencr
  url        = Option(require=True, validate=validators.Match('https url', '^https:\/\/'))
  paramMap   = Option(require=False)
  output     = Option(require=False, default='json')
  timeout    = Option(require=False, default=10, validate=validators.Integer())
  headers    = Option(require=False)
  method     = Option(require=False, default='get')
  ref        = Option(require=False)  
  data       = Option(require=False)
  realm      = Option(require=False)
  useAppCre  = Option(require=False, default=True, validate= validators.Boolean())
  

  def generate(self):
    url        = self.url
    paramMap   = self.parseParamMap(self.paramMap) if self.paramMap != None else None
    output     = self.output
    timeout    = self.timeout if self.timeout != None else None
    headers    = self.parseHeaders(self.headers) if self.headers != None else None
    method = self.method if self.method != None else None
    data = self.data if self.data != None else None
    ref = self.ref if self.ref != None else None 
    realm = self.realm if self.realm != None else None
    useAppCre = self.useAppCre if self.useAppCre != None else None

    storage_passwords=self.service.storage_passwords

    if useAppCre :
     for credential in storage_passwords:
        if realm != None: 
          if credential.content.get('realm') == realm :
            usercreds = {'username':credential.content.get('username'),'password':credential.content.get('clear_password')}
            json_string = json.dumps(headers).replace('username',usercreds['username'])
            headers = json.loads(json_string.replace('password',usercreds['password']))        
                
    #self._logger.error( "header used '%s'", headers)
    # Load data from REST API
    record = {}   
    try:

     if method == 'get': 
      request = requests.get(
        url,
        params=paramMap,
        auth=None,
        headers=headers,
        timeout=timeout
      )
     else:
        request = requests.post(
         url,
         data=data,
         auth=None,
         headers=headers,
         timeout=timeout
        )
      # Choose right output format
     if output == 'json':
        record = request.json()
        if ref != None:
         record["ref"] = ref
     else:
       if ref != None:
         resp = request.text + ","+ref
       else :
         resp = request.text
       record = {'reponse': resp}

     
     

    except requests.exceptions.RequestException as err:
      record = ({"Error:": err})
    
    yield record

  ''' HELPERS '''
  '''
    Parse paramMap into python dict
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
    Convert headers string into dict
    @headers string: Headers as json string
    @return dict
  '''
  def parseHeaders(self, headers):
    # Replace single quotes with double quotes for valid json
    return json.loads(
      headers.replace('\'', '"')
    )

dispatch(dbdata, sys.argv, sys.stdin, sys.stdout, __name__)