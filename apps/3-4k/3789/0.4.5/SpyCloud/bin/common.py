""" common.py

Common functions used across both inputs.

"""
import datetime
import logging
import re
import sys

import splunk.entity as entity
import splunk.rest


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
    myapp = 'SpyCloud'
    try:
        # list all credentials
        entities = entity.getEntities(
            ['admin', 'passwords'], namespace=myapp, owner='nobody', sessionKey=session_key
        )
    except Exception as unknown_exception:
        raise Exception("Could not get %s credentials from splunk. Error: %s"
                        % (myapp, str(unknown_exception)))

    # grab first set of credentials
    last = None
    timestamp = 0
    api_key = None
    for stanza in entities.values():
        if stanza['eai:acl']['app'] == myapp:
            time = stanza['username'].split('spycloud')[1]
            if time > timestamp:
                last = stanza['username'], stanza['clear_password']
                timestamp = time
    if last:
        # username is not needed
        api_key = last[1]
    else:
        message = 'No credentials have been found. Please configure SpyCloud first.'
        make_error_message(message, session_key, 'common.py')
        sys.exit(0)
    return api_key


def make_error_message(message, session_key, filename):
    """ Generates Splunk error message """
    logging.error(message)
    splunk.rest.simpleRequest(
        '/services/messages/new',
        postargs={'name': 'SpyCloud', 'value': '%s - %s' % (filename, message),
                  'severity': 'error'}, method='POST', sessionKey=session_key
    )


def newer_timestamp(checkpoint, timestamp):
    """ Check if timestamp is newer """
    checkpoint = checkpoint.split('T')[0]
    timestamp = timestamp.split('T')[0]
    checkpoint_dt = datetime.datetime.strptime(checkpoint, '%Y-%m-%d')
    timestamp_dt = datetime.datetime.strptime(timestamp, '%Y-%m-%d')
    return bool(timestamp_dt > checkpoint_dt)
