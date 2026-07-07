#
# Common Incident Intelligence functions used by incident intelligence actions
#
from __future__ import absolute_import
from __future__ import print_function

# encoding = utf-8
# Always put this line at the beginning of this file
import incident_intelligence_declare

import os
import json
import sys

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

import splunklib.client as client
import splunk.rest
from splunk.clilib import cli_common as cli

myapp = 'splunk_incident_intelligence_app'
collection_name = 'incident_intelligence_collection'
proxy_collection_name = 'proxyconfig'
svc = None


def get_service(session_key, app, logger):
    global svc
    if svc is None:
        # Get mgmt host and port from web.conf
        cfg = cli.getConfStanza('web', 'settings')
        hostAndPortStr = cfg.get('mgmtHostPort')
        logger.info('mgmtHostPort: ' + hostAndPortStr)
        hostAndPortArr = hostAndPortStr.rsplit(':', 1)
        # In case of ipv6, remove the brackets for service
        hostAndPortArr[0] = hostAndPortArr[0].replace("[", "")
        hostAndPortArr[0] = hostAndPortArr[0].replace("]", "")
        logger.info('Using Management Host And Port: ' + repr(hostAndPortArr))
        svc = client.Service(token=session_key, app=app, host=hostAndPortArr[0], port=hostAndPortArr[1])

    return svc


#
# Retrieve app version from $SPLUNK_HOME/etc/apps/splunk_incident_intelligence_app/default/app.conf
#
def get_app_version():
    version = 'unknown'
    app_conf_file = os.path.normpath(os.environ.get("SPLUNK_HOME") + '/etc/apps/' + myapp + '/default/app.conf')
    with open(app_conf_file) as propertyFile:
        for line in propertyFile:
            propname, propval = line.partition("=")[::2]
            if propname.strip() == 'version':
                version = propval[:-1]
                return version
    return version


#
# Retrieve splunk version from $SPLUNK_HOME/etc/splunk.version
#
def get_splunk_version():
    version = 'unknown'
    splunk_file = os.path.normpath(os.environ.get("SPLUNK_HOME") + '/etc/splunk.version')
    with open(splunk_file) as propertyFile:
        for line in propertyFile:
            propname, propval = line.partition("=")[::2]
            if propname.strip() == 'VERSION':
                version = propval[:-1]
                return version
    return version


#
# Retrieve an SFX token's value from the KVStore using keyId (i.e. _key) of the key to retrieve.
#
def get_sfx_token_from_password(session_key, key_id, logger):

    logger.info('Looking up SFX token from storage/passwords for recordId: ' + str(key_id))
    passwd_endpoint = '/servicesNS/nobody/' + myapp + '/storage/passwords/:' + str(key_id).rstrip() + \
                      ':?output_mode=json'
    # Will throw exception if not found.
    passwd_response, passwd_content = splunk.rest.simpleRequest(passwd_endpoint, method='GET', sessionKey=session_key,
                                                                raiseAllErrors=False)
    tmp = json.loads(passwd_content)
    sfx_token = tmp['entry'][0]['content']['clear_password']
    return sfx_token


#
# Retrieve an SFX Token's value from the KVStore using the org_id of the key to retrieve.
#
def get_key_by_id(session_key, org_id, logger):

    service = get_service(session_key, myapp, logger)
    query = json.dumps({"org_id": org_id})
    collection = service.kvstore[collection_name]

    if collection_name in service.kvstore:
        result = None
        try:
            result = collection.data.query(query=query)
            if len(result) > 0:
                logger.info('Found SFX token by org_id: ' + org_id)
                sfx_token = get_sfx_token_from_password(session_key, result[0]['_key'], logger)
                return [sfx_token]
            else:
                logger.error('Failed to find key by org_id: ' + org_id)
                return ['', '']

        except Exception as e:
            logger.error(e)
            raise Exception('Record with name: ' + org_id + ' not found!')


#
# Retrieve the api key marked as default from the KVStore
#
def get_default_sfx_token(session_key, logger):

    service = get_service(session_key, myapp, logger)
    service.login()

    query = json.dumps({"is_default": "true"})
    collection = service.kvstore[collection_name]

    # Lookup default key from the KV store.
    if collection_name in service.kvstore:
        result = None
        try:
            result = collection.data.query(query=query)

            if len(result) > 0:
                logger.info('Found default SFX token')
                # Retrieve the actual API key from the storage/passwords endpoint.
                key_id = result[0]['_key']
                sfx_token = get_sfx_token_from_password(session_key, key_id, logger)
                return [sfx_token]
            else:
                logger.error('Default key not found!')
                return ['', '']

        except Exception as e:
            logger.error(e)
            raise Exception('Default key record not found!')


#
# Method to configure web proxy settings if a proxy is configured.
#
def get_web_proxy_config(session_key, logger):

    logger.info('Entering get_web_proxy_config')
    service = get_service(session_key, myapp, logger)
    query = json.dumps({})
    collection = service.kvstore[proxy_collection_name]

    protocol = ''
    host = ''
    port = -1
    user = ''
    proxy_pass = ''

    if collection_name in service.kvstore:
        result = None
        try:
            result = collection.data.query(query=query)
            if len(result) > 0:
                logger.info('Found Proxy configuration.')
                # This will find the optional proxy password.
                protocol = result[0]['protocol']
                host = result[0]['host']
                port = str(result[0]['port'])
                user = result[0]['user']
                if len(user) > 0:
                    proxy_pass = get_sfx_token_from_password(session_key, result[0]['_key'], logger)

                logger.info("proxy_settings: proxy_type={}, proxy_url={}, proxy_port={}, proxy_username={}".
                            format(protocol, host, port, user))
                return {"proxy_type": protocol, "proxy_url": host, "proxy_port": port, "proxy_username": user,
                        "proxy_password": proxy_pass}
            else:
                logger.info('Proxy configuration not found.')
        except Exception as e:
            logger.error('Error retrieving proxy configuration')
            logger.error(e)
    else:
        logger.info('ProxyConfig collection not found in KV store!')
    return {}


def unquote(s):
    """unquote('abc%20def') -> 'abc def'."""
    mychr = chr
    myatoi = int
    list = s.split('%')
    res = [list[0]]
    myappend = res.append
    del list[0]
    for item in list:
        if item[1:2]:
            try:
                myappend(mychr(myatoi(item[:2], 16))
                     + item[2:])
            except ValueError:
                myappend('%' + item)
        else:
            myappend('%' + item)
    return "".join(res)


# Internal method to read command header from splunk.
def get_settings(input_buf):

    settings = {}
    # get the header info
    input_buf = sys.stdin
    # until we get a blank line, read "attr:val" lines, setting the values in 'settings'
    attr = last_attr = None
    while True:
        line = input_buf.readline()
        line = line[:-1] # remove lastcharacter(newline)
        if len(line) == 0:
            break

        colon = line.find(':')
        if colon < 0:
            if last_attr:
                settings[attr] = settings[attr] + '\n' + unquote(line)
            else:
                continue

        # extract it and set value in settings
        last_attr = attr = line[:colon]
        val  = unquote(line[colon+1:])
        settings[attr] = val

    return settings
