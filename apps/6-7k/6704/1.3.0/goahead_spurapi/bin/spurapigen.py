#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os.path
import sys
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
import commonlib

APPNAME = "goahead_spurapi"
CREDUSER = 'spur_api_user1'
CREDREALM = 'spur_api_realm'

@Configuration()
class spurapigen(GeneratingCommand):
  ip = Option(require=True,doc=''' ipv4 or ipv6 string is valid for Spur context API (v2) ''')

  def generate(self):
    #self.logger.info('spurapigen: %s', vars(self))
    try:
      sessionkey = self.metadata.searchinfo.session_key
      if sessionkey is None:
        raise Exception("[Session Error] Did not receive a session key from splunkd.")

      apitoken = commonlib.get_credentials(sessionkey,APPNAME,CREDUSER,CREDREALM)
    except Exception as e:
      self.logger.exception("spurapigen raised Exception")
      raise Exception("[Credential Error] Could not retrieve credential from Splunk Secret Storage by {}".format(str(e)))

    response_json = commonlib.request_spurapi(self.logger,self.ip,apitoken)
    event = {}
    for key,value in response_json.items():
        event["Spur_%s"%key] = value 
    event["_time"] = time.time()
    
    yield event 

dispatch(spurapigen, sys.argv, sys.stdin, sys.stdout, __name__) 

