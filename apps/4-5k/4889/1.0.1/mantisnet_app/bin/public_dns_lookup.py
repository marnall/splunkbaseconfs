'''
Custom Scripted Input for populating a lookup file

This scripted input retrieves a CSV file of public DNS information and writes it to 
a lookup file.

This performs better than using inline Splunk external lookup scripts

January 2020

Developed by BaboonBones, Ltd. ( www.baboonbones.com ) for Mantisnet ( www.mantisnet.com )
'''

import splunk.entity as entity
import sys
import os
import re
import requests
import logging
from logging.handlers import TimedRotatingFileHandler


APP_NAME = "mantisnet_app"
CONF_FILE = "mantisnet"
STANZA_NAME = "lookup:public_dns"
USER = ""
PASS = ""
URL = ""
LOOKUP_CSV = ""
CONF_STANZA = None
SESSION_KEY = ""

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
    
#set up logging to this location
LOG_FILENAME = os.path.join(SPLUNK_HOME,"var/log/splunk/mantisnet_app_lookup_public_dns.log")

# Set up a specific logger
logger = logging.getLogger('mantisnet')

logger.setLevel(logging.DEBUG)

#log format
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

# Add the daily rolling log message handler to the logger
handler = TimedRotatingFileHandler(LOG_FILENAME, when="d",interval=1,backupCount=5)
handler.setFormatter(formatter)
logger.addHandler(handler)


def get_credentials():

   try:
      # list all credentials
      entities = entity.getEntities(['admin', 'passwords'], namespace=APP_NAME,
                                    owner='nobody', sessionKey=SESSION_KEY)
   except Exception, e:
      raise Exception("Could not get %s credentials from splunk. Error: %s"
                      % (APP_NAME, str(e)))

   # return first set of credentials
   for i, c in entities.items():
   	    if c['username'] == USER:
        	return c['username'], c['clear_password']

   logger.warn("No credentials have been found")
   return None,None
   

def run_script():

  try:

    USER = CONF_STANZA["username"]
    URL = CONF_STANZA["url"]
    LOOKUP_CSV = CONF_STANZA["lookup_csv"]

    csv_file_path = os.path.join(SPLUNK_HOME,"etc" ,"apps" ,APP_NAME,"lookups",LOOKUP_CSV)


    #if any credentials were encrypted via the apps setup page , we could get them here
    USER,PASS = get_credentials()

    with requests.Session() as s:
      download = s.get(URL)
      with open(csv_file_path, 'w') as csv_file:
        csv_file.writelines(download.content)  
        csv_file.close() 
    
  	
  except:  
    e = sys.exc_info()[0]  
    logger.error("Error : %s" % e)
  pass


if __name__ == '__main__':
 
  logger.info("Running Mantisnet public_dns_lookup script")
	# Get the sessionKey from splunkd
	# Note: inputs.conf shoud specify passAuth = splunk-system-user
  sk = sys.stdin.readline().strip()
  SESSION_KEY = re.sub(r'sessionKey=', "", sk)
  

  try:
	 # Get the stanza key/value pairs
	 CONF_STANZA = entity.getEntity('configs/conf-' + CONF_FILE, STANZA_NAME, namespace=APP_NAME, owner='nobody', sessionKey=SESSION_KEY)
	 run_script()
  except:  
    e = sys.exc_info()[0]  
    logger.error("Error : %s" % e)
  pass
 
 

