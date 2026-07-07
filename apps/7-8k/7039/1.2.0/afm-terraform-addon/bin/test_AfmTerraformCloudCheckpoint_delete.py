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

splunkCheckpoint = SplunkCheckpoint('sample.conf', SplunkCheckpoint.CHECKPOINT_DIR)

splunkCheckpoint.delete_checkpoint()
print(json.dumps({ "message": "Checkpoints Successfully Deleted" }))
