import os
import configparser
from uuid import uuid4

from constants import (
    SPLUNK_INSTANCE_CONFIG_FILE,
    SPLUNK_INSTANCE_CONFIG_FOLDER
)


def get_splunk_main_path():
    path = __file__
    while os.path.basename(path) != SPLUNK_INSTANCE_CONFIG_FOLDER:
        path = os.path.dirname(path)
    return os.path.join(path, SPLUNK_INSTANCE_CONFIG_FILE)


def get_splunk_guid():
    config = configparser.ConfigParser()
    config.read(get_splunk_main_path())
    try:
        guid = config['general']['guid']
    except KeyError:
        guid = str(uuid4())
    return guid
