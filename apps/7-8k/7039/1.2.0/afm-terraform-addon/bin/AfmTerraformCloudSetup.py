import splunk.rest
import json
import sys, os
#####
# REST endpoint setup, available on /setup (see restmap.conf)
#####

# Initialize Global Variables
APP_NAME = __file__.split(os.sep)[-3]
LOG_DIR  = os.path.join(os.environ["SPLUNK_HOME"], 'var', 'log', APP_NAME)
APP_DIR  = os.path.join(os.environ["SPLUNK_HOME"], 'etc', 'apps', APP_NAME)
LIB_DIR  = os.path.join(APP_DIR, 'bin', "lib")

# Add the "./lib" directory to sys.path to enable import on Custom Libraries
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
sys.path.append(os.path.join(os.path.dirname(__file__), "lib", "SplunkMgmt"))

from ConfigProperties import ConfigProperties
from SplunkInput import SplunkInput


class SetupHandler(splunk.rest.BaseRestHandler):

    def __init__(self, method, requestInfo, responseInfo, sessionKey):
        splunk.rest.BaseRestHandler.__init__(self, method, requestInfo, responseInfo, sessionKey)
        self.configProperties = ConfigProperties()
        self.splunkInput = SplunkInput()

    def writeJson(self, data):
        self.response.setStatus(200)
        self.response.setHeader('content-type', 'application/json')
        self.response.write(json.dumps(data))

    def handle_GET(self):
        config_dict = self.configProperties.get_config(config_format = ConfigProperties.FORMAT_JSON)
        self.writeJson(config_dict)

        # self.writeJson({ "message": "Hello World!" })

    def handle_POST(self):
        config_payload = json.loads(self.request["payload"])
        
        # Update the Config.properties file
        isUpdateSuccess = self.configProperties.update_config(config_payload, config_format = ConfigProperties.FORMAT_JSON)
        if not isUpdateSuccess:
            self.response.setStatus(500)
            self.response.write("Failed to update %s" % self.configProperties.CONFIG_NAME)
        
        # Update the Inputs.conf file
        isUpdateSuccess = self.splunkInput.update_config(config_payload, config_format = SplunkInput.FORMAT_JSON)
        if not isUpdateSuccess:
            self.response.setStatus(500)
            self.response.write("Failed to update %s" % self.splunkInput.CONFIG_NAME)

        # Return the config.properties Content
        config_dict = self.configProperties.get_config(config_format = ConfigProperties.FORMAT_JSON)
        self.writeJson(config_dict)
            
