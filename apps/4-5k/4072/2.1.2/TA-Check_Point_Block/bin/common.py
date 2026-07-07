"""
common.py

Extracts creds from a custom conf file created by setup.xml

"""

import splunk.entity as entity # pylint: disable=import-error, consider-using-from-import


def get_credentials(session_key):
    """ Gets encrypted credentials from Splunk conf file """
    my_app = 'TA-Check_Point_Block'
    try:
        # list all credentials
        entities = entity.getEntities(['admin', 'passwords'],
                                      namespace=my_app, owner='nobody',
                                      sessionKey=session_key)
    except Exception as err:
        raise Exception (f"Could not get {my_app} credentials from Splunk. Error: {str(err)}")  # pylint: disable=raise-missing-from,broad-exception-raised

    # return first set of credentials
    last = None
    for idx, conf in entities.items(): # pylint: disable=unused-variable
        if conf['eai:acl']['app'] == my_app:
            if conf['username'] is None:
                username = ''
            else:
                username = conf['username']
            if conf['clear_password'] is None:
                clear_password = '' # nosec
            else:
                clear_password = conf['clear_password']
            last = username, clear_password
    if last:
        return last

    raise Exception("No credentials have been found." # pylint: disable=broad-exception-raised
                    " Please configure TA-Check_Point_Block first.")
