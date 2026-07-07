import requests
import os, sys
import logging, logging.handlers
import json
import splunk
import urllib3

# as per https://github.com/splunk/splunk-app-examples/blob/master/custom_endpoints/hello-world/bin/hello_world.py
# with additional details on https://github.com/jrervin/splunk-rest-examples/blob/master/doc/persistent_examples.md
from splunk.persistconn.application import PersistentServerConnectionApplication

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def setup_logging():
    logger = logging.getLogger('SearchHeadStatus')
    SPLUNK_HOME = os.environ['SPLUNK_HOME']

    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = "searchhead_status.log"
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
    splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a')
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
    return logger

logger = setup_logging()
logger.info("SearchHeadStatus start")

class SearchHeadStatus(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        data = json.loads(in_string)
        headers = { "Authorization" : "Splunk " + data['system_authtoken'] }

        # Temporary hack until we improve our security keys
        #requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += 'HIGH:!DH:!aNULL'      
        logger = setup_logging()

        url = "https://localhost:8089/services/shcluster/member/info?output_mode=json"
        logger.debug(f"requests.get call to url={url} headers={headers}")

        status = ""
        try:
            res = requests.get(url, headers=headers, verify=True)
        except requests.exceptions.SSLError:
            logger.error(f"requests.get call to url={url} failed due to SSLError, you may need to set verify=False")
            status = "SSL_Verify_Error"

        status_code = 503
        if status!="":
            pass
        elif res.status_code != 200:
            logger.error(f"Call to {url} failed with text={res.text} status_code={res.status_code} reason={res.reason}")
            status = "REST_Call_Error"
        else:
            logger.debug(f"Response from url={url} text={res.text} status_code={res.status_code}")
            status = res.json()['entry'][0]['content']['status']
            if status == "Up":
                status_code = 200

        logger.info(f"Returning status response {status}")

        return {'payload': status,  # Payload of the request.
                'status': status_code          # HTTP status code
        }

