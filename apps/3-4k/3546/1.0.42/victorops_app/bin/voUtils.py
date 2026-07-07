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
sys.path.append(make_splunkhome_path(['etc', 'apps', 'victorops_app', 'lib']))

import splunklib.client as client
import splunk.rest
from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.clilib import cli_common as cli

myapp = 'victorops_app'
collection_name = 'mycollection'
data_collection_name = 'dataconfig'
proxy_collection_name = 'proxyconfig'
active_alerts_collection_name = 'activealerts'

svc = None;
def getService(sessionKey,app,logger):
    global svc;
    if svc == None:
        # Get mgmt host and port from web.conf
        cfg = cli.getConfStanza('web','settings');
        hostAndPortStr = cfg.get('mgmtHostPort');
        logger.info('mgmtHostPort: ' + hostAndPortStr);
        hostAndPortArr = hostAndPortStr.rsplit(':',1);
        # In case of ipv6, remove the brackets for service
        hostAndPortArr[0] = hostAndPortArr[0].replace("[","")
        hostAndPortArr[0] = hostAndPortArr[0].replace("]","")
        logger.info('Using Management Host And Port: ' + repr(hostAndPortArr));
        svc = client.Service(token=sessionKey, app=app, host=hostAndPortArr[0], port=hostAndPortArr[1]);

    return svc;
#
# Retrieve app version from $SPLUNK_HOME/etc/apps/victorops_app/default/app.conf
#
def getAppVersion():
    version = 'unknown';
    appConfFile = os.path.normpath(os.environ.get("SPLUNK_HOME") + '/etc/apps/' + myapp + '/default/app.conf');
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
# Retrieve an API key's value from the KVStore using recordId (i.e. _key) of the key to retrieve.
#
def getApiKey(sessionKey,recordId,logger):

    systemKey = getSystemSessionKey(sessionKey, logger)
    #logger.info('systemKey='+systemKey)

    logger.info('Looking up API key from storage/passwords for recordId: ' + str(recordId));
    passwdEndpoint = '/servicesNS/nobody/' + myapp + '/storage/passwords/:' + str(recordId).rstrip() + ':?output_mode=json'
    # Will throw exception if not found.
    passwdResponse, passwdContent = splunk.rest.simpleRequest (passwdEndpoint, method='GET', sessionKey=systemKey, raiseAllErrors=False)
    #passwdResponse, passwdContent = splunk.rest.simpleRequest (passwdEndpoint, method='GET', sessionKey=sessionKey, raiseAllErrors=False)
    tmp = json.loads(passwdContent)
    api_key = tmp['entry'][0]['content']['clear_password']
    return api_key;

#
# Retrieve an API key's value from the KVStore using the name of the key to retrieve.
#
def getKeyByName(sessionKey,name,logger):

    service = getService(sessionKey, myapp, logger)
    query = json.dumps({"org_name": name})

    collection = service.kvstore[collection_name]

    if collection_name in service.kvstore:

        result = None;
        try:
            result = collection.data.query(query=query);

            if len(result) > 0:
                logger.info('Found API key by name: ' + name);
                apiKey = getApiKey (sessionKey,result[0]['_key'],logger);
                routingKey = result[0]['routing_key'];
                return [apiKey,routingKey];
            else:
                logger.error('Failed to find key by name: ' + name);
                return ['',''];

        except Exception as e:
            logger.error(e);
            raise Exception('Record with name: ' + name + ' not found!');

def getInternalKey(sessionKey,apiKey,logger):
    service = getService(sessionKey, myapp, logger)
    query = json.dumps({"org_name": "<internal>", "api_key": apiKey})

    collection = service.kvstore[collection_name]

    if collection_name in service.kvstore:

        result = None;
        try:
            result = collection.data.query(query=query);

            if len(result) > 0:
                logger.info('Found Internal API key: ' + maskUrl(apiKey));
                apiKey = getApiKey (sessionKey,result[0]['_key'],logger);
                routingKey = result[0]['routing_key'];
                return result[0]['_key']
            else:
                logger.info('Failed to find internal key: ' + maskUrl(apiKey));
                return ''

        except Exception as e:
            logger.error(e);
            raise Exception('Record with apiKey: ' + maskUrl(apiKey) + ' not found!');

#
# Retrieve the api key marked as default from the KVStore
#
def getDefaultKey(sessionKey,logger):

    service = getService(sessionKey, myapp, logger)
    service.login()

    query = json.dumps({"is_default": "true"})
    collection = service.kvstore[collection_name]

    # Lookup default key from the KV store.
    if collection_name in service.kvstore:

       result = None;
       try:
           result = collection.data.query(query=query);

           if len(result) > 0:
               logger.info('Found default API key');
               # Retrieve the actual API key from the storage/passwords endpoint.
               apiKeyId = result[0]['_key'];
               apiKey = getApiKey(sessionKey,apiKeyId,logger);
               routingKey = result[0]['routing_key'];
               return [apiKey,routingKey];
           else:
               logger.error('Default key not found!');
               return ['',''];

       except Exception as e:
           logger.error(e);
           raise Exception('Default key record not found!');

#
# Retrieve the api and routing key of the specified key entry identified recordId, name, or default key
# if neither is specified.
#
def getCredentials(sessionKey,recordId,name,logger):

    logger.info('getCreds recordId: [' + recordId + '], name: [' + name + ']');

    if len(recordId) == 0 and len(name) == 0:
        logger.info('Doing default API key lookup.');
        return getDefaultKey(sessionKey,logger);
    elif len(name) > 0:
        logger.info('Doing API key lookup by name: ' + name);
        return getKeyByName(name,logger);

    if recordId == '-1':
        return ['',''];

    # Find by _key (recordId)
    logger.info('Doing API key lookup for record_id: ' + recordId);
    service = getService(sessionKey, myapp, logger)
    service.login()

    # set the kvstore collection with api key values
    collection = service.kvstore[collection_name]

    if collection_name in service.kvstore:
        try:
            result = collection.data.query_by_id(recordId);
            apiKey = getApiKey(sessionKey,result['_key'],logger);
            routingKey = result['routing_key'];
            return [apiKey,routingKey];
        except Exception as e:
            logger.error(e)
            logger.error("Did not find API key by recordId " + recordId + " - falling back to default")
        try:
            return getDefaultKey(sessionKey, logger)
        except Exception as ex:
            logger.error("Failed to fall back to default API key.")
            logger.error(ex);
            raise Exception('Record with key: ' + recordId + ' not found!')

    else:
        raise Exception('Collection: ' + collection_name + ' not found!');

#
# Retrieve an API key's value from the KVStore using the name of the key to retrieve.
#
def getDataKeyByName(sessionKey,name,logger):

    service = getService(sessionKey, myapp, logger)
    query = json.dumps({"name": name})

    collection = service.kvstore[data_collection_name]

    if data_collection_name in service.kvstore:

        result = None;
        try:
            result = collection.data.query(query=query);

            if len(result) > 0:
                logger.info('Found Data key by name: ' + name);
                apiId = result[0]['api_id'];
                name = result[0]['name'];
                apiKey = getApiKey (sessionKey,result[0]['_key'],logger);
                return [name,apiId,apiKey];
            else:
                logger.error('Failed to find key by name: ' + name);
                return ['','',''];

        except Exception as e:
            logger.error(e);
            raise Exception('Record with name: ' + name + ' not found!');


#
# Retrieve the api key marked as default from the KVStore
#
def getDefaultDataKey(sessionKey,logger):
    service = getService(sessionKey, myapp, logger)
    service.login()

    query = json.dumps({"is_default": "true"})
    collection = service.kvstore[data_collection_name]

    # Lookup default key from the KV store.
    if data_collection_name in service.kvstore:

       result = None;
       try:
           result = collection.data.query(query=query);
           if len(result) > 0:
               logger.info('Found default Data API key');
               # Retrieve the actual API key from the storage/passwords endpoint.
               apiKeyId = result[0]['_key'];
               #logger.info("apiKeyId="+apiKeyId)
               apiKey = getApiKey (sessionKey,apiKeyId,logger);
               apiId = result[0]['api_id'];
               name = result[0]['name'];
               return [name,apiId,apiKey];
           else:
               logger.error('Default Data key not found!');
               return ['','',''];

       except Exception as e:
           logger.error(e);
           raise Exception('Default Data key record not found!');
#
def getDataKey(sessionKey,recordId,name,logger):

    if len(recordId) == 0 and len(name) == 0:
        logger.info('Doing default Data API key lookup.');
        return getDefaultDataKey(sessionKey,logger);
    elif len(name) > 0:
        logger.info('Doing Data API key lookup by name: ' + name);
        return getDataKeyByName(sessionKey,name,logger);

    # Find by _key (recordId)
    logger.info('Doing API key lookup for record_id: ' + recordId);
    service = getService(sessionKey, myapp, logger)
    service.login()

    # set the kvstore collection with api key values
    collection = service.kvstore[data_collection_name]

    if data_collection_name in service.kvstore:

        result = None;
        try:
            result = collection.data.query_by_id(recordId);
        except Exception as e:
            logger.error(e);
            raise Exception('Record with key: ' + recordId + ' not found!');

        if result == None:
            logger.error('Failed to find record with id: ' + recordId + ' in the kv-store!');
            return ['',''];

        apiKey = getApiKey(sessionKey,result['_key'],logger);
        apiId = result['api_id'];
        name = result['name'];
        return [name,apiId,apiKey];

    else:
        raise Exception('Collection: ' + data_collection_name + ' not found!');


#
# Method to configure web proxy settings if a proxy is configured.
#
def getWebProxyConfig(sessionKey,logger):

    logger.info('Entering getWebProxyConfig')
    service = getService(sessionKey, myapp, logger)
    query = json.dumps({})
    collection = service.kvstore[proxy_collection_name]

    protocol = '';
    host = '';
    port = -1;
    user = '';
    proxyPass = '';

    if collection_name in service.kvstore:
        result = None;
        try:
            result = collection.data.query(query=query);
            if len(result) > 0:
                logger.info('Found Proxy configuration.');
                # This will find the optional proxy password.
                protocol = result[0]['protocol'];
                host = result[0]['host'];
                port = str(result[0]['port']);
                user = result[0]['user'];
                if len(user) > 0:
                    proxyPass = getApiKey (sessionKey,result[0]['_key']);
            else:
                logger.info('Proxy configuration not found.');

        except Exception as e:
            logger.error('Error retrieving proxy configuration');
            logger.error(e);
    else:
        logger.info('ProxyConig collection not found in KV store!');

    return { "protocol": protocol, "host": host, "port": port, "user": user, "pass": proxyPass};

#
# Send a VO notification using URL specified in api_endpoint, proxy configuration, and data that contains the
# alert's content.
#
def send_notification(sessionKey, api_endpoint, proxy, data,logger):

    if 'host' in proxy and proxy['host'] != '':
        proto = proxy['protocol'];
        proxyUrl = proto + '://' + proxy['host'] + ':' + proxy['port'] + '/';
        conf = {};

        # All calls to VictorOps API are https, setup proxy URL to reference
        # the proxy which could be http or https.
        conf['https'] = proxyUrl;
        conf['http'] = proxyUrl;
        proxy_handler = ProxyHandler(conf);

        if 'user' in proxy and proxy['user'] != '' and 'pass' in proxy and proxy['pass'] != '':
            logger.info('Configuring proxy configuration to use authentication...');
            # Proxy https requests with auth.
            proxy_auth_handler = HTTPBasicAuthHandler();
            proxy_auth_handler.add_password(None, proxyUrl, proxy['user'], proxy['pass']);
            opener = build_opener(proxy_handler, proxy_auth_handler);
        else:
            # Auth not defined, proxy all https requests w/out auth.
            logger.info('Using http proxy w/out authentication...');
            opener = build_opener(proxy_handler);

        install_opener(opener);

    else:
        logger.info('Proxy IS NOT configured!');

    # Send notification.
    body = json.dumps(data)
    logger.info('send_notification, endpoint path: ' + str(maskUrl(api_endpoint.split('?')[0].split('/', 3)[-1])));
    req = Request(api_endpoint, body.encode(), {"Content-Type": "application/json"});
    try:
        res = urlopen(req);
        body = res.read();
        logger.debug('Response Body=' + str(body));
        return True;

    except HTTPError as e:
        raise;

#
# Helper to mask the API key from the notification URL.
#
def maskUrl(url):
    return re.sub(r'.{8}-.{4}-.{4}-.{4}-', 'XXXX-XXXX-XXXX-XXXX-', url)

def getSystemSessionKey(sessionKey, logger):
    keyEndpoint = '/recover_alert'
    keyResponse, keyContent = splunk.rest.simpleRequest (keyEndpoint, method='GET', sessionKey=sessionKey, raiseAllErrors=False)
    return keyContent.decode('ASCII')
    
