"""
common.py

Extracts creds from a custom conf file created by setup.xml

"""

import logging
import splunk.entity as entity  # pylint: disable=import-error


def get_credentials(session_key): # pylint: disable=inconsistent-return-statements
    """ Gets encrypted credentials from Splunk conf file """
    my_app = 'TA-detectify'
    try:
        # list all credentials
        entities = entity.getEntities(['admin', 'passwords'],
                                      namespace=my_app, owner='nobody', sessionKey=session_key)
    except Exception as err:
        raise Exception("Could not get %s credentials from splunk. Error: %s" % (my_app, str(err)))

    # return first set of credentials
    last = None
    for idx, conf in entities.items():  # pylint: disable=unused-variable
        if conf['eai:acl']['app'] == my_app:
            last = conf['username'], conf['clear_password']
    if last:
        return last


def make_error_message(message, session_key, filename):
    """ Generates Splunk error message """
    logging.error(message)
    entity.rest.simpleRequest(
        '/services/messages/new',
        postargs={'name': 'TA-detectify', 'value': '%s - %s' % (filename, message),
                  'severity': 'error'}, method='POST', sessionKey=session_key
    )
