import sys
import os

import logging
import json
import datetime
import time
import re


import xml.dom.minidom

# Initialize Global Variables
APP_NAME = __file__.split(os.sep)[-3]
APP_DIR  = os.path.join(os.environ["SPLUNK_HOME"], 'etc', 'apps', APP_NAME)
BIN_DIR  = os.path.join(APP_DIR, 'bin')
LIB_DIR  = os.path.join(APP_DIR, 'bin', "lib")

# Add the "./lib" directory to sys.path to enable import on Custom Libraries
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
sys.path.append(os.path.join(os.path.dirname(__file__), "lib", "Terraform"))

# Add the 3rd party libraries to the sys.path
for filename in os.listdir(LIB_DIR):
    if filename.endswith(".egg"):
        sys.path.append(LIB_DIR + filename)
    if filename.endswith(".whl"):
        sys.path.append(LIB_DIR + filename)

import xmltodict
from HelperFunctions import log, encodeXMLText

# Custom Splunk Libraries
from SplunkCheckpoint import SplunkCheckpoint

# Terraform Cloud Libraries
from TerraformRuns import TerraformRuns
from TerraformApply import TerraformApply
from TerraformWorkspace import TerraformWorkspace

# Setup Logging Configuration
logging.root
logging.root.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s %(message)s')
# with zero args , should go to STD ERR
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)

def do_scheme():
    print("""<scheme>
        <title>Automation Fabric Monitoring - Terraform Cloud Addon Addon</title>
        <description>AFM Addon for getting Terraform Cloud Runs Logs</description>
        <use_external_validation>true</use_external_validation>
        <streaming_mode>xml</streaming_mode>

        <endpoint>
            <args>
                <arg name="terraform_host">
                    <title>Host: </title>
                    <description>Terraform Cloud Host</description>
                </arg>

                <arg name="protocol">
                    <title>Protocol: </title>
                    <description>Protocol to be used in API Calls (HTTP/HTTPS)</description>
                </arg>

                <arg name="token">
                    <title>Token</title>
                    <description>Terraform Cloud Token</description>
                </arg>

                <arg name="workspace_id">
                    <title>Workspace ID</title>
                    <description>Terraform Cloud Workspace ID</description>
                </arg>
            </args>
        </endpoint>
    </scheme>
    """)

def do_validate():
    # Temp Validation Message
    print("Argument Validation is currently unavaiable. Will be included at a later version of the app.")
    

    # config = get_input_config()
    # TODO
    # if error , print_validation_error & sys.exit(2)

def get_input_config():
    config = {}

    try:
        # read everything from STDIN
        config_str = sys.stdin.read()

        log(config_str, "raw_xml_config.log")

        # parse the config XML
        doc = xml.dom.minidom.parseString(config_str)
        root = doc.documentElement

        session_key_node = root.getElementsByTagName("session_key")[0]
        if session_key_node and session_key_node.firstChild and \
            session_key_node.firstChild.nodeType == session_key_node.firstChild.TEXT_NODE:

            data = session_key_node.firstChild.data
            config["session_key"] = data

        server_uri_node = root.getElementsByTagName("server_uri")[0]
        if server_uri_node and server_uri_node.firstChild and \
            server_uri_node.firstChild.nodeType == server_uri_node.firstChild.TEXT_NODE:

            data = server_uri_node.firstChild.data
            config["server_uri"] = data

        conf_node = root.getElementsByTagName("configuration")[0]
        if conf_node:
            logging.debug("XML: found configuration")
            stanza = conf_node.getElementsByTagName("stanza")[0]
            if stanza:
                stanza_name = stanza.getAttribute("name")
                if stanza_name:
                    # logging.debug("XML: found stanza " + stanza_name)
                    config["name"] = stanza_name

                    params = stanza.getElementsByTagName("param")
                    for param in params:
                        param_name = param.getAttribute("name")
                        logging.debug("XML: found param '%s'" % param_name)
                        if param_name and param.firstChild and \
                           param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                            data = param.firstChild.data
                            config[param_name] = data
                            # logging.debug("XML: '%s' -> '%s'" % (param_name, data))

        checkpnt_node = root.getElementsByTagName("checkpoint_dir")[0]
        if checkpnt_node and checkpnt_node.firstChild and \
           checkpnt_node.firstChild.nodeType == checkpnt_node.firstChild.TEXT_NODE:
            config["checkpoint_dir"] = checkpnt_node.firstChild.data

        if not config:
            raise Exception("Invalid configuration received from Splunk.")

        config_name = config["name"].replace("afm_aa_control_room://", "")
        
        log_file = config_name + ".log"
        log(config_str, log_file)

        config_log = config_name + ".config"
        log(json.dumps(config), config_log)

    except Exception as e:
        raise Exception("Error getting Splunk configuration via STDIN: %s" % str(e))

    return config

def parse_config():
    config_str = sys.stdin.read()

    # Convert XML to Dict
    config_xml = xmltodict.parse(config_str)
    config_dict = json.loads(json.dumps(config_xml))['input']

    configuration = {
        'server_host': "",
        'server_uri': "",
        'session_key': "",
        'checkpoint_dir': "",

        'stanza': "",
        'app_name': "",

        'host': "",
        'protocol': "",
        'token': "",
        'workspace_id': "",
    }

    if 'server_host' in config_dict:
        configuration['server_host'] = config_dict['server_host']
    
    if 'server_uri' in config_dict:
        configuration['server_uri'] = config_dict['server_uri']
    
    if 'session_key' in config_dict:
        configuration['session_key'] = config_dict['session_key']

    if 'checkpoint_dir' in config_dict:
        configuration['checkpoint_dir'] = config_dict['checkpoint_dir']
    
    if 'configuration' in config_dict and 'stanza' in config_dict['configuration'] and '@name' in config_dict['configuration']['stanza']:
        configuration['stanza'] = config_dict['configuration']['stanza']['@name']

    if 'configuration' in config_dict and 'stanza' in config_dict['configuration'] and '@app' in config_dict['configuration']['stanza']:
        configuration['app_name'] = config_dict['configuration']['stanza']['@app']
    
    for param in config_dict['configuration']['stanza']['param']:
        configuration[param['@name']] = param['#text']

    return configuration


def do_run():
    config = parse_config()
    log(json.dumps(config), "raw_xml_config.log")

    terraformRuns = TerraformRuns(\
        hostname = config['terraform_host'], \
        protocol = config['protocol'], \
        token = config['token'], \
        workspace_id = config['workspace_id'])
    terraformRunsList = terraformRuns.list_runs()

    terraformWorkspace = TerraformWorkspace(\
        hostname = config['terraform_host'], \
        protocol = config['protocol'], \
        token = config['token'], \
        workspace_id = config['workspace_id'])

    splunkCheckpoint = SplunkCheckpoint(\
        checkpoint_file=config["stanza"], \
        checkpoint_dir=config["checkpoint_dir"])

    checkpointConfig = splunkCheckpoint.load_checkpoint()
    
    checkpointDate = None
    if checkpointConfig.has_option(config["stanza"], "created-at"):
        checkpointDate = checkpointConfig.get(config["stanza"], "created-at")
        checkpointDate = datetime.datetime.strptime(checkpointDate, "%Y-%m-%dT%H:%M:%S.%fZ")

    newCheckpointDate = checkpointDate

    for event in terraformRunsList:
        event_timestamp = datetime.datetime.strptime(event['attributes']['created-at'], "%Y-%m-%dT%H:%M:%S.%fZ")
        # Skip the events that is earlier than the checkpoint date
        if (checkpointDate is not None and checkpointDate >= event_timestamp): 
            continue

        if (newCheckpointDate is None or newCheckpointDate < event_timestamp):
            newCheckpointDate = event_timestamp

        terraformApply = TerraformApply(\
            hostname = config['terraform_host'], \
            protocol = config['protocol'], \
            token = config['token'], \
            run_id = event['id'])

        event['apply_logs'] = terraformApply.get_apply_log()

        event['relationships']['workspace']['data']['name'] = terraformWorkspace.get_workspace()['attributes']['name']
        event['relationships']['organization'] = terraformWorkspace.get_workspace()['relationships']['organization']
        
        print_xml_stream_with_time(json.dumps(event), re.sub(r"\.\d*Z$", "", event['attributes']['created-at']))

    newCheckpointDate = newCheckpointDate.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    splunkCheckpoint.save_checkpoint({ "created-at": newCheckpointDate})


def usage():
    print("usage: %s [--scheme|--validate-arguments]")
    logging.error("Incorrect Program Usage")
    sys.exit(2)

# HELPER FUNCTIONS

# prints XML stream
def print_xml_stream(s):
    print("<stream><event unbroken=\"1\"><data>%s</data><done/></event></stream>" % encodeXMLText(s))


def print_xml_stream_with_time(s, date):
    timestamp = time.mktime(datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S").timetuple())
    print("<stream><event unbroken=\"1\"><time>%s</time><data>%s</data><done/></event></stream>" % (encodeXMLText(str(timestamp)), encodeXMLText(s)))

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            do_scheme()
        elif sys.argv[1] == "--validate-arguments":
            do_validate()
        else:
            usage()
    else:
        do_run()

    sys.exit(0)