import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.modularinput import *
from splunklib import client
from splunk.clilib import cli_common as cli
from cyberintegrations import DRPPoller
import logging.handlers
import json
import datetime
import urllib3
from state_store import FileStateStore, Credentials


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

APP_NAME = 'gib_drp'
SEQUPDATE_FILE = os.environ['SPLUNK_HOME'] + '/etc/apps/gib_drp/bin/seqUpdate_storage.json'
LOG_FILE_DIRECTORY = os.environ['SPLUNK_HOME'] + '/var/log/splunk/' + APP_NAME

logger = logging.getLogger(APP_NAME)
logging.propagate = False
logger.setLevel(logging.DEBUG)
if not os.path.exists(LOG_FILE_DIRECTORY):
    os.makedirs(LOG_FILE_DIRECTORY)
log_path = os.path.join(LOG_FILE_DIRECTORY, "modinput.log")
file_handler = logging.handlers.RotatingFileHandler(log_path)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.debug("Logger Initialized")

COLLECTION_LIST = {
    'violation/list': 'Violation List'
}



def get_current_sequpdates(state_store, collection):
    collection_param_name = collection.replace("/", "_")
    return state_store.get_state(collection_param_name)


def save_checkpoint(state_store, collection, seq_update):
    collection_param_name = collection.replace("/", "_")
    state_store.update_state(collection_param_name, seq_update)


def delete_sequpdate(state_store, collection):
    collection_param_name = collection.replace("/", "_")
    state_store.update_state(collection_param_name, None)


class GIBDRP(Script):
    def __init__(self):

        super().__init__()
        self.session_key = None

    def get_scheme(self):
        scheme = Scheme("GIB Digital Risk Protection")
        scheme.use_external_validation = True
        scheme.use_single_instance = False
        scheme.description = "GIB Digital Risk Protection"
        username = Argument("gib_username")
        username.title = "Username"
        username.data_type = Argument.data_type_string
        username.description = "Username"
        username.required_on_create = True
        username.required_on_edit = True
        scheme.add_argument(username)

        enable_proxy = Argument("enable_proxy")
        enable_proxy.title = "Enable Proxy?"
        enable_proxy.data_type = Argument.data_type_boolean
        enable_proxy.description = ""
        enable_proxy.required_on_create = False
        enable_proxy.required_on_edit = False
        scheme.add_argument(enable_proxy)

        proxy_address = Argument("proxy_address")
        proxy_address.title = "Proxy Address"
        proxy_address.data_type = Argument.data_type_string
        proxy_address.required_on_create = False
        proxy_address.required_on_edit = False
        scheme.add_argument(proxy_address)

        proxy_port = Argument("proxy_port")
        proxy_port.title = "Proxy Port"
        proxy_port.data_type = Argument.data_type_number
        proxy_port.required_on_create = False
        proxy_port.required_on_edit = False
        scheme.add_argument(proxy_port)

        proxy_protocol = Argument("proxy_protocol")
        proxy_protocol.title = "Proxy Protocol"
        proxy_protocol.data_type = Argument.data_type_string
        proxy_protocol.required_on_create = False
        proxy_protocol.required_on_edit = False
        scheme.add_argument(proxy_protocol)


        for collection_tech_name, collection_name in COLLECTION_LIST.items():
            temp = Argument(collection_tech_name.replace("/", "_"))
            temp.title = collection_name
            temp.data_type = Argument.data_type_boolean
            temp.required_on_create = False
            temp.required_on_edit = False
            scheme.add_argument(temp)

            temp_date = Argument(collection_tech_name.replace("/", "_") + "_date")
            temp_date.title = "Initial Date"
            temp_date.data_type = Argument.data_type_string
            temp_date.required_on_create = False
            temp_date.required_on_edit = False
            scheme.add_argument(temp_date)

        return scheme

    def validate_input(self, validation_definition):
        USERNAME = validation_definition.parameters['gib_username']
        self.session_key = validation_definition.__dict__.get('metadata').get('session_key')
        API_KEY = Credentials.get_api_key(self.session_key, USERNAME)
        API_URL = 'https://drp.group-ib.com/client_api/'

        # Validate date fields set correctly.
        for collection in list(COLLECTION_LIST.keys()):
            collection_name = collection.replace("/", "_")
            date_field_name = collection_name + "_date"
            if validation_definition.parameters.get(collection_name) == '1':
                if not validation_definition.parameters.get(date_field_name):
                    raise ValueError(
                        "Please provide an initial date value for " + COLLECTION_LIST.get(collection) + " collection.")
                try:
                    datetime.datetime.strptime(validation_definition.parameters.get(date_field_name), "%Y-%m-%d")
                except ValueError as e:
                    raise ValueError("Please, provide initial date for " + COLLECTION_LIST.get(
                        collection) + " collection in the following format: YYYY-mm-dd")

        poller = DRPPoller(USERNAME, API_KEY, API_URL)
        poller.set_verify(True)
        PROXY_ENABLED = validation_definition.parameters['enable_proxy']

        if PROXY_ENABLED == '1':
            PROXY_ADDRESS = validation_definition.parameters['proxy_address']
            PROXY_PORT = validation_definition.parameters['proxy_port']
            PROXY_PROTOCOL = validation_definition.parameters['proxy_protocol']

        # Validate connection and available collections.
        if validation_definition.parameters['enable_proxy'] == '1':
            poller.set_proxies({
                "http": PROXY_PROTOCOL + "://" + PROXY_ADDRESS + ":" + str(PROXY_PORT),
                "https": PROXY_PROTOCOL + "://" + PROXY_ADDRESS + ":" + str(PROXY_PORT)
            })
        try:
            s = poller.get_seq_update_dict(date='2023-01-01')
            logger.info("Validation complete")
        except Exception as e:
            raise ValueError("ERROR. " + str(e))

    def stream_events(self, inputs, ew):
        for input_name, input_item in inputs.inputs.items():
            state_store = FileStateStore(inputs.metadata, input_name)
            USERNAME = input_item['gib_username']
            self.session_key = inputs.metadata.get('session_key')
            API_KEY = Credentials.get_api_key(self.session_key, USERNAME)
            API_URL = 'https://drp.group-ib.com/client_api/'
            PROXY_ENABLED = input_item['enable_proxy']
            PROXY_ADDRESS = input_item.get('proxy_address', None)
            PROXY_PORT = input_item.get('proxy_port', None)
            PROXY_PROTOCOL = input_item.get('proxy_protocol', None)

            poller = DRPPoller(USERNAME, API_KEY, API_URL)
            poller.set_product(product_type="SIEM", product_name="Splunk", integration_name="Group-IB DRP Splunk", integration_version='0.1.4')
            poller.set_verify(True)
            if PROXY_ENABLED == '1':
                poller.set_proxies({
                    "http": PROXY_PROTOCOL + "://" + PROXY_ADDRESS + ":" + str(PROXY_PORT),
                    "https": PROXY_PROTOCOL + "://" + PROXY_ADDRESS + ":" + str(PROXY_PORT)
                })

            enabled_collections = [key.replace("/", "_") for key, value in input_item.items() if value == '1']
            enabled_collections = [i for i in list(COLLECTION_LIST.keys()) if
                                   i.replace("/", "_") in enabled_collections]

            disabled_collections = [key.replace("/", "_") for key, value in input_item.items() if value == '0']
            disabled_collections = [i for i in list(COLLECTION_LIST.keys()) if
                                    i.replace("/", "_") in disabled_collections]

            for collection in disabled_collections:
                delete_sequpdate(state_store, collection)

            for collection in enabled_collections:
                logger.info('Start for collection: {}'.format(collection))

                seqUpdate = get_current_sequpdates(state_store, collection)
                # if no seqUpdate file -> get this value from server
                if seqUpdate is None:
                    ew.log("INFO", "Getting " + collection + " seqUpdate from server...")
                    configured_date = input_item.get(collection.replace("/", "_") + "_date")
                    try:
                        seqUpdate = poller.get_seq_update_dict(date=configured_date).get(collection)
                        save_checkpoint(state_store, collection, seqUpdate)
                        ew.log("INFO", "The value received from server:" + str(seqUpdate))
                    except Exception as e:
                        ew.log("ERROR", "Failed to get the " + collection + " collection. Reason: " + str(e))
                        continue

                ew.log("INFO",
                       "Downloading the " + collection + " collection starting with seqUpdate " + str(seqUpdate))
                feeds_iterator = poller.create_update_generator(collection, sequpdate=seqUpdate, limit=100)
                try:
                    for response in feeds_iterator:
                        for item in response.raw_dict.get("items"):
                            event = Event()
                            event.stanza = collection.replace("/", "_")
                            event.data = json.dumps(item)
                            event.source = "gib_drp_" + collection.replace("/", "_")
                            event.sourceType = "gib_drp_" + collection.replace("/", "_")

                            ew.write_event(event)
                        save_checkpoint(state_store, collection, response.sequpdate)
                except Exception as e:
                    ew.log("ERROR", "Failed to get the " + collection + " collection. Reason: " + str(e))
                    logger.info("ERROR: Failed to get the {} collection. Reason: {}".format(collection, e))


if __name__ == "__main__":
    sys.exit(GIBDRP().run(sys.argv))