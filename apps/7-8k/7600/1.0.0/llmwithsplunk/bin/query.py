#!/usr/bin/env python
# coding=utf-8


import os, sys, csv, json, time
from collections import OrderedDict
import requests as req
import splunk.Intersplunk
import logging
import logging.handlers

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators, ReportingCommand, GeneratingCommand

REST_PATH=os.path.abspath(os.path.join(os.getcwd(), '../lookups', 'rest.csv'))
#RESTENDPOINT="http://localhost:5555"
with open(REST_PATH, 'r') as f:
  reader = csv.reader(f)
  for i, l in enumerate(reader):
    if i==1:
      RESTENDPOINT = l[0]

def setup_logger(level):
    logger = logging.getLogger('query')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)

    file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/clms_llm_query.log', maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger

logger = setup_logger(logging.INFO)
csvFilePath = os.environ['SPLUNK_HOME'] + '/etc/apps/clms/csvfiles/llm_query.csv'

logger.info("Hello this is the first sentence")

@Configuration(type="reporting")
class query(GeneratingCommand):
    
    search = Option(require=True)
    collectionName = Option(require=True)
    model= Option(require=True)

    # @Configuration()

    # def map(self, records):
    #     return records
    
    # def reduce(self, records):
    #     logger.info("Hello this is the second sentence")
    #     payload = {"query": self.search, "collectionName": self.collectionName}
    #     payload_json=json.dumps(payload)
    #     r2 = req.post('http://localhost:5555/userQuery', json=payload_json)
    #     r2_json = r2.json()
    #     llm_answer = r2_json["Output"]["answer"]
    #     # logger.info(type(llm_answer))
    #     # logger.info(r2_json["Output"]["answer"])
    #     #logger.info(r2_json["answer"])
    #     #logger.info()
    #     llm_answer=[{'Name': 'LLM Results', 'Output': str(llm_answer)}]
    #     # logger.info(llm_answer)
    #     # logger.info(type(llm_answer))
    #     return()
    
    def generate(self):
        payload = {"query": self.search, "collectionName": self.collectionName, "model": self.model}
        payload_json=json.dumps(payload)
        r2 = req.post(RESTENDPOINT + '/userQuery', json=payload_json)
        r2_json = r2.json()
        llm_answer = r2_json["Output"]
        #model_used = r2_json["Output"]["model"]
        llm_answer=[{'Name': 'RAG Results', 'Output': llm_answer}]
        for outputlist in llm_answer:
            logger.info(outputlist["Name"])
            logger.info(outputlist["Output"])
            #logger.info(outputlist["Model"])
            yield {'_time': time.time(),'Name' : outputlist["Name"], 'Output' : outputlist["Output"]}




dispatch(query, sys.argv, sys.stdin, sys.stdout, __name__)

