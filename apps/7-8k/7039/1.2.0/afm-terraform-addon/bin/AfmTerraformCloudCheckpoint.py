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

from SplunkCheckpoint import SplunkCheckpoint


class SetupHandler(splunk.rest.BaseRestHandler):

    def __init__(self, method, requestInfo, responseInfo, sessionKey):
        splunk.rest.BaseRestHandler.__init__(self, method, requestInfo, responseInfo, sessionKey)
        self.splunkCheckpoint = SplunkCheckpoint('sample.conf', SplunkCheckpoint.CHECKPOINT_DIR)

    def writeJson(self, data):
        self.response.setStatus(200)
        self.response.setHeader('content-type', 'application/json')
        self.response.write(json.dumps(data))

    def handle_DELETE(self):
        self.splunkCheckpoint.delete_checkpoint()
        self.writeJson({ "message": "Checkpoints Successfully Deleted" })
            
