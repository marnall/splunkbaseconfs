import os, traceback
import splunk.clilib.bundle_paths as bundle_paths
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from ConfigParser import ConfigParser
import codecs

APP_NAME = "OPTIC_Splunk_App"
APP_OWNER = "nobody"

DEFAULT_JOB_SEARCH_COUNT = 10000
DEFAULT_KVS_BATCH_SIZE = 300
DEFAULT_KVS_GET_LIMIT = 10000

def get_splunk_home():
    return make_splunkhome_path([''])

def get_app_home():
    return os.path.join(bundle_paths.get_base_path(), APP_NAME)

def get_upload_dir():
    return os.path.join(get_app_home(), "upload")

def get_working_dir():
    return os.path.join(get_app_home(), "tmp")

def get_lookup_dir():
    return os.path.join(get_app_home(), "lookups")

def get_conf_file():
    return os.path.join(get_working_dir(), "client.conf")

def get_platform():
    platform = os.uname()[0]
    if platform == "Linux":
        return 'linux'
    else:
        return 'macos'
    
def get_sample_events_dir():
    return os.path.join(get_app_home(), "bin/sample_events")

def get_iocdata_dir():
    return os.path.join(get_app_home(), "iocdata")

def get_samples_dir():
    return os.path.join(get_app_home(), "samples")

def get_csv_dir():
    return make_splunkhome_path(['var', 'run', 'splunk'])

def get_mgmt_port():
    web_default_config = make_splunkhome_path(['etc', 'system', 'default', 'web.conf'])
    web_config = make_splunkhome_path(['etc', 'system', 'local', 'web.conf'])
    config = ConfigParser()
    try:
        if os.path.exists(web_default_config):
            with codecs.open(web_default_config, 'r', 'utf_8_sig') as fhandler:
                config.readfp(fhandler)
        if os.path.exists(web_config):
            with codecs.open(web_config, 'r', 'utf_8_sig') as fhandler:
                config.readfp(fhandler)
    except Exception as e:
        print(traceback.format_exc())
    mgmt_port = "localhost:8089"
    try:
        mgmt_port = config.get("settings", "mgmtHostPort")
    except Exception as e:
        print(traceback.format_exc())
    port = 8089
    try:
        port = int(mgmt_port.split(":")[1])
    except Exception as e:
        print(e)
    return port

def get_backfill_checkpoint():
    return os.path.join(get_working_dir(),".backfill_checkpoint")
