#!/usr/bin/env python
# coding=utf-8


import os, sys, csv
from collections import OrderedDict
import requests as req
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators, ReportingCommand


import logging
import logging.handlers

REST_PATH=os.path.abspath(os.path.join(os.getcwd(), '../lookups', 'rest.csv'))
#RESTENDPOINT="http://localhost:5555"
try:
    with open(REST_PATH, 'r') as f:
        reader = csv.reader(f)
        for i, l in enumerate(reader):
            if i==1:
                RESTENDPOINT = l[0]
except:
    print("Please ensure you have defined the REST Endpoint before proceeding with Embedding/Query")
        

def setup_logger(level):
    logger = logging.getLogger('clms')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)

    file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/clms_llm.log', maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger

logger = setup_logger(logging.INFO)
csvFilePath = os.environ['SPLUNK_HOME'] + '/etc/apps/clms/csvfiles/temp.csv'
textFilePath = os.environ['SPLUNK_HOME'] + '/etc/apps/clms/csvfiles/text.csv'

logger.info("The rest PATH is: " + REST_PATH)
logger.info("The rest endpoint is " + RESTENDPOINT)

@Configuration()
class embed(ReportingCommand):
    
    collectionName = Option(require=True)
     
    @Configuration()
        
    def map(self, records):
        return records
    
    def reduce(self, records):
        count = 0
        rowcount = 0
        for record in records:
            # logger.info(record)
            if count == 0:
                with open(csvFilePath, "w") as outfile:
                    csvwriter = csv.writer(outfile)
                    csvwriter.writerow(dict(record).values())
                    count+=1
            if count != 0:
                with open(csvFilePath, "a") as outfile:
                    csvwriter = csv.writer(outfile)
                    csvwriter.writerow(dict(record).values())
                    count +=1
                # logger.info(count)
  
        for row in open(csvFilePath):
            rowcount+=1
        logger.info("Number of rows in CSV is " + str(rowcount))

        with open(csvFilePath, 'r') as f_in, open(textFilePath, 'w') as f_out:
            # 2. Read the CSV file and store in variable
            content = f_in.read()
            # 3. Write the content into the TXT file
            f_out.write(content)   

        logger.info('This is in reduce function: ' + self.collectionName)     
        
        f=open(textFilePath, 'r')
        logger.info('BEFORE')
        payload = {"collectionName": self.collectionName, "textToEmbed": f.read()}
        payload_json=json.dumps(payload, indent=2)
        logger.info(type(payload_json))
        logger.info(payload_json)
        r1 = req.post(RESTENDPOINT + '/splunkSearch', json=payload_json)
        logger.info(r1.status_code)
        return()

dispatch(embed, sys.argv, sys.stdin, sys.stdout, __name__)


