"""
common.py
Helper file containing useful methods
"""
import splunk.entity as entity

def getCredentials(sessionKey):
    """
    Checks for existence of API key and returns it if available
    :param sessionKey:
    :return: API Key
    """
    myapp = 'SA-shodan'
    try:
        # list all credentials
        entities = entity.getEntities(['admin', 'passwords'], namespace=myapp, owner='nobody', sessionKey=sessionKey)
    except Exception, e:
        raise Exception("Could not get %s credentials from splunk. Error: %s" % (myapp, str(e)))

    # return first set of credentials
    last = None
    for c in entities.values():
        if c['eai:acl']['app'] == myapp:
            last = c['username'], c['clear_password']
    if last:
        return last

    raise Exception("No credentials have been found. Please configure SA-shodan first.")
