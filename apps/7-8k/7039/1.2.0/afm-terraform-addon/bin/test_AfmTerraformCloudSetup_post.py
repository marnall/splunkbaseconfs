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

payload = json.dumps({
  "input-1": {
    "protocol": "https",
    "terraform_host": "app.terraform.io",
    "token": "sample_token_1",
    "workspace_id": "workspace_1",
    "index": "afm_terraform_cloud_idx",
    "interval": "500",
    "sourcetype": "_json",
    "disabled": "0"
  },
  "input-2": {
    "protocol": "https",
    "terraform_host": "app.terraform.io",
    "token": "sample_token_2",
    "workspace_id": "workspace_2",
    "index": "afm_terraform_cloud_idx",
    "interval": "500",
    "sourcetype": "_json",
    "disabled": "0"
  }
})
config_payload = json.loads(payload)

configProperties = ConfigProperties()
splunkInput = SplunkInput()

# Update the Config.properties file
isUpdateSuccess = configProperties.update_config(config_payload, config_format = ConfigProperties.FORMAT_JSON)
if not isUpdateSuccess:
    print("Failed to update %s" % configProperties.CONFIG_NAME)

# Update the Inputs.conf file
isUpdateSuccess = splunkInput.update_config(config_payload, config_format = SplunkInput.FORMAT_JSON)
if not isUpdateSuccess:
    print("Failed to update %s" % splunkInput.CONFIG_NAME)

# Return the config.properties Content
config_dict = configProperties.get_config(config_format = ConfigProperties.FORMAT_JSON)
print(json.dumps(config_dict))