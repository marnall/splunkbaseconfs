from __future__ import print_function
from builtins import str
import glob
import os
import sys
import time
import xml.dom.minidom, xml.sax.saxutils
import logging
from datetime import date, timedelta, datetime

# set up logging suitable for splunkd comsumption
logging.root
logging.root.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(levelname)s %(message)s")
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)

SCHEME = """<scheme>
    <title>File Deleter</title>
    <description>Deletes files older than a certain age</description>
    <use_external_validation>false</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <endpoint>
        <args>
            <arg name="age">
                <title>Age</title>
                <description>Age in seconds before a file is deleted</description>
                <data_type>number</data_type>
                <required_on_create>true</required_on_create>
            </arg>
        </args>
    </endpoint>
</scheme>"""


def validate_conf(config, key):
    if key not in config:
        raise Exception(
            "Invalid configuration received from Splunk: key '%s' is missing." % key
        )


# Routine to get the value of an input
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
                        if (
                            param_name
                            and param.firstChild
                            and param.firstChild.nodeType == param.firstChild.TEXT_NODE
                        ):
                            data = param.firstChild.data
                            config[param_name] = data
                            logging.debug("XML: '%s' -> '%s'" % (param_name, data))

        checkpnt_node = root.getElementsByTagName("checkpoint_dir")[0]
        if (
            checkpnt_node
            and checkpnt_node.firstChild
            and checkpnt_node.firstChild.nodeType == checkpnt_node.firstChild.TEXT_NODE
        ):
            config["checkpoint_dir"] = checkpnt_node.firstChild.data

        if not config:
            raise Exception("Invalid configuration received from Splunk.")

    except Exception as e:
        raise Exception("Error getting Splunk configuration via STDIN: %s" % str(e))

    return config


# Routine to index data
def run_script():
    config = get_config()
    age = time.time() - int(config["age"])
    path = config["name"][9:]
    for f in glob.glob(path):
        if os.stat(f).st_mtime < age:
            logging.info(f"Deleting {f}")
            os.remove(f)
        else:
            logging.debug(f"Ignoring {f}")


# Script must implement these args: scheme, validate-arguments
if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            print(SCHEME)
        elif sys.argv[1] == "--validate-arguments":
            pass
        else:
            pass
    else:
        run_script()

    sys.exit(0)