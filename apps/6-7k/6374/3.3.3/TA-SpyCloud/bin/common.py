""" common.py

Common functions used across both inputs.

"""
from datetime import datetime
import logging
import re
import sys

from consts import APP_NAME
from splunklib.client import connect # pylint: disable=import-error
import splunk.rest

def check_api_key(helper, filename):
    api_key = helper.get_global_setting('spycloud_key')
    if api_key == "":
        message = "SpyCloud API Key is either Invalid or Empty" 
        make_error_message(helper, message, filename)
        sys.exit(0)   

def checkpoint_cleanup(checkpoint):
    """ Expire off documents which were ingested more than 3 days before the last run date """
    last_run_dt = datetime.strptime(checkpoint["last_run"], "%Y-%m-%d")
    output = checkpoint
    output["last_run"] = date_stamp()
#    for document_id in checkpoint["documents"].keys():
#        document_time_str = checkpoint["documents"][document_id]
#        document_time_dt = datetime.strptime(document_time_str, "%Y-%m-%d")
#        if (last_run_dt - document_time_dt).days > 3:
#            del output["documents"][document_id]
    return output

def date_stamp():
    """ Returns current date in yyyy-mm-dd format. """
    now = datetime.now()
    return datetime.strftime(now, "%Y-%m-%d")

def make_error_message(helper, message, filename):
    """ Generates Splunk error message """
    session_key = helper.context_meta['session_key'] 
    helper.log_debug("session_key=" + str(session_key))
    helper.log_error(message)
    splunk.rest.simpleRequest(
        '/services/messages/new',
        postargs={'name': helper.get_app_name(), 'value': '{} - {}'.format(filename, message),  # pylint: disable=consider-using-f-string
                  'severity': 'error'}, method='POST', sessionKey=session_key
    )


def make_error_message_with_session(session_key, message, filename):
    """Generates Splunk error message when no helper object is available."""
    logging.error(message)
    splunk.rest.simpleRequest(
        '/services/messages/new',
        postargs={'name': APP_NAME, 'value': '{} - {}'.format(filename, message),  # pylint: disable=consider-using-f-string
                  'severity': 'error'}, method='POST', sessionKey=session_key
    )

def newer_timestamp(checkpoint, timestamp):
    """ Check if timestamp is newer """
    checkpoint = checkpoint.split('T')[0]
    timestamp = timestamp.split('T')[0]
    checkpoint_dt = datetime.strptime(checkpoint, '%Y-%m-%d')
    timestamp_dt = datetime.strptime(timestamp, '%Y-%m-%d')
    return bool(timestamp_dt > checkpoint_dt)

"""

Functions used by version 1.5

"""

def get_session_key():
    """
    Grabs session key from first line of stdin
    """
    first_line = sys.stdin.readline().strip()
    session_key = re.sub(r'sessionKey=', "", first_line)
    if session_key is None or session_key == "":
        sys.stderr.write("Please provide a session key for this input to work properly\n")
        sys.exit(0)
    else:
        return session_key


def get_credentials(session_key):
    """
    Retrieves credentials from encrypted credential store.
    """
    service = connect(token=session_key, owner='nobody', app=APP_NAME)
    passwords = service.storage_passwords
    if "spycloud_key" in passwords:
        api_key = passwords["spycloud_key"].clear_password
    else:
        message = 'No credentials have been found. Please configure SpyCloud first.'
        make_error_message_with_session(session_key, message, 'common.py')
        api_key = None
    return api_key

