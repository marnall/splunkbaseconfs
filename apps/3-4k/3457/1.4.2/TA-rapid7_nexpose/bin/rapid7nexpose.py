from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from builtins import input
from builtins import str
from future import standard_library
standard_library.install_aliases()
import sys
import xml.dom.minidom, xml.sax.saxutils
import xml.etree.ElementTree as ET
import os
import splunk.clilib.cli_common as scommon
import api.pnexpose as pnx
from api.utils import Utils
import getpass
import splunk
import splunk.auth as auth
from nexpose_reporter import NexposeReporter
from multiprocessing.dummy import Pool
import json
import requests

SPLUNK_HOME = os.environ['SPLUNK_HOME']
APP_NAME = 'TA-rapid7_nexpose'
API_VER = '2.0.1'

VENDOR = "Splunk"
PRODUCT = "SplunkEnterprise"
VERSION = "1.3.1"

manual_run = None

logger = Utils.setup_logging()

def get_manual_session():
    logger.info("Running manual session")
    username = os.environ.get('SPLUNK_USERNAME')
    password = os.environ.get('SPLUNK_PASSWORD')

    if not (username and password):
        username = input("Please enter Splunk username: ")
        password = getpass.getpass()

    sessionKey = auth.getSessionKey(username, password)

    if sessionKey:
        print('Fetched sessionKey manually! Continuing...')
        return sessionKey

    print('Failed to get session key manually! Exiting...')
    exit(2)


# Empty introspection routine
def do_scheme():
    print("""
    <scheme>
    <title>Rapid7 Nexpose</title>
    <description>Enable input from Rapid7 Nexpose</description>
    <streaming_mode>xml</streaming_mode>
    <endpoint>
      <args>
        <arg name="name">
          <required_on_create>1</required_on_create>
          <title>Job Name</title>
        </arg>
        
        <arg name="job_type">
          <required_on_create>1</required_on_create>
          <required_on_edit>0</required_on_edit>
          <title>Sites to include</title>
        </arg>

        <arg name="sites">
          <required_on_create>0</required_on_create>
          <required_on_edit>0</required_on_edit>
          <title>Sites to include</title>
        </arg>
      </args>
    </endpoint>
    </scheme>
    """)


# Empty validation routine. This routine is optional.
def validate_arguments(): 
    pass


def get_session_key(root_node):
    session_key = root_node.find('session_key')
    if session_key is None:
        print("Session key not found")
        return 0
    session_key = "".join(session_key.itertext())
    return session_key


# access the credentials in /servicesNS/nobody/<MyApp>/admin/passwords
def getPassword(session_key):
    logger.info('Retrieving password')

    server_uri = splunk.getLocalServerInfo()
    credential_name = 'nexpose_password'

    password_url = '{}/servicesNS/nobody/{}/storage/passwords/%3A{}%3A?output_mode=json'.format(server_uri, APP_NAME, credential_name)

    try:
        # attempting to retrieve cleartext password, disabling SSL verification for practical reasons
        result = requests.get(url=password_url, headers={'Authorization': 'Splunk ' + session_key}, verify=False)
        if result.status_code != 200:
            logger.error("Error retrieving password: %s" % str(result.json()))
            sys.exit()
    except Exception as e:
        error = "ERROR Error making password request: %s" % e
        logger.error(error)
        sys.exit()

    logger.info("Loading Splunk password response")
    splunk_response = json.loads(result.text)

    logger.info("Parsing Splunk password response")    
    password = splunk_response.get("entry")[0].get("content").get("clear_password")

    return password


def parseConfig(root_node):
    config = {}
    checkpoint_node = root_node.find('checkpoint_dir')
    config['checkpoint_dir'] = "".join(checkpoint_node.itertext())
    
    for stanza in root_node.find('configuration'):
        for param in stanza:
            config[param.get('name')] = "".join(param.itertext())
    return config


# Routine to get the value of an input
def get_config():
    try:
        # read everything from stdin
        if manual_run:
            config_str = sys.argv[2] 
        else:
            config_str = sys.stdin.read()

        try:
            tree = ET.fromstring(config_str)
        except Exception as e:
            print("Error parsing config: {}, will not be able to configure Rapid7 Nexpose add-on module input".format(e))
            raise Exception("Error parsing config: {}".format(e))

        config = parseConfig(tree)

        if manual_run:
            session_key = get_manual_session() 
        else:
            session_key = get_session_key(tree)
     
        config['session_key'] = session_key
        config['password'] = getPassword(session_key)
        
        return config

    except Exception as e:
        raise Exception("Error getting Splunk configuration via STDIN: %s" % str(e))

    return config_str


def register_metrics(settings):
    client = pnx.nexposeClient(settings['hostname'], 
                               settings['port'], 
                               settings['username'],
                               settings['password'], 
                               logger, 
                               API_VER)
    session = client.get_auth_token()

    logger.setup_statistics_collection(VENDOR, PRODUCT, VERSION)
    result = logger.on_connect(settings['hostname'], settings['port'], 
                               session, '')


def get_reporter(settings):
    reporter = NexposeReporter(settings['username'],
                               settings['password'],
                               settings['hostname'],
                               settings['port'],
                               settings['session_key'],
                               settings.get('index', 'default'),
                               settings.get('new_scans_only', False),
                               settings.get('import_solution', False)
                               )
    return reporter


def run_site_queries(reporter, settings):

    reporter.set_sites(settings.get('sites', ''))
    reporter.check_history(settings['checkpoint_dir'])
    concurrency = 4
    
    if settings.get('concurrency'):
        try:
            concurrency = int(settings.get('concurrency'))
        except Exception as e:
            concurrency = 4

    logger.info("Running import with {} threads".format(concurrency))

    reporter.run_site_queries(concurrency)


def run_vuln_exception_queries(reporter, settings):
    reporter.run_exception_query()


# Routine to index data
def run_script():
    logger.info("--- Import job starting ---")
    settings = scommon.getConfStanza('nexpose_details', 'setupentity')
    settings.update(get_config())

    register_metrics(settings)

    reporter = get_reporter(settings)

    if settings.get('job_type', 'asset_vulns') == 'asset_vulns':
        run_site_queries(reporter, settings)
    else:
        run_vuln_exception_queries(reporter, settings)
    
    logger.info("--- Import job complete ---")


# Script must implement these args: scheme, validate-arguments
if __name__ == '__main__':    

    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            do_scheme()
        elif sys.argv[1] == "--validate-arguments":
            validate_arguments()
        elif sys.argv[1] == "--manual":
            manual_run = True
            run_script()
        else:
            pass
    else:
        run_script()

    sys.exit(0)
