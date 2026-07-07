#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os.path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
import galib

APPNAME = "goahead_hatching_triage_utils"
CREDUSER = 'triageapp_user1'
CREDREALM = 'triage_realm'
COMMANDNAME = 'triageurlsubmit'

logger = galib.setup_logging(APPNAME)

@Configuration()
class triageurlsubmit(GeneratingCommand):
  instance = Option(doc=''' triage sandbox instance whether "public" or "private" or "recordedfuture" ''',require=True,validate=validators.Set('public','private','recordedfuture'))
  kind = Option(doc='''  "import", "fetch", "url" ''',require=True,validate=validators.Set('import','fetch','url'))   
  url = Option(doc=''' url target''',require=True)   
  profile_name = Option(doc=''' sandbox environment profile name''',require=False)   

  def generate(self):
    try:
      #logger.debug('triageurlsubmit: %s', vars(self))
      try:
        sessionkey = self.metadata.searchinfo.session_key
        if sessionkey is None:
          raise Exception("[Session Error] Did not receive a session key from splunkd.")
        apikey = galib.get_credentials(sessionkey,APPNAME,CREDUSER,CREDREALM)
      except Exception as e:
        raise Exception("[Credential Error] Could not retrieve credential from Splunk Entity via the API server by '{}'".format(str(e)))

      if self.instance == "public":
        baseUrl = "https://api.tria.ge/v0/"
      elif self.instance == "private":
        baseUrl = "https://private.tria.ge/api/v0/"   
      elif self.instance == "recordedfuture":
        baseUrl = "https://sandbox.recordedfuture.com/api/v0/" 
      else:
        raise Exception("[Option Error] Please specify 'public' or 'private' or 'recordedfuture' in order to choose which Hatching Triage sandbox instance to access.")
        return 0

      if not self.profile_name: 
        profiles = None
      else:
        profiles = [ {"profile": self.profile_name} ]

      # run query 
      try:
        from triagelib import urlsubmit
        jsonResponse = urlsubmit(baseUrl,apikey,self.kind,self.url,profiles,logger)
      except Exception as e:
        raise Exception("[API Error] Could not retrieve a valid json results by '{}'".format(str(e)))
        return 0

      # return the results to splunk output
      yield jsonResponse

    except Exception as e:
      logger.exception("Unexpected Error: {}".format(str(e)))
      raise Exception("[Unexpected Error]: Please see the error detail in app log or search log. '{}'".format(str(e)))
      return 1
      
dispatch(triageurlsubmit, sys.argv, sys.stdin, sys.stdout, __name__)
