import os
import sys
import time
import urllib2
import json
import base64
import logging
import xml.dom.minidom, xml.sax.saxutils
import splunk.entity as entity

# globals
KOBO_API_URL = "https://kc.kobotoolbox.org/api/v1/data"

# set up logging suitable for splunkd comsumption
logging.root
logging.root.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(formatter)
logging.root.addHandler(handler)

SCHEME = """<scheme>
    <title>KoBoToolbox</title>
    <description>Get survey data from KoBoToolbox.</description>
    <use_external_validation>false</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <endpoint>
        <args>
            <arg name="name">
                <title>Name</title>
                <description>Enter a unique name for this input</description>
            </arg>

            <arg name="username">
                <title>KoBoToolbox API Username</title>
                <description></description>
            </arg>

            <arg name="password">
                <title>KoBoToolbox API Password</title>
                <description></description>
            </arg>

            <arg name="refresh_interval">
                <title>Refresh Interval (Seconds)</title>
                <description>Minimum value of 60 seconds</description>
            </arg>
        </args>
    </endpoint>
</scheme>
"""

def do_scheme():
	print SCHEME

def usage():
    print "usage: %s [--scheme|--validate-arguments]"
    sys.exit(2)

def init_stream():
    sys.stdout.write("<stream>")

def fini_stream():
    sys.stdout.write("</stream>")

# prints XML error data to be consumed by Splunk
def print_error(s):
    print "<error><message>%s</message></error>" % xml.sax.saxutils.escape(s)

# prints XML event
def print_event(time, data):
     print "<event><time>%s</time><data>%s</data></event>"  % (time,xml.sax.saxutils.escape(data))

def validate_conf(config, key):
    if key not in config:
        raise Exception, "Invalid configuration received from Splunk: key '%s' is missing." % key

# read XML configuration passed from splunkd
def get_config():
    config = {}

    try:
        # read everything from stdin
        config_str = sys.stdin.read()

        # parse the config XML
        doc = xml.dom.minidom.parseString(config_str)
        root = doc.documentElement
        conf_node = root.getElementsByTagName("configuration")[0]
        if conf_node:
            logging.debug("XML: found configuration")
            stanza = conf_node.getElementsByTagName("stanza")[0]
            if stanza:
                stanza_name = stanza.getAttribute("name")
                if stanza_name:
                    logging.debug("XML: found stanza " + stanza_name)
                    config["name"] = stanza_name

                    params = stanza.getElementsByTagName("param")
                    for param in params:
                        param_name = param.getAttribute("name")
                        logging.debug("XML: found param '%s'" % param_name)
                        if param_name and param.firstChild and \
                           param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                            data = param.firstChild.data
                            config[param_name] = data
                            logging.debug("XML: '%s' -> '%s'" % (param_name, data))

        checkpnt_node = root.getElementsByTagName("checkpoint_dir")[0]
        if checkpnt_node and checkpnt_node.firstChild and \
           checkpnt_node.firstChild.nodeType == checkpnt_node.firstChild.TEXT_NODE:
            config["checkpoint_dir"] = checkpnt_node.firstChild.data

        if not config:
            raise Exception, "Invalid configuration received from Splunk."

        # just some validation: make sure these keys are present (required)
        validate_conf(config, "name")
        validate_conf(config, "username")
        validate_conf(config, "password")
        validate_conf(config, "refresh_interval")
        validate_conf(config, "checkpoint_dir")
    except Exception, e:
        raise Exception, "Error getting Splunk configuration via STDIN: %s" % str(e)

    # validate refresh_interval is integer and override if required
    if isinstance(config['refresh_interval'], (int, long)):
        # if interval is less than 60 seconds, set to 60 seconds - that should be frequent enough
        if config['refresh_interval'] < 60:
            config['refresh_interval'] = 60
    else:
        # if for some odd reason interval is not an integer, set to default of 600 seconds
        config['refresh_interval'] = 600

    return config

def get_validation_data():
    val_data = {}

    # read everything from stdin
    val_str = sys.stdin.read()

    # parse the validation XML
    doc = xml.dom.minidom.parseString(val_str)
    root = doc.documentElement

    logging.debug("XML: found items")
    item_node = root.getElementsByTagName("item")[0]
    if item_node:
        logging.debug("XML: found item")

        name = item_node.getAttribute("name")
        val_data["stanza"] = name

        params_node = item_node.getElementsByTagName("param")
        for param in params_node:
            name = param.getAttribute("name")
            logging.debug("Found param %s" % name)
            if name and param.firstChild and \
               param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                val_data[name] = param.firstChild.data

    return val_data

# returns last submission id for survey if the checkpoint file exists
def load_checkpoint(config, survey_id):
    chk_file = os.path.join(config["checkpoint_dir"], survey_id)
    # try to open this file
    try:
        f = open(chk_file, 'r')
        last_submission_id = f.readline().rstrip('\n')
        f.close()
    except:
        # assume that this means the checkpoint it not there
        return 0
    return last_submission_id

# creates a checkpoint file with the last submission id for survey
def save_checkpoint(config, survey_id, submission_id):
    chk_file = os.path.join(config["checkpoint_dir"], survey_id)
    logging.info("Checkpointing submission id=%s survey id=%s file=%s", submission_id, survey_id, chk_file)
    # write last submission id for survey to checkpoint file
    f = open(chk_file, 'w+')
    f.write(submission_id)
    f.close()

# function to make web requests to the KoBoToolbox API
def request_api(username, password, uri=''):

    auth_header = 'Authorization', b'Basic ' + base64.b64encode(username + b':' + password)
    url = KOBO_API_URL + uri

    request = urllib2.Request(url, None, {'Content-Type': 'application/json'})
    request.add_header(*auth_header)
    logging.debug("KoBoToolbox API request: %s" % url)

    try:
        api_response = json.load(urllib2.urlopen(request))

        logging.debug("KoBoToolbox API response: %s" % json.dumps(api_response))
    except Exception, e:
        api_response = None

        logging.error("Could not access API for KoBoToolbox: %s" % str(e))

    return api_response

def run():
    config = get_config()
    init_stream()

    while True:
        logging.debug("Getting list of active surveys from KoBoToolbox API")

        # get list of surveys from KoBoToolbox API
        api_response = request_api(config['username'], config['password'])

        # loop through surveys
        for survey in api_response:
            survey_id = str(survey['id'])

            # get last submission id from checkpoint file (otherwise we set submission id to 0 to start at beginning)
            last_submission_id = load_checkpoint(config, survey_id)
            submissions_uri = '/' + survey_id + '?query={"_id": {"$gt": ' + str(last_submission_id) + '}}'

            # get list of survey submissions from KoBoToolbox API
            logging.debug("Getting list of submissions for survey id %s from KoBoToolbox API" % survey['id_string'])
            api_response = request_api(config['username'], config['password'], submissions_uri)
            submission_count = len(api_response)
            logging.info("Found %s new submissions for survey id %s" % (str(submission_count), survey['id_string']))

            # loop through survey submissions
            for submission in api_response:
                submission_id = str(submission['_id'])

                # time and JSON object of submission for Splunk
                event_time = int(time.mktime(time.strptime(submission['_submission_time'], '%Y-%m-%dT%H:%M:%S')))
                event_data = json.dumps(submission)

                # stream submission data
                logging.debug("Streaming submission data to Splunk: %s" % event_data)
                print_event(event_time,event_data)

                # write latest survey submission id to tracker file
                save_checkpoint(config, survey_id, submission_id)

        # wait for refresh
        time.sleep(config['refresh_interval'])
    fini_stream()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            do_scheme()
        elif sys.argv[1] == "--validate-arguments":
            api_response = request_api(sys.argv[2], sys.argv[3])

            survey_count = len(api_response)
            print "KoBoToolbox API connection successful! %s surveys present" % survey_count
        elif sys.argv[1] == "--test":
            print 'No tests for the scheme present'
        else:
            usage()
    else:
        # just request data from KoBoToolbox
        run()

    sys.exit(0)
