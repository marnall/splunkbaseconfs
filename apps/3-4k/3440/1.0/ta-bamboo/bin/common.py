# Exports stuff to the rest of the files.
import ConfigParser
import logging
import os

import splunk.Intersplunk as isp
import splunk.bundle as sb

# FIXME: What to do if $SPLUNK_HOME is not set?
splunk_home = os.environ.get('SPLUNK_HOME')

if splunk_home is not None:
    path_to_app = splunk_home + "/etc/apps/ta-bamboo"
    # Note: Just calling python from inside a modular input
    # also seems to invoke the splunk python.
    splunk_python_path = splunk_home + "/bin/python"

path_to_exec = path_to_app + "/bin/get_events.py"

# Path to file where we will be logging everything
logging_file_path = path_to_app + "/bamboo.log"
logging.basicConfig(filename=logging_file_path, level=logging.DEBUG)

# FIXME: should the private.pem file be encrypted? I don't think it is required because
# we can create this rsa private-public pair just for accessing bamboo,
# and not use it for any other accounts.

rsa_filename = splunk_home + '/etc/apps/ta-bamboo/private.pem'

# Will save it there in json format (json.dumps of a dictionary object)
# just define this in Bamboo Input Helper.
# recovery_time_filename = path_to_app + '/recovery'


# For developing - so we can keep running API every minute, but not overloading
# the Bamboo server:

develop_mode = True

# Gets the data about previous builds as well as the latest build.
# Using it now because we aren't running the script all the time in
# order to keep the load less on app-tester.
history_mode = False


def getSplunkConf():
    results, dummyresults, settings = isp.getOrganizedResults()
    namespace = settings.get("namespace", None)
    owner = settings.get("owner", None)
    sessionKey = settings.get("sessionKey", None)

    conf = sb.getConf('bamboo', namespace=namespace, owner=owner, sessionKey=sessionKey)
    stanza = conf.get('bamboo')

    return stanza


def getLocalConf():
    local_conf = ConfigParser.ConfigParser()
    location = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
    local_conf.read(location + '/config.ini')

    return local_conf


def flatten(item, keys):
    response = {}
    for (key, replacer) in keys:
        if not replacer:
            response[key] = str(item[key])
        else:
            response[key] = replacer.get(item[key], item[key])

    return response


def api_to_dict(apidata):
    dictdata = {}
    for item in apidata:
        dictdata[item['id']] = item['name']
    return dictdata


LOG_FILENAME = os.path.join(os.environ.get('SPLUNK_HOME'),
                            'var', 'log', 'splunk',
                            'bamboo.log')
logger = logging.getLogger('bamboo')
logger.setLevel(logging.DEBUG)
handler = logging.handlers.RotatingFileHandler(LOG_FILENAME,
                                               maxBytes=5124800,
                                               backupCount=4)
f = logging.Formatter("%(asctime)s %(levelname)s %(lineno)d %(message)s")
handler.setFormatter(f)
handler.setLevel(logging.INFO)
logger.addHandler(handler)
