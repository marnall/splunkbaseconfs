#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os.path
import sys
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
import commonlib
from pymongo import MongoClient

APPNAME = "goahead_mongofetch"
CREDUSER = 'mongofetch_user1'
CREDREALM = 'mongofetch_realm'

logger = commonlib.setup_logging("goahead_mongofetch")

@Configuration(streaming=True, local=True)
class mongocheck(GeneratingCommand):

  def generate(self):
    #logger.info('mongocheck: %s', vars(self))
    try:
      sessionkey = self.metadata.searchinfo.session_key
      if sessionkey is None:
        raise Exception("[Session Error] Did not receive a session key from splunkd.")
      self.target_mongo = commonlib.get_credentials(sessionkey,APPNAME,CREDUSER,CREDREALM)
    except Exception as e:
      logger.error(f"[Credential Error] by {str(e)}")
      raise Exception("[Credential Error] Could not retrieve credential from Splunk Secret Storage by {}".format(str(e)))

    try:
      event = { "_raw":{}, "_time":time.time() }
      with MongoClient(self.target_mongo) as client:
        logger.debug(f" mongo client: {vars(client)}")
        event["_raw"]["client"] = str(client)        
        try:
          server_info = client.server_info()
          logger.debug(f" server_info: {server_info}")
          event["_raw"]["server_info"] = server_info
          if server_info["ok"] == 1:
            event["_raw"]["connection_status"] = "success"
          else:
            event["_raw"]["connection_status"] = "unexpected. please check the connection string again."
        except Exception as e:
          event["_raw"]["server_info"] = {}
          event["_raw"]["connection_status"] = f"fail by {str(e)} please check the connection string again whether the user credential is enough to access the authsource database."
          logger.error(f"mongocheck connect error: fail by {str(e)}")
    except Exception as e:
      logger.error(f"[MongoDB Connection Error] by {str(e)}")
      raise Exception("[MongoDB Connection Error] Could not build a connection to the mongodb by {}".format(str(e)))            
    
    yield event 

dispatch(mongocheck, sys.argv, sys.stdin, sys.stdout, __name__) 

