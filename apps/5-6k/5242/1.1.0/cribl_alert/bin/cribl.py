from __future__ import print_function

import sys,os,hashlib,time
import json
import shutil
import logging
import splunk.entity as entity
import gzip
import requests
import csv,io
from logging.handlers import TimedRotatingFileHandler

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")


requests.packages.urllib3.disable_warnings()

#set up logging to this location
LOG_FILENAME = os.path.join(SPLUNK_HOME,"var","log","splunk","criblalert_app_modularalert.log")

# Set up a specific logger
logger = logging.getLogger('criblalert')

#default logging level , can be overidden in stanza config
logger.setLevel(logging.INFO)

#log format
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

# Add the daily rolling log message handler to the logger
handler = TimedRotatingFileHandler(LOG_FILENAME, when="d",interval=1,backupCount=5)
handler.setFormatter(formatter)
logger.addHandler(handler)
  
def get_credentials(session_key):
   myapp = 'cribl_alert'
   try:
      # list all credentials
      entities = entity.getEntities(['admin', 'passwords'], namespace=myapp,
                                    owner='nobody', sessionKey=session_key)
   except Exception as e:
      raise Exception("Could not get credentials from splunk. Error: %s" % str(e))

   return entities.items()

def push_to_cribl(file,settings,search_name):
    logger.debug("%s : Pushing search results to Cribl with settings %s" % (search_name,settings))
    
    host = settings.get('host')
    port = settings.get('port')
    authtoken = settings.get('authtoken')
    fieldlist = settings.get('fieldlist','_time,_raw,host,source,sourcetype,index,eventtype')
    maxpostevents = settings.get('maxpostevents',100)
    activation_key = settings.get('activationkey').strip()
    app_name = "Cribl Modular Alert"
    
    if len(activation_key) > 32:
        activation_hash = activation_key[:32]
        activation_ts = activation_key[32:][::-1]
        current_ts = time.time()
        m = hashlib.md5()
        m.update((app_name + activation_ts).encode('utf-8'))
        if not m.hexdigest().upper() == activation_hash.upper():
            logger.error("Trial Activation key for App '%s' failed. Please ensure that you copy/pasted the key correctly." % app_name)
            sys.exit(2)
        if ((current_ts - int(activation_ts)) > 604800):
            logger.error("Trial Activation key for App '%s' has now expired. Please visit http://www.baboonbones.com/#activation to purchase a non expiring key." % app_name)
            sys.exit(2)
    else:
        m = hashlib.md5()
        m.update((app_name).encode('utf-8'))
        if not m.hexdigest().upper() == activation_key.upper():
            logger.error("Activation key for App '%s' failed. Please ensure that you copy/pasted the key correctly." % app_name)
            sys.exit(2)
    
    try:  
        
        cribl_uri = 'https://'+host+':'+port+'/cribl/_bulk'

        headers = {'Authorization': authtoken}
       
        keys_we_want = fieldlist.split(",")
        

        with gzip.open(file,'rt') as search_results_file:
            search_results = csv.DictReader(search_results_file)
            
            counter = 0;
            bulk_json = ''
            for result in search_results:
                counter += 1
                cribl_event = { c_key: result[c_key] for c_key in keys_we_want }
                bulk_json = bulk_json+json.dumps(cribl_event)+"\n"
                if (counter == maxpostevents):
                    counter = 0;
                    logger.debug("%s : Posting Data to Cribl URI %s , bytes_total=%d" % (search_name,cribl_uri,len(bulk_json.encode('utf-8'))))
                    r = requests.post(cribl_uri, data=bulk_json, headers=headers, verify=False)
                    r.raise_for_status()
                    bulk_json = ''   

        if(counter > 0 and counter < maxpostevents): 
            logger.debug("%s : Posting Data to Cribl URI %s , bytes_total=%d" % (search_name,cribl_uri,len(bulk_json.encode('utf-8'))))           
            r = requests.post(cribl_uri, data=bulk_json, headers=headers, verify=False)
            r.raise_for_status()

        return True 

    except requests.exceptions.HTTPError as e:
        error_output = r.text
        error_http_code = r.status_code
        error_event=""
        error_event += 'http_error_code = %s error_message = %s' % (error_http_code, error_output) 
        logger.error("%s : Error pushing search results to Cribl: %s" % (search_name,error_event))
        return False
    except Exception as tre:  
        logger.error("%s : Error pushing search results to Cribl: %s" % (search_name,tre))
        return False  
    except:  
        e = sys.exc_info()[0]  
        logger.error("%s : Error pushing search results to Cribl: %s" % (search_name,e))
        return False  
    
  
if __name__ == "__main__":  
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":  
        

        json_config = sys.stdin.read()
        payload = json.loads(json_config)

        #change log level from configuration stanza if present
        log_level = logging.getLevelName(payload.get('configuration').get("log_level","INFO"))
        logger.setLevel(log_level)
        
        search_name = payload.get('search_name')

        logger.info("%s : Executing Push Data to Cribl" % search_name)
        
        credentials_list = get_credentials(payload.get('session_key'))

        for i, c in credentials_list:
            replace_key='{encrypted:%s}' % c['username']
            json_config = json_config.replace(replace_key,c['clear_password'])

       
        payload = json.loads(json_config)


        if not push_to_cribl(payload.get('results_file'),payload.get('configuration'),search_name):
            logger.error("%s : Failed trying to push search results to Cribl" % search_name)
            sys.exit(2)
        else:
            logger.info("%s : Successfully pushed search results to Cribl" % search_name)
    else:
        logger.critical("Unsupported execution mode (expected --execute flag)")
        sys.exit(1)
