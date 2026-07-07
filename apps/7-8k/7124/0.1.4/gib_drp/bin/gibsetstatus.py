import sys
import os
import urllib.parse
from state_store import Credentials
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.modularinput import *
from splunk.clilib import cli_common as cli
import sys
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
from cyberintegrations import DRPPoller
import validators

import logging

APP_NAME = 'gib_drp'
SEQUPDATE_FILE = os.environ['SPLUNK_HOME'] + '/etc/apps/gib_drp/bin/seqUpdate_storage.json'
LOG_FILE_DIRECTORY = os.environ['SPLUNK_HOME'] + '/var/log/splunk/' + APP_NAME

logger = logging.getLogger(APP_NAME)
logging.propagate = False
logger.setLevel(logging.DEBUG)
if not os.path.exists(LOG_FILE_DIRECTORY):
    os.makedirs(LOG_FILE_DIRECTORY)
log_path = os.path.join(LOG_FILE_DIRECTORY,"modinput_search.log")
file_handler = logging.handlers.RotatingFileHandler(log_path)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.debug("Logger Initialized")




@Configuration(type="reporting")
class gibsetstatus(GeneratingCommand):
    id_item = Option(require=True)
    status = Option(require=True)

    def read_conf(self, path):
        with open("../local/inputs.conf") as conf:
            for item in conf:
                if path in item:
                    c = item.split('=')
                    return c[1].strip()

    def generate(self):
        # USERNAME = self.read_conf('gib_username')
        session_key = super().service.__dict__.get('token')
        USERNAME = Credentials.get_username(session_key)
        logger.info("Start uploading data")
        API_KEY = Credentials.get_api_key(session_key, USERNAME)
        API_URL = 'https://drp.group-ib.com/client_api/'
        PROXY_ENABLED = self.read_conf('enable_proxy')
        ID_ITEM = self.id_item
        STATUS = self.status
        try:
            poller = DRPPoller(username=USERNAME, api_key=API_KEY, api_url='https://drp.group-ib.com/client_api/')
            poller.set_verify(True)
            poller.set_product(product_type="SIEM", product_name="Splunk", integration_name="Group-IB DRP Splunk", integration_version='0.1.0')
            if PROXY_ENABLED == '1':
                PROXY_ADDRESS = self.read_conf('proxy_address')
                PROXY_PORT = self.read_conf('proxy_port')
                PROXY_PROTOCOL = self.read_conf('proxy_protocol')
                poller.set_proxies({
                    "http": PROXY_PROTOCOL + "://" + PROXY_ADDRESS + ":" + str(PROXY_PORT),
                    "https": PROXY_PROTOCOL + "://" + PROXY_ADDRESS + ":" + str(PROXY_PORT)
                })

            poller.change_status(ID_ITEM, STATUS)

            yield 'Status was changed'

        finally:
            poller.close_session()


dispatch(gibsetstatus, sys.argv, sys.stdin, sys.stdout, __name__)
