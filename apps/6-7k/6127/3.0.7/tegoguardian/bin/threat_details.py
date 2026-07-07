#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Splunk specific dependencies
import sys, os, re
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators, splunklib_logger as logger

# Command specific dependencies
import requests
from requests.auth import HTTPDigestAuth
import json

@Configuration(type='reporting')
class curlCommand(GeneratingCommand):
  token        = Option(require=True)
  paramMap   = Option(require=False)
  output     = Option(require=False, default='json')
  timeout    = Option(require=False, default=10, validate=validators.Integer())
  
  def generate(self):
    token        = self.token
    paramMap   = self.parseParamMap(self.paramMap) if self.paramMap != None else None
    output     = self.output
    timeout    = self.timeout if self.timeout != None else None
 
    record = {} 

    #hard code url
    tego_url = "https://ti.tegocyber.com/api/Main/getdetails/"
    url = tego_url + token

    try:
      response = requests.get(
        url,
        params=paramMap,
        timeout=timeout
      )

      # Choose right output format
      if output == 'json':
        if response.text != "" and response.text != "[]":
            response.raise_for_status()
            jsobj = response.json()
            jsobj = jsobj[0]
            if jsobj["ip"]:
                record["ip"] = jsobj["ip"]
            elif jsobj["url"]:
                record["url"] = jsobj["url"]
            elif jsobj["hash"]:
                record["hash"] = jsobj["hash"]
            elif jsobj["domain"]:
                record["domain"] = jsobj["domain"]
            record["riskLevel"] = jsobj["riskLevel"]
            record["isp"] = jsobj["isp"]
            record["region"] = jsobj["region"]
            record["city"] = jsobj["city"]
            record["country"] = jsobj["country"]
        else:
          record = {'response': 'No details for this threat'}
      else:
        record = {'reponse': response.content}

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

  
dispatch(curlCommand, sys.argv, sys.stdin, sys.stdout, __name__)