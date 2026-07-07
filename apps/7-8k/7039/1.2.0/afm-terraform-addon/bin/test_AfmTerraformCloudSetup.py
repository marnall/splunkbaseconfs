import json
import sys, os
#####
# REST endpoint setup, available on /setup (see restmap.conf)
#####

# Initialize Global Variables
APP_NAME = __file__.split(os.sep)[-3]
LOG_DIR  = os.path.join(os.environ["SPLUNK_HOME"], 'var', 'log', APP_NAME)
APP_DIR  = os.path.join(os.environ["SPLUNK_HOME"], 'etc', 'apps', APP_NAME)
BIN_DIR  = os.path.join(APP_DIR, 'bin')
LIB_DIR  = os.path.join(APP_DIR, 'bin', "lib")

# Add the "./lib" directory to sys.path to enable import on Custom Libraries
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
sys.path.append(os.path.join(os.path.dirname(__file__), "lib", "SplunkMgmt"))

from ConfigProperties import ConfigProperties
from SplunkInput import SplunkInput

configProperties = ConfigProperties()
config_dict = configProperties.get_config(config_format = ConfigProperties.FORMAT_JSON)
print(json.dumps(config_dict))

# print({ "message": "Hello World!" })