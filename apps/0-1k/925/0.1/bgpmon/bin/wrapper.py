#!/usr/bin/env python

import os
import sys
import splunk.entity as entity


def getCredentials(sessionKey):
    myapp = 'bgpmon'
    try:
        # list all credentials
        entities = entity.getEntities(['admin', 'passwords'], namespace=myapp,
                                      owner='nobody', sessionKey=sessionKey)
    except Exception, e:
        raise Exception("Could not get %s credentials from splunk. Error: %s"
                              % (myapp, str(e)))
    # return first set of credentials
    for i, c in entities.items():
        return c['username'], c['clear_password']
    raise Exception("No credentials have been found")  


# read session key sent from splunkd
sessionKey = sys.stdin.readline().strip()
if len(sessionKey) == 0:
    sys.stderr.write("Did not receive a session key from splunkd. " +
    "Please enable passAuth in inputs.conf for this " +
    "script\n")
    exit(2)
# now get BgpMon credentials - might exit if no creds are available
login, passw = getCredentials(sessionKey)


NEW_PYTHON_PATH = '/usr/bin/python'

os.environ['PYTHONPATH'] = NEW_PYTHON_PATH
my_process = '/opt/splunk/etc/apps/bgpmon/bin/bgpMon.py'

os.execv(my_process, (login, passw))
