### Copyright 2017 RTP Technology Inc. - Full details found here: $SPLUNK_HOME/etc/apps/Splunk_TA_RTP-Health-Checker/defaut/LICENSE.txt

import ConfigParser
import csv
import json
import os
import re
import requests
import splunk.mining.dcutils as dcu
import sys
import tarfile
import time
import urllib
from xml.dom import minidom

appBinDir = sys.path[0]
confPath = os.path.join(appBinDir,'..','local','rtpHealthChecker.conf')
inputsConfPath = os.path.join(appBinDir,'..','local','inputs.conf')
logger = dcu.getLogger()
lookupsPath = os.path.join(appBinDir,'..','lookups')
searches_capacity=("Capacity - Compression Ratio","Capacity - CPU and Memory","Capacity - Disk Usage", "Capacity - Hosts and Sourcetypes","Capacity - Saved Searches","Capacity - Users")
searches_general=("General - Applications","General - Searches","General - Server")
searches_health=("Health - Errors and Warnings","Health - Indexing Latency","Health - Long Searches","Health - Skipped Searches")
sessionKey = sys.stdin.readline().strip()

def getJobStatus(sid,sessionKey):
 try:
  uri = "https://localhost:8089//services/search/jobs/" + sid
  headers = {'Authorization':''}
  headers['Authorization'] = 'Splunk ' + sessionKey
  r = requests.post(uri, headers=headers, verify=False)
  isDone = re.search("isDone\"\>(.*)\<",r.text).group(1)
  if int(isDone) == 1:
   return True
  else:
   return False
 except Exception, e:
  logger.exception("Failed to getJobStatus " + str(sid) + " job due to the following exception: " + str(e)) 

def dispatchSearch(search,sessionKey):
 try:
  uri = "https://localhost:8089/servicesNS/nobody/Splunk_TA_RTP-Health-Checker/saved/searches/" + str(search) + "/dispatch"
  data = {'trigger_actions':1}
  headers = {'Authorization':''}
  headers['Authorization'] = 'Splunk ' + sessionKey
  r = requests.post(uri, headers=headers, data=data, verify=False)
  sid=minidom.parseString(r.text).getElementsByTagName('sid')[0].childNodes[0].nodeValue
  if r.status_code < 300:
   logger.info("Dispatch " + str(search) + " Successful, status code: " + str(r.status_code))
   while not getJobStatus(sid,sessionKey):
    logger.info("Execution pausing for 15 seconds to allow " + str(search) + " to complete")
    time.sleep(15)
  logger.info("Execution resuming")
 except Exception, e:
  logger.exception("Failed to dispatch " + str(search) + " job due to the following exception: " + str(e)) 

def uploadData(search_name, payload):
 try:
  ### TBD: Gracefully find the csv files  
  lookup = search_name.replace(" ","_").replace("-","").replace("__","_").lower()
  lookupPath = os.path.join(lookupsPath,lookup+'.csv') 
  ### TBD: Transform data to remove \n etc...
  file = open(lookupPath, 'rb')
  reader = csv.DictReader(file,delimiter=",")
  row_count = 0
  for row in reader:
   if '\n' in row:
    pass
   else:
    row_count = row_count + 1
  
  data = payload + ',"post_data_to_crm":false,"report_name":"' + search_name + '","data": ['
  with open(lookupPath, 'rb') as f:
   reader = csv.DictReader(f,delimiter=',')
   print("row_count is " + str(row_count))
   i=1
   for row in reader:
    if i < row_count:
     data = data + json.dumps(row) + ","
     i = i + 1
    else:
     data = data + json.dumps(row)
  data = data + ']}' 
  print(data) 
  uri = 'https://gp8047zitj.execute-api.us-east-1.amazonaws.com/prod/rtpHealthChecker'
  r = requests.post(uri,data=data, verify=False)  
  if r.status_code < 300:
   logger.info("Upload of " + str(search_name) + " data was successful, status code: " + str(r.status_code))
   print(r.status_code)
  else:
   logger.error("Failed to upload " + str(search_name) + " data, status code: " + str(r.status_code))  
   print(r.status_code)
 except Exception, e:
  logger.exception("Failed to upload " + str(search_name) + " data due to the following exception: " + str(e)) 

def sendToCRM(payload):
 try:
  uri = 'https://gp8047zitj.execute-api.us-east-1.amazonaws.com/prod/rtpHealthChecker'
  data = payload + ',"post_data_to_crm":true,"report_name":"none","data": []}'
  r = requests.post(uri,data=data, verify=False) 
  if not r.status_code <= 399:
   logger.error("Couldnt post company name, first name, last name, phone, and email to RTP. Status Code:" + str(r.status_code))
 except Exception, e:
  logger.error("Couldnt post company name, first name, last name, phone, and email to RTP. Error:" + str(e))

try:
 config = ConfigParser.RawConfigParser()
 config.optionxform = str
 config.read(confPath)
 if not config.has_section("settings"):
  logger.errror(confPath + " doesnt contain a section named settings")
 else:
  send_capacity_data = config.getboolean("settings","send_capacity_data")
  send_general_data = config.getboolean("settings","send_general_data")
  send_health_data = config.getboolean("settings","send_health_data")
  no_internet = config.getboolean("settings","no_internet")
  license_agreement = config.getboolean("settings","license_agreement")  
  payload = config.get("settings","payload") 
except Exception as e:
 logger.error("Couldnt parse the options from local rtpHealthChecker.conf due to the following error: " + str(e))

try:
 if license_agreement:
  # Make & Send Capacity Data
  try:
   if send_capacity_data:
    for search_name in searches_capacity:
     dispatchSearch(urllib.quote_plus(str(search_name)),sessionKey)
     if not no_internet:
      uploadData(search_name, payload)
     else:
      lookupfiles = [f for f in os.listdir(lookupsPath) if os.path.isfile(os.path.join(lookupsPath, f))]
      with tarfile.open(os.path.join(lookupsPath,"RTPHealthCheckData.tar.gz"),"w") as tar:
       for lookupfile in lookupfiles:
        tar.add(os.path.join(lookupsPath,lookupfile))
  except Exception as e:
   # by design the exception error is vague
   logger.error("Capacity Data Error: " + str(e))
 
  # Make & Send General Data
  try:
   if send_general_data:
    for search_name in searches_general:
     dispatchSearch(urllib.quote_plus(str(search_name)),sessionKey)
     if not no_internet:
      uploadData(search_name, payload)
     else:
      lookupfiles = [f for f in os.listdir(lookupsPath) if os.path.isfile(os.path.join(lookupsPath, f))]
      with tarfile.open(os.path.join(lookupsPath,"RTPHealthCheckData.tar.gz"),"w") as tar:
       for lookupfile in lookupfiles:
        tar.add(os.path.join(lookupsPath,lookupfile))
  except Exception as e:
   # by design the exception error is vague
   logger.error("General Data Error: " + str(e))

  # Make & Send Health Data
  try:
   if send_health_data:
    for search_name in searches_health:
     dispatchSearch(urllib.quote_plus(str(search_name)),sessionKey)
     if not no_internet:
      uploadData(search_name, payload)
     else:
      lookupfiles = [f for f in os.listdir(lookupsPath) if os.path.isfile(os.path.join(lookupsPath, f))]
      with tarfile.open(os.path.join(lookupsPath,"RTPHealthCheckData.tar.gz"),"w") as tar:
       for lookupfile in lookupfiles:
        tar.add(os.path.join(lookupsPath,lookupfile))
  except Exception as e:
   logger.error("Health Data Error: " + str(e))
  # Send contact details to CRM
  try:
   if not no_internet:
    sendToCRM(payload)
  except Exception as e:
   logger.error(str(e))
 else:
  logger.info("The license agreement was not accepted. The Health Check will not run.")
except Exception as e:
 logger.error("Could not determine if the license agreement was accepted due to the following error: " + str(e))

# Disable this scripted input
try:
 config = ConfigParser.RawConfigParser()
 config.optionxform = str
 config.read(inputsConfPath)
 if not config.has_section("script://$SPLUNK_HOME/etc/apps/Splunk_TA_RTP-Health-Checker/bin/rtpHealthChecker.py"):
  config.add_section("script://$SPLUNK_HOME/etc/apps/Splunk_TA_RTP-Health-Checker/bin/rtpHealthChecker.py")
 config.set("script://$SPLUNK_HOME/etc/apps/Splunk_TA_RTP-Health-Checker/bin/rtpHealthChecker.py","disabled",1)
 with open(inputsConfPath,"wb") as confFile:
  config.write(confFile)
except Exception as e:
 logger.error("Could not disable the scripted input due to the following error: " + str(e))
