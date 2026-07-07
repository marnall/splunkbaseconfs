# Copyright (c) 2017 by Farsight Security, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import re
import sys
import ssl

from axamd.client.exceptions import ProblemDetails
from axamd.client import Client
import requests
from splunk.clilib import cli_common as cli
import xml.dom.minidom
import xml.sax.saxutils
import splunk.entity as entity

logging.root.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)

SCHEME = """\
<scheme>
    <title>Sentry Manager SRA</title>
    <description>Pulls data from SRA channel</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <endpoint>
        <args>
            <arg name="channels">
                <title>Channels (comma delimited)</title>
                <description>https://www.farsightsecurity.com/Technical/fsi-sie-channel-guide.pdf</description>
            </arg>
            <arg name="watches">
                <title>Watches (comma delimited)</title>
            </arg>
            <arg name="timeout">
                <title>Socket timeout in seconds</title>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="sample_rate">
                <title>Channel sampling rate (percent)</title>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="rate_limit">
                <title>Maximum packets per second</title>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="report_interval">
                <title>Seconds between emission of server accounting messages (packet statistics)</title>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
        </args>
    </endpoint>
</scheme>\
"""

def do_scheme():
    print SCHEME

def get_validation_config():
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

def validate_conf(config, key):
    if key not in config:
        raise Exception, "Invalid configuration received from Splunk: key '%s' is missing." % key

def print_error(s):
    print "<error><message>%s</message></error>" % xml.sax.saxutils.escape(s)

#read XML configuration passed from splunkd
def get_config():
    config = {}

    try:
        # read everything from stdin
        config_str = sys.stdin.read()

        # parse the config XML
        doc = xml.dom.minidom.parseString(config_str)
        root = doc.documentElement
        s_key = root.getElementsByTagName("session_key")[0]
        config["session_key"] = s_key.firstChild.nodeValue
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
        validate_conf(config, "channels")
        validate_conf(config, "watches")
    except Exception, e:
        raise Exception, "Error getting Splunk configuration via STDIN: %s" % str(e)

    return config

def make_error_message(s, sessionKey, uri):
    headers = {'Authorization': 'Splunk %s' % sessionKey}
    r = requests.post(uri, headers=headers, data={'name':'Farsight SRA Input','value':s,'severity':'error'})
    r.raise_for_status()

def parse_channel(s):
    m = re.match(r'^(?:ch)?(\d+)$', s, flags=re.IGNORECASE)
    if not m:
        raise Exception, 'Invalid channel: {!r}'.format(s)
    return int(m.group(1))

def getCredentials(sessionKey):
   myapp = 'SA-FarsightWatchManager'
   try:
      # list all credentials
      entities = entity.getEntities(['admin','passwords'], namespace=myapp,
                                    owner='nobody', sessionKey=sessionKey)
   except Exception, e:
      raise Exception("Could not get %s credentials from splunk. Error: %s"
                      % (myapp, str(e)))

   # return first set of credentials
   for i, c in entities.items():
        if c['username'] == 'api_key':
                return c['clear_password']

   raise Exception("No credentials have been found")

def run():
    global_config = cli.getConfStanza('axamd','axamd')
    config = get_config()

    server = global_config.get("server")
    proxy = global_config.get("proxy")
    apikey = global_config.get("api_key")
    logging_uri = global_config.get("logging_uri")
    channels = [parse_channel(x.strip()) for x in config["channels"].split(',')]
    watches = [str(x.strip()) for x in config["watches"].split(',')]

    kwargs = {}
    if "timeout" in config:
        kwargs["timeout"] = float(config["timeout"])
    if "sample_rate" in config:
        kwargs["sample_rate"] = float(config["sample_rate"])/100
    if "rate_limit" in config:
        kwargs["rate_limit"] = int(config["rate_limit"])
    if "report_interval" in config:
        kwargs["report_interval"] = int(config["report_interval"])
    if "session_key" in config:
        sessionKey = config["session_key"]

    if len(sessionKey) == 0:
       sys.stderr.write("Did not receive a session key from splunkd. " +
           "Please enable passAuth in inputs.conf for this " +
           "script\n")
       exit(2)

    #Put this on hold until splunk gets credentials working reliably.
    #apikey = getCredentials(sessionKey)

    #force HTTPS
    logging_uri = logging_uri.replace("http://","")
    logging_uri = logging_uri.replace("https://","")
    logging_uri = "https://" + logging_uri + "/services/messages/new"
    server = "https://" + server

    c = Client(server, apikey, proxy=proxy)
    try:
        for line in c.sra(channels=channels, watches=watches, **kwargs):
            print "<stream><event><data>%s</data></event></stream>" % xml.sax.saxutils.escape(line.translate(None, "\x1e"))
    except ProblemDetails as e:
        logging.error("Caught AXAMD exception: %s" % (str(e)))
        make_error_message("Error in SRA input %s: %s" % (config["name"], str(e)), sessionKey, logging_uri)
    except ssl.SSLError as e:
        logging.error("Caught SSL exception: %s" % (str(e)))
        make_error_message("Error in RAD input %s: %s" % (config["name"], str(e) ), sessionKey, logging_uri)
    except Exception as e:
        logging.error("Caught exception: %s" % (str(e)))
        make_error_message("Error in RAD input %s: %s" % (config["name"], str(e) ), sessionKey, logging_uri)

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            do_scheme()
        elif sys.argv[1] == "--validate-arguments":
            config = get_validation_config()
        elif sys.argv[1] == "--test":
            print 'No tests for the scheme present'
            sys.exit(1)
        else:
            print 'Invalid argument(s)'
            sys.exit(1)
    else:
        # just request data from SRA
        run()

    sys.exit(0)

if __name__ == '__main__':
    main()
