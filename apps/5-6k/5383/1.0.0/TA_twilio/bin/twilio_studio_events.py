import sys
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
_APP_NAME = 'TA_twilio'
import os.path

base_location = sys.path[0].split(os.path.sep)
base_location.pop(-1)
base_location.append(os.path.sep.join(["lib", "python3.7", "site-packages"]))
sys.path.pop(0)
sys.path.insert(0, os.path.sep.join(base_location))
sys.path.insert(0, make_splunkhome_path(["etc", "apps", _APP_NAME, "lib"]))

from twilio_modular_input import twilio_modular_input
import logging as log

import json
import requests as request
from requests.auth import HTTPBasicAuth
import splunk.appserver.mrsparkle.lib.util as util
from requests.exceptions import *
from twilio.rest import Client

_MI_APP_NAME = 'Twilio Studio Logs'

# SYSTEM EXIT CODES
_SYS_EXIT_FAILED_GET_OAUTH_CREDENTIALS = 6


_SPLUNK_HOME = os.getenv("SPLUNK_HOME")
if _SPLUNK_HOME is None:
    _SPLUNK_HOME = make_splunkhome_path([""])

_APP_HOME = os.path.join(util.get_apps_dir(), _APP_NAME)
_app_local_directory = os.path.join(_APP_HOME, "local")
_BIN_PATH = os.path.join(_APP_HOME, "bin")


MI = twilio_modular_input(_APP_NAME, {
    "title": "Twilio Studio Logs",
    "description": "The Twilio Studio Logs input will connect to your Twilio account and pull the studio logs into the splunk.",
    "args": [
         {"name": "account_id",
         "description": "Account ID of the app created in Twilio",
         "title": "Account ID",
         "required": True
         },
         {"name": "auth_token",
         "description": "Authentication Token of the app created in Twilio",
         "title": "Authentication Token",
         "required": True
         }
    ]
})


def run():
    MI.start()
    try:
        log.info("action=starting_modular_input_run")
        MI.set_logger(log) 
        account_id = MI.get_config("account_id")
        auth_token = MI.get_config("auth_token")        
        
        try:
            client = Client(account_id, auth_token)
            log.info("action=getting_access_key loaded=true")
        except Exception as e:
            log.error("operation=load_client config={} msg={}".format(MI.get_config("name"), e))
            MI._catch_error(Exception("operation=load_client config={} msg={}".format(MI.get_config("name"), e)))        
            
        twilio_events = MI.get_twilio_studio_events(client)        
    except Exception as e:
        MI._catch_error(e)
    MI.info("action=stop item=modular_input")
    MI.stop()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            MI.scheme()
        elif sys.argv[1] == "--validate-arguments":
            MI.validate_arguments()
        elif sys.argv[1] == "--test":
            print('No tests for the scheme present')
        else:
            print('You giveth weird arguments')
    else:
        run()

    sys.exit(0)
