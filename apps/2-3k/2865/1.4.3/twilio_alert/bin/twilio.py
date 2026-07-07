from __future__ import print_function

import sys,os,hashlib,time
import json
import logging
try:
    import splunk.entity as entity
except:
    pass
from logging.handlers import TimedRotatingFileHandler

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")

#set up logging to this location
LOG_FILENAME = os.path.join(SPLUNK_HOME,"var","log","splunk","twilioalert_app_modularalert.log")

# Set up a specific logger
logger = logging.getLogger('twilioalert')

#default logging level , can be overidden in stanza config
logger.setLevel(logging.INFO)

#log format
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

# Add the daily rolling log message handler to the logger
handler = TimedRotatingFileHandler(LOG_FILENAME, when="d",interval=1,backupCount=5)
handler.setFormatter(formatter)
logger.addHandler(handler)

#dynamically load in any eggs
EGG_DIR = os.path.join(SPLUNK_HOME,"etc","apps","twilio_alert","bin")

for filename in os.listdir(EGG_DIR):
    if filename.endswith(".egg"):
        sys.path.append(os.path.join(EGG_DIR ,filename))

from twilio.rest import Client


def get_credentials(session_key):
   myapp = 'twilio_alert'
   try:
      # list all credentials
      entities = entity.getEntities(['admin', 'passwords'], namespace=myapp,
                                    owner='nobody', sessionKey=session_key)
   except Exception as e:
      logger.error("Could not get credentials from splunk. Error: %s" % str(e))
      return {}

   return entities.items()

def send_message(settings,search_name):

    logger.debug("%s : Sending message with settings %s"  % (search_name,settings))
    
    account_sid = settings.get('accountsid')
    auth_token = settings.get('authtoken')
    from_number = settings.get('fromnumber')
    to_number = settings.get('tonumber')
    message = settings.get('message')
    
    activation_key = settings.get('activationkey').strip()
    app_name = "Twilio SMS Alerting"
    
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
        client = Client(account_sid, auth_token)  
  
        numbers_list = to_number.split(",") 
        
        for number in numbers_list:  
            logger.info("%s : Sending SMS via Twilio from number=%s to number=%s with message=%s" % (search_name,from_number, number,message))   
            message_resp = client.messages.create(body=message,to=number,from_=from_number)    
            logger.info("%s : Sent Twilio SMS message with sid=%s" % (search_name,message_resp.sid))
          
        return True  
    except Exception as tre:  
        logger.error("%s : Error sending SMS message via Twilio: %s" % (search_name,tre)) 
        return False  
    except:  
        e = sys.exc_info()[0]  
        logger.error("%s : Error sending SMS message via Twilio: %s" % (search_name,e))  
        return False  
  
  
if __name__ == "__main__":  
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":  
        json_config = sys.stdin.read()
        payload = json.loads(json_config)

        #change log level from configuration stanza if present
        log_level = logging.getLevelName(payload.get('configuration').get("log_level","INFO"))
        logger.setLevel(log_level)
        
        search_name = payload.get('search_name')

        logger.info("%s : Executing Twilio Alert" % search_name)

       
        payload = json.loads(json_config)

        settings = payload.get('configuration')
        account_sid = settings.get('accountsid')

        credentials_list = get_credentials(payload.get('session_key'))

        for i, c in credentials_list:
            username = c['username']
            password = c['clear_password']
            if username == account_sid:
                settings["authtoken"] = password
            if username == "activation_key":
                settings["activationkey"] = password


        if not send_message(settings,search_name):
            logger.error("%s : Failed trying to send SMS Message via Twilio" % search_name)
            sys.exit(2)
        else:
            logger.info("%s : SMS Message successfully sent via Twilio" % search_name)
    else:
        logger.error("Unsupported execution mode (expected --execute flag)")
        sys.exit(1)
