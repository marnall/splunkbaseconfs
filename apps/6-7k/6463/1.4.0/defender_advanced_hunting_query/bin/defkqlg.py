#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os,sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
import galib
from defapi import get_aadToken

APPNAME = "defender_advanced_hunting_query"
COMMANDNAME = 'defkqlg'
CREDUSER = 'defenderapp_user1'
CREDREALM = 'defender_realm'
logger = galib.setup_logging(APPNAME)

@Configuration()
class defkqlg(GeneratingCommand):
  api = Option(doc=''' API kinds whether "queries" or "hunting" ''',require=True,validate=validators.Set('queries','hunting'))
  kql = Option(doc=''' KQL query to run ''',require=True)   

  def generate(self):
    try:
      try:
        sessionkey = self.metadata.searchinfo.session_key
        if sessionkey is None:
          raise Exception("[Session Error] Did not receive a session key from splunkd.")

        cred_strings = galib.get_credentials(sessionkey,APPNAME,CREDUSER,CREDREALM)
      except Exception as e:
        raise Exception(f"[Credential Error] Could not retrieve credential from Secret Storage by {str(e)}")

      tenantId = cred_strings.split("&")[0]
      appId = cred_strings.split("&")[1]
      appSecret = cred_strings.split("&")[2]

      if self.api == "queries":
        from defapi import advancedqueries_run as run_query
      elif self.api == "hunting":
        from defapi import advancedhunting_run as run_query
      else:
        raise Exception("[Option Error] Please specify 'queries' or 'hunting' to api= option for selecting which Advanced Hunting API.")
        return 0

      # get aadToken 
      try:
        aadToken = get_aadToken(tenantId,appId,appSecret,self.api)
      except Exception as e:
        raise Exception(f"[Token Error] Could not retrieve aadToken from the Azure AD creds by {str(e)}")
        return 0

      # run kql query 
      final_kql = self.kql.replace('"',"'")
      logger.warning(f"final_kql: {final_kql}")
      try:
        results = run_query(aadToken,final_kql)
      except Exception as e:
        raise Exception(f"[DefenderAPIQuery Error] Could not retrieve a valid kql results by {str(e)}")
        return 0

      logger.info(f"defender result count: {len(results)}")
      
      # return the results to splunk output
      if isinstance(results,list):
        for row in results:
          yield row 
      elif isinstance(results,dict):
        yield results
      else:
        yield { "Defender_app_error": f"Unexpected result format type of {type(results)}"}

    except Exception as e:
      logger.exception(f"Unexpected Error: {str(e)}")
      raise Exception(f"[Unexpected Error]: Please see the error detail in app log or search log. {str(e)}")
      return 1
      
dispatch(defkqlg, sys.argv, sys.stdin, sys.stdout, __name__)
