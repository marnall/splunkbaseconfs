import logging.handlers
import os

import requests
import splunk
import splunk.entity as en

from constants import (
    FIELD_ACCESS_TOKEN, FIELD_CLIENT_ID, FIELD_CLIENT_SECRET, OWNER, NAMESPACE,
    SIGNIN_URL)


def get_encrypted_value(field_name, session_key):
    try:
        entity = en.getEntity(
            'storage/passwords',
            field_name,
            owner=OWNER,
            namespace=NAMESPACE,
            sessionKey=session_key,
        )
    except splunk.ResourceNotFound:
        return ''
    return entity['clear_password']


def store_encrypted_value(field_name, value, session_key):
    entity = en.Entity(
        'storage/passwords',
        field_name,
        {'password': value},
        owner=OWNER,
        namespace=NAMESPACE,
    )
    en.setEntity(entity, session_key)


def get_access_token(session_key, lookup_local_first=True):
    if lookup_local_first:
        value = get_encrypted_value(FIELD_ACCESS_TOKEN, session_key)
        if value:
            return value
    client_id = get_encrypted_value(FIELD_CLIENT_ID, session_key)
    client_secret = get_encrypted_value(FIELD_CLIENT_SECRET, session_key)
    sign_in_data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
    }
    response = requests.post(SIGNIN_URL, sign_in_data)
    value = response.json().get('access_token')
    if value:
        store_encrypted_value(FIELD_ACCESS_TOKEN, value, session_key)
    return value


def setup_logger():
    logger = logging.getLogger('avanan')
    SPLUNK_HOME = os.environ['SPLUNK_HOME']

    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = "avanan.log"
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
    splunk_log_handler = logging.handlers.RotatingFileHandler(
        os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a')
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
    return logger


logger = setup_logger()
