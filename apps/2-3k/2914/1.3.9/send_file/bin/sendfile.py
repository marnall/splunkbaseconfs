from __future__ import print_function

import sys,os,hashlib,time
import json
import shutil
import logging
#for running on Universal Forwarders where the library is not present
try:
    import splunk.entity as entity
except:
    pass
from logging.handlers import TimedRotatingFileHandler

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")

#set up logging to this location
LOG_FILENAME = os.path.join(SPLUNK_HOME,"var","log","splunk","sendfilealert_app_modularalert.log")

# Set up a specific logger
logger = logging.getLogger('sendfilealert')

#default logging level , can be overidden in stanza config
logger.setLevel(logging.INFO)

#log format
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

# Add the daily rolling log message handler to the logger
handler = TimedRotatingFileHandler(LOG_FILENAME, when="d",interval=1,backupCount=5)
handler.setFormatter(formatter)
logger.addHandler(handler)
  
def get_credentials(session_key):
   myapp = 'send_file'
   try:
      # list all credentials
      entities = entity.getEntities(['admin', 'passwords'], namespace=myapp,
                                    owner='nobody', sessionKey=session_key)
   except Exception as e:
      logger.error("Could not get credentials from splunk. Error: %s" % str(e))
      return {}

   return entities.items()

def send_file(file,settings,search_name):
    logger.debug("%s : Sending file with settings %s" % (search_name,settings))
    
    directory = settings.get('directory')
    filename = settings.get('filename')
    
    activation_key = settings.get('activationkey').strip()
    app_name = "Scheduled Export of Indexed Data (SEND) to File"
    
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
        
        dstfile =  os.path.join(directory, filename)
        shutil.copy(file, dstfile) 
    
        return True  
    except Exception as tre:  
        logger.error("%s : Error sending file: %s" % (search_name,tre))
        return False  
    except:  
        e = sys.exc_info()[0]  
        logger.error("%s : Error sending file: %s" % (search_name,e))
        return False  
  
  
if __name__ == "__main__":  
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":  
        
        json_config = sys.stdin.read()
        payload = json.loads(json_config)

        #change log level from configuration stanza if present
        log_level = logging.getLevelName(payload.get('configuration').get("log_level","INFO"))
        logger.setLevel(log_level)
        
        search_name = payload.get('search_name')

        logger.info("%s : Executing Send To File Alert" % search_name)


        credentials_list = get_credentials(payload.get('session_key'))

        for i, c in credentials_list:
            replace_key='{encrypted:%s}' % c['username']
            json_config = json_config.replace(replace_key,c['clear_password'])

       
        payload = json.loads(json_config)

        if not send_file(payload.get('results_file'),payload.get('configuration'),search_name):
            logger.error("%s : Failed trying to send file" % search_name)
            sys.exit(2)
        else:
            logger.info("%s : File successfully sent" % search_name)
    else:
        logger.error("Unsupported execution mode (expected --execute flag)")
        sys.exit(1)
