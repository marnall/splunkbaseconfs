#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os.path
import sys
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
import commonlib
from pymongo import MongoClient,CursorType
from datetime import datetime
import ast,json

APPNAME = "goahead_mongofetch"
CREDUSER = 'mongofetch_user1'
CREDREALM = 'mongofetch_realm'

logger = commonlib.setup_logging("goahead_mongofetch")
WINDOW_SIZE = 10000

@Configuration(streaming=True, local=True)
class mongofetch(GeneratingCommand):
  database = Option(require=True,doc=''' target database name''')
  table = Option(require=True,doc=''' target table name ''')
  query = Option(require=True,doc=''' search query with pymongo schema {}''',default="{}")
  dbtimestamp = Option(require=False,doc=''' timestamp field name of the target table, which is necessary if the query use the timestamp field. ''')

  def adjust_query(self):
    query_json = ast.literal_eval(self.query)
    if isinstance(query_json,str):
      logger.error("[DB QueryError] Did you quote your whole query by using double-quote ? In addition, Inside quote letter must be a single-quote(') or an escaped double-quote(\") ! ")
      raise Exception("[DB QueryError] Did you quote your whole query by using double-quote ? In addition, Inside quote letter must be a single-quote(') or an escaped double-quote(\") !")
    if self.dbtimestamp:
      if "$and" in query_json.keys() or "$or" in query_json.keys():
        try:
          for complex_name in query_json:
            if complex_name=="$and" or complex_name=="$or":
              i = 0
              while i < len(query_json[complex_name]):
                if self.dbtimestamp in query_json[complex_name][i]:
                  for condition,value_epoc in query_json[complex_name][i][self.dbtimestamp].items():
                    if condition in ("$gt","$lt","$gte","$lte"):
                      epoch_time = None
                      epoch_time = value_epoc
                      query_json[complex_name][i][self.dbtimestamp][condition] = datetime.fromtimestamp(value_epoc)
                i+=1
        except Exception as e:
          logger.error(f"[{str(e)}]query: {query_json}")
      else:
        for key_name,value_epoc in query_json[self.dbtimestamp].items():
          if key_name in ("$gt","$lt","$gte","$lte"):
            epoch_time = None
            epoch_time = value_epoc
            query_json[self.dbtimestamp][key_name] = datetime.fromtimestamp(value_epoc)
    return query_json


  def fetch_mongo_records(self):
    records_json = []

    with MongoClient(self.target_mongo) as client:
      assert client is not None
      logger.debug(f" mongo client: {vars(client)}")      
      try:
        db = client[self.database]
        collection = db[self.table]
        try:
          query_json = self.adjust_query()
        except Exception as e:
          raise Exception(f"[{self.database}]({self.table}) {str(e)}")

        logger.info("set query into find():  %s "%query_json)
        counts = collection.estimated_document_count(query_json)
        logger.info(f"[{self.database}]({self.table}) ?{self.query} {counts}records")
        position = 0
        while position < counts:
          # ERROR: searchcommands/internals.py", line 640 : 'staticmethod' object is not callable. (pymongo cursor object)
          # [ records_json.append(record) for record in collection.find(query_json).sort([( '$natural', 1 )]).skip(position).limit(WINDOW_SIZE) ]
          for obj in collection.find(query_json).sort([( '$natural', 1 )]).skip(position).limit(WINDOW_SIZE):
            record = self.convert_obj2json(obj)
            records_json.append(record)
          
          logger.info("[%s] position in progress: %d, stored record counts = %d"%(datetime.now().strftime('%Y-%m-%dT%H-%M-%SZ'),position,len(records_json)))
          position += WINDOW_SIZE

      except Exception as e:
        logger.error(f"[{self.database}]({self.table}) {str(e)}")
        raise Exception(f"[{self.database}]({self.table}) {str(e)}")

    return records_json

  def convert_obj2json(self, iterObj):
    '''Convert pymongo bson objects to json format'''
    if type(iterObj).__name__ == 'dict':
      for k, v in iterObj.items():
        if type(v).__name__ == 'ObjectId':
            iterObj[k] = str(v)
        elif type(v).__name__ == 'list':
            self.toStr(v)
        elif type(v).__name__ == 'datetime':
            iterObj[k] = v.strftime('%Y-%m-%dT%H-%M-%SZ')
    return json.dumps(iterObj)


  def generate(self):
    #logger.info('mongofetch: %s', vars(self))
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
      records = self.fetch_mongo_records()
    except Exception as e:
      logger.error(f"[Mongofetch Error] by {str(e)}")
      raise Exception("[Mongofetch Error] {}".format(str(e)))     

    event["_raw"] = records
    yield event

dispatch(mongofetch, sys.argv, sys.stdin, sys.stdout, __name__) 

