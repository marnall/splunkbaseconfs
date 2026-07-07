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
class mongolist(GeneratingCommand):
  show_count = Option(require=False,doc=''' add record count for each database and table which the user can read ''',default="false",validate=validators.Boolean())

  def list_dbs(self):
    result = {}

    with MongoClient(self.target_mongo) as client:
      assert client is not None
      logger.debug(f" mongo client: {vars(client)}")
      for database in client.list_databases():
        database_name = database.get("name")        
        result[database_name] = None
        try:
          for table_name in client[database_name].list_collection_names():
            try:
              if self.show_count:
                result[database_name] = { table_name: None }
                db = client[database_name]
                collection = db[table_name]
                try:
                  counts = collection.estimated_document_count({})
                except Exception as e:
                  if "not authorized" in str(e):
                    counts = "unauthorized"
                  else:
                    counts = None
                result[database_name][table_name] = counts
              else:
                if result[database_name] is not None:
                  result[database_name].append(table_name)
                else:
                  result[database_name] = [table_name]
            except Exception as e:
              logger.error(f"[MongoDB Process Error] Could not fetch the data by {str(e)} from [{database_name}]({table_name})")
        except Exception as e:
          logger.error(f"[MongoDB Process Error] by {str(e)}")
          raise Exception("[MongoDB Process Error] Could not fetch the data from DB:{} by {}".format(database_name,str(e)))          

      return result


  def generate(self):
    #logger.info('mongolist: %s', vars(self))
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
      records = self.list_dbs()
      event["_raw"] = records 

    except Exception as e:
      logger.error(f"[Mongolist Error] by {str(e)}")
      raise Exception("[Mongolist Error] {}".format(str(e)))           
    
    yield event 

dispatch(mongolist, sys.argv, sys.stdin, sys.stdout, __name__) 

