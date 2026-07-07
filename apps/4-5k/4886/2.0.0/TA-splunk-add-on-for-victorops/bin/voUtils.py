#
# Common VictorOps functions used by victorops.py and recoverAlerts.py
#
from __future__ import absolute_import
from __future__ import print_function
import os
import sys
import json
import csv
import gzip
import re
import time
import hashlib
try:
    # For Python 3.0 and later
    from urllib.request import urlopen, ProxyHandler, HTTPBasicAuthHandler, build_opener, install_opener, Request
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import urlopen, ProxyHandler, HTTPBasicAuthHandler, build_opener, install_opener, Request
try:
    from urllib.error import HTTPError
except ImportError:
    from urllib2 import HTTPError

from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'TA-splunk-add-on-for-victorops', 'lib']))

import splunklib.client as client
import splunk.rest
from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.clilib import cli_common as cli

myapp = 'TA-splunk-add-on-for-victorops'
proxy_collection_name = 'TA_splunk_add_on_for_victorops_proxyconfig'

svc = None;
def getService(sessionKey,app):
    global svc;
    if svc == None:
        # Get mgmt host and port from web.conf
        cfg = cli.getConfStanza('web','settings');
        hostAndPortStr = cfg.get('mgmtHostPort');
        hostAndPortArr = hostAndPortStr.split(':');
        svc = client.Service(token=sessionKey, app=app, host=hostAndPortArr[0], port=hostAndPortArr[1]);

    return svc;

#
# Method to configure web proxy settings if a proxy is configured.
#
def getWebProxyConfig(sessionKey):

    service = getService(sessionKey, myapp)
    query = json.dumps({})
    collection = service.kvstore[proxy_collection_name]

    protocol = '';
    host = '';
    port = -1;
    user = '';
    proxyPass = '';

    if proxy_collection_name in service.kvstore:
        result = None;
        try:
            result = collection.data.query(query=query);
            if len(result) > 0:
                # This will find the optional proxy password.
                protocol = result[0]['protocol'];
                host = result[0]['host'];
                port = str(result[0]['port']);
                user = result[0]['user'];
                #if len(user) > 0:
                #    proxyPass = getApiKey (sessionKey,result[0]['_key']);
        except Exception as e:
            raise e

    return { "protocol": protocol, "host": host, "port": port, "user": user, "pass": proxyPass};

def getSystemSessionKey(sessionKey):
    keyEndpoint = '/vo_sess_key'
    keyResponse, keyContent = splunk.rest.simpleRequest (keyEndpoint, method='GET', sessionKey=sessionKey, raiseAllErrors=False)
    return keyContent.decode('ASCII')

#
# Retrieve app version from $SPLUNK_HOME/etc/apps/TA-splunk-add-on-for-victorops/default/app.conf
#
def getAppVersion():
    version = 'unknown';
    appConfFile = os.path.normpath(os.environ.get("SPLUNK_HOME") + '/etc/apps/TA-splunk-add-on-for-victorops/default/app.conf');
    with open(appConfFile) as propertyFile:
        for line in propertyFile:
            propname, propval = line.partition("=")[::2]
            if propname.strip() == 'version':
                version = propval[:-1]
                return version;
    return version;
#
# Retrieve splunk version from $SPLUNK_HOME/etc/splunk.version
#
def getSplunkVersion():
    version = 'unknown';
    splunkFile = os.path.normpath(os.environ.get("SPLUNK_HOME") + '/etc/splunk.version');
    with open(splunkFile) as propertyFile:
        for line in propertyFile:
            propname, propval = line.partition("=")[::2]
            if propname.strip() == 'VERSION':
                version = propval[:-1]
                return version;
    return version;

#
# Generate an MD5 hash of the data
# This is a workaround for the usedforsecurity parameter in Python 3.9+
# which is not available on all platforms.
#
# Note: usedforsecurity=False will not be used for security purposes.
# It is just to get the same behavior as before Python 3.9.
#
def md5_compat(data):
    if sys.version_info >= (3, 9):
        return hashlib.md5(data.encode('utf-8'), usedforsecurity=False).hexdigest()
    else:
        return hashlib.md5(data.encode('utf-8')).hexdigest()
