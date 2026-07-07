import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.modularinput import *
from splunklib import client
from splunk.clilib import cli_common as cli
from cyberintegrations import TIPoller
from cyberintegrations import ParserHelper
import logging
import logging.handlers
import json
import datetime
import urllib3
from state_store import FileStateStore, Credentials

from cyberintegrations.exception import ConnectionException

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

APP_NAME = 'facct_ti'
SEQUPDATE_FILE = os.environ['SPLUNK_HOME'] + '/etc/apps/facct_ti/bin/seqUpdate_storage.json'
LOG_FILE_DIRECTORY = os.environ['SPLUNK_HOME'] + '/var/log/splunk/' + APP_NAME

logger = logging.getLogger(APP_NAME)
logging.propagate = False
logger.setLevel(logging.DEBUG)
if not os.path.exists(LOG_FILE_DIRECTORY):
    os.makedirs(LOG_FILE_DIRECTORY)
log_path = os.path.join(LOG_FILE_DIRECTORY,"modinput.log")
file_handler = logging.handlers.RotatingFileHandler(log_path)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.debug("Logger Initialized")


COLLECTION_LIST = {
    "compromised/account_group": "Compromised::Account",
    "compromised/bank_card_group": "Compromised::Group_Card",
    "compromised/masked_card": "Compromised::Masked Card",
    "compromised/mule": "Compromised::Mule",
    "compromised/breached": "Compromised::Brached DB",
    "compromised/reaper": "Compromised::Darkweb",
    "compromised/access": "Compromised::Access",
    "compromised/discord": "Compromised::Discord",
    "compromised/messenger": "Compromised::Messenger",
    "ioc/common": "IOC::Common",
    "attacks/ddos": "Attacks::DDoS",
    "attacks/deface": "Attacks::Deface",
    "attacks/phishing_kit": "Attacks::Phishing Kit",
    "attacks/phishing_group": "Attacks::Phishing Group",
    "hi/threat": "Human Intelligence::Threat",
    "hi/threat_actor": "Human Intelligence::Threat Actor",
    "apt/threat": "APT::Threat",
    "apt/threat_actor": "APT::Threat Actor",
    "osi/git_repository": "OSI::Git Repository",
    "osi/vulnerability": "OSI::Vulnerability",
    "osi/public_leak": "OSI::Public Leak",
    "suspicious_ip/tor_node": "Suspicious IP::Tor Node",
    "suspicious_ip/open_proxy": "Suspicious IP::Open Proxy",
    "suspicious_ip/socks_proxy": "Suspicious IP::Socks Proxy",
    "suspicious_ip/scanner": "Suspicious IP::Scanner",
    "suspicious_ip/vpn": "Suspicious IP::VPN",
    "malware/cnc": "Malware::C&C",
    "malware/config": "Malware::Config",
    "malware/signature": "Malware::Signature",
    "malware/malware": "Malware::Malware",
    "malware/yara": "Malware::yara",
    }

INPUT_COLLECTION_ITEMS_LIST = {
    'apt/threat': 'apt_threat',
    'apt/threat_actor': 'apt_threat_actor',
    'attacks/ddos': 'attacks_ddos',
    'attacks/deface': 'attacks_deface',
    'attacks/phishing': 'attacks_phishing',
    'attacks/phishing_kit': 'attacks_phishing_kit',
    'bp/phishing': 'bp_phishing',
    'bp/phishing_kit': 'bp_phishing_kit',
    'compromised/account': 'compromised_account',
    'compromised/card': 'compromised_card',
    'compromised/imei': 'compromised_imei',
    'compromised/mule': 'compromised_mule',
    'compromised/breached': 'compromised_breached',
    'compromised/reaper': 'compromised_reaper',
    'hi/threat': 'hi_threat',
    'hi/threat_actor': 'hi_threat_actor',
    'malware/cnc': 'malware_cnc',
    'malware/targeted_malware': 'malware_targeted_malware',
    'osi/git_leak': 'osi_git_leak',
    'osi/public_leak': 'osi_public_leak',
    'osi/vulnerability': 'osi_vulnerability',
    'suspicious_ip/open_proxy': 'suspicious_ip_open_proxy',
    'suspicious_ip/socks_proxy': 'suspicious_ip_socks_proxy',
    'suspicious_ip/tor_node': 'suspicious_ip_tor_node'
}

MASKED_VALUE = {
    'compromised/breached': [
        'password'
    ],
    'compromised/account_group': [
        'password'
    ]
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


class FACCTTI(Script):
    def __init__(self):

        super().__init__()
        self.session_key = None

    def get_scheme(self):
        scheme = Scheme("FACCT Threat Intelligence")
        scheme.use_external_validation = True
        scheme.use_single_instance = False
        scheme.description = "FACCT Threat Intelligence"
        username = Argument("facct_username")
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

        masking_type = Argument("masking_type")
        masking_type.title = "Masking data type"
        masking_type.description = "Input: 1 - Mask half of the field 2 - Mask all fild."
        masking_type.data_type = Argument.data_type_string
        masking_type.required_on_create = False
        masking_type.required_on_edit = False
        scheme.add_argument(masking_type)
        


        for collection_tech_name, collection_name in COLLECTION_LIST.items():
            temp = Argument(collection_tech_name.replace("/", "_"))
            temp.title = collection_name
            temp.data_type = Argument.data_type_boolean
            temp.required_on_create = False
            temp.required_on_edit = False
            scheme.add_argument(temp)
            if collection_tech_name == "hi/threat" or collection_tech_name == 'apt/threat':
                temp = Argument(collection_tech_name.replace("/", "_")+'_img_state')
                temp.title = "Download img from source"
                temp.data_type = Argument.data_type_boolean
                temp.required_on_create = False
                temp.required_on_edit = False
                scheme.add_argument(temp)
            if collection_tech_name in MASKED_VALUE.keys():
                temp = Argument(collection_tech_name.replace("/", "_") + '_mask_state')
                temp.title = "Mask confidential data"
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
        USERNAME = validation_definition.parameters['facct_username']
        self.session_key = validation_definition.__dict__.get('metadata').get('session_key')

        API_KEY = Credentials.get_api_key(self.session_key, USERNAME)

        # Validate date fields set correctly.
        for collection in list(COLLECTION_LIST.keys()):
            collection_name = collection.replace("/", "_")
            date_field_name = collection_name + "_date"
            if validation_definition.parameters.get(collection_name) == '1':
                if not validation_definition.parameters.get(date_field_name):
                    raise ValueError("Please provide an initial date value for " + COLLECTION_LIST.get(collection) + " collection.")
                try:
                    datetime.datetime.strptime(validation_definition.parameters.get(date_field_name), "%Y-%m-%d")
                except ValueError as e:
                    raise ValueError("Please, provide initial date for " + COLLECTION_LIST.get(collection) + " collection in the following format: YYYY-mm-dd")

        poller = TIPoller(USERNAME, API_KEY,'https://ti.facct.ru/api/v2/')
        poller.set_verify(True)
        poller.set_product()
        PROXY_ENABLED = validation_definition.parameters['enable_proxy']

        if PROXY_ENABLED == '1':
            PROXY_ADDRESS = validation_definition.parameters['proxy_address']
            PROXY_PORT = validation_definition.parameters['proxy_port']
            PROXY_PROTOCOL = validation_definition.parameters['proxy_protocol']

        # Validate connection and available collections.
        if validation_definition.parameters['enable_proxy'] == '1':
            poller.set_proxies(
                PROXY_PROTOCOL,PROXY_ADDRESS,PROXY_PORT
            )
        try:
            s = poller.get_available_collections()
            logger.info("Validation complete")
        except Exception as e:
            raise ValueError("ERROR. " + str(e))

    def stream_events(self, inputs, ew):
        for input_name, input_item in inputs.inputs.items():
            state_store = FileStateStore(inputs.metadata, input_name)
            USERNAME = input_item['facct_username']
            self.session_key = inputs.metadata.get('session_key')
            API_KEY = Credentials.get_api_key(self.session_key, USERNAME)
            PROXY_ENABLED = input_item['enable_proxy']
            PROXY_ADDRESS = input_item.get('proxy_address', None)
            PROXY_PORT = input_item.get('proxy_port', None)
            PROXY_PROTOCOL = input_item.get('proxy_protocol', None)
            MASK_TYPE = input_item.get('masking_type',None)

            poller = TIPoller(USERNAME, API_KEY,'https://ti.facct.ru/api/v2/')
            poller.set_product(
                product_type="SIEM",
                product_name="Splunk",
                integration_name="FACCT Threat Intelligence",
                integration_version='1.4.2'
                )
            poller.set_verify(True)
            if PROXY_ENABLED == '1':
                poller.set_proxies(
                    PROXY_PROTOCOL,PROXY_ADDRESS,PROXY_PORT
                )

            enabled_collections = [key.replace("/", "_") for key, value in input_item.items() if value == '1']
            enabled_collections = [i for i in list(COLLECTION_LIST.keys()) if i.replace("/", "_") in enabled_collections]

            disabled_collections = [key.replace("/", "_") for key, value in input_item.items() if value == '0']
            disabled_collections = [i for i in list(COLLECTION_LIST.keys()) if i.replace("/", "_") in disabled_collections]

            for collection in disabled_collections:
                delete_sequpdate(state_store, collection)

            for collection in enabled_collections:
                logger.info('Start for collection: {}'.format(collection))
                if collection in ["compromised/reaper", "compromised/breached"]:
                    start_date = get_current_sequpdates(state_store, collection)

                    if start_date is None:
                        start_date = input_item.get(collection.replace("/", "_") + "_date")
                        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").strftime("%Y-%m-%d")
                    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
                    ew.log("INFO", "START DATE: " + start_date + ", END DATE:" + current_date)
                    logger.info("start date {}, End date{}".format(start_date, current_date))

                    feeds_iterator = poller.create_search_generator(collection, date_from=start_date, date_to=current_date)
                    try:
                        for response in feeds_iterator:
                            for item in response.raw_dict.get("items"):
                                event = Event()
                                event.stanza = collection.replace("/", "_")
                                event.data = json.dumps(item)
                                event.source = "facct_ti_" + collection.replace("/", "_")
                                event.sourceType = "facct_ti_" + collection.replace("/", "_")
                                ew.write_event(event)

                            if collection == "compromised/breached":
                                ew.log("INFO", "New Datetime: " + response.raw_dict.get("items")[-1].get("updateTime"))
                                save_checkpoint(state_store, collection, response.raw_dict.get("items")[-1].get("updateTime"))
                            if collection == "compromised/reaper":
                                ew.log("INFO", "New Datetime: " + response.raw_dict.get("items")[-1].get("datetime"))
                                save_checkpoint(state_store, collection, response.raw_dict.get("items")[-1].get("datetime"))
                        save_checkpoint(state_store, collection, current_date)
                    except Exception as e:
                        ew.log("ERROR", "Failed to get the " + collection + " collection. Reason: " + str(e))
                        logger.info("ERROR: Failed to get the {} collection. Reason: {}".format(collection,e))

                else:
                    seqUpdate = get_current_sequpdates(state_store, collection)
                    # if no seqUpdate file -> get this value from server
                    if seqUpdate is None:
                        ew.log("INFO", "Getting " + collection + " seqUpdate from server...")
                        logger.info("Getting {}, seqUpdate from server...".format(collection))
                        configured_date = input_item.get(collection.replace("/", "_") + "_date")
                        try:
                            seqUpdate = poller.get_seq_update_dict(date=configured_date).get(collection)
                            save_checkpoint(state_store, collection, seqUpdate)
                            ew.log("INFO", "The value received from server:" + str(seqUpdate))
                            logger.info("The value received from server: {}".format(str(seqUpdate)))

                        except Exception as e:
                            ew.log("ERROR", "Failed to get the " + collection + " collection. Reason: " + str(e) )
                            logger.info("Failed to get the {} collection. Reason: {}".format(collection, str(e) ))

                            continue

                    ew.log("INFO", "Downloading the " + collection + " collection starting with seqUpdate " + str(seqUpdate))
                    logger.info("Downloading the {} collection starting with seqUpdate {}".format(collection, str(seqUpdate)))

                    feeds_iterator = poller.create_update_generator(collection, sequpdate=seqUpdate, limit=100)
                    try:
                        for response in feeds_iterator:
                            for item in response.raw_dict.get("items"):
                                if collection in ["apt/threat", "hi/threat"]:
                                    apt_img_state = input_item.get(collection.replace("/", "_") + "_img_state")
                                    hi_img_state = input_item.get(collection.replace("/", "_") + "_img_state")
                                    if apt_img_state == '1' or hi_img_state == '1':
                                        REPORTS_IMAGES_DIRECTORY = os.environ['SPLUNK_HOME'] + '/var/spool/splunk/facct_ti/threats/'
                                        if not os.path.exists(LOG_FILE_DIRECTORY):
                                            os.makedirs(LOG_FILE_DIRECTORY)
                                        for file_obj in item.get("files"):
                                            current_image_directory = os.environ['SPLUNK_HOME'] + '/var/spool/splunk/facct_ti/threats/' + "hi/threat" +"/"+  item.get("id") + "/file/"
                                            if not os.path.exists(current_image_directory):
                                                os.makedirs(current_image_directory)
                                            try:
                                                file_content = poller.search_file_in_threats(collection, item.get("id"), file_obj.get("name"))
                                                with open(current_image_directory + "/" + file_obj.get("name"), "wb") as f:
                                                    f.write(file_content)
                                            except Exception as e:
                                                ew.log("ERROR", str(e))
                                                logger.info("ERROR".format(str(e)))

                                                pass
                                if collection in MASKED_VALUE.keys():
                                    mask_state = input_item.get(collection.replace("/", "_") + "_mask_state")
                                    if mask_state == '1':
                                        for field in MASKED_VALUE[collection]:
                                            value_field = ParserHelper.find_element_by_key(item, field)
                                            if value_field and MASK_TYPE=='1':
                                                ParserHelper.set_element_by_key(item, field, value_field[:len(value_field)//2] + '*'*(len(value_field)//2))
                                            elif value_field and MASK_TYPE=='2':
                                                ParserHelper.set_element_by_key(item, field, "")

                                event = Event()
                                event.stanza = collection.replace("/", "_")
                                event.data = json.dumps(item)
                                event.source = "facct_ti_" + collection.replace("/", "_")
                                event.sourceType = "facct_ti_" + collection.replace("/", "_")

                                ew.write_event(event)
                            save_checkpoint(state_store, collection, response.sequpdate)
                    except Exception as e:
                        ew.log("ERROR", "Failed to get the " + collection + " collection. Reason: " + str(e))
                        logger.info("Failed to get the {} collection. Reason: {}".format(collection, e))

if __name__ == "__main__":
    sys.exit(FACCTTI().run(sys.argv))