import os
import platform

APP_NAME = "sap_solman_app"
DEFAULT_SPLUNK_PATHS = {'Windows': 'C:\Program Files\Splunk', 'Linux': '/opt/splunk'}

def get_addon_path():
    app_dir = os.path.join(os.environ.get('SPLUNK_HOME', DEFAULT_SPLUNK_PATHS[platform.system()]),'etc','apps', APP_NAME)
    return app_dir