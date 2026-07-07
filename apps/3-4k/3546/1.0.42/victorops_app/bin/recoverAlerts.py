from __future__ import absolute_import
from __future__ import print_function
import sys
import os
import time
from decimal import Decimal
import splunk.Intersplunk as si
import json
import logging as logger
import voUtils

logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','victorops_alert_recovery.log'),
     filemode='a')
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

myapp = 'victorops_app'

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
def getSettings(input_buf):

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

    return(settings)

# Retrieve alert recovery configuration from the KV store's alertrecovery collection.
def getRecoveryConfig(sessionKey):
    collection_name = 'alertrecovery';
    service = voUtils.getService(sessionKey, myapp, logger)
    query = json.dumps({})
    collection = service.kvstore[collection_name];

    # Lookup Alert recovery configuration from the KV store.
    if collection_name in service.kvstore:
        result = None;
        try:
            result = collection.data.query(query=query);

            if len(result) > 0:
                logger.info('Found alert recovery config');
                return result[0];
            else:
                # Recovery config not found, add default entry. Recovery is enabled by default with
                # polling interval of 5 minutes and numPeriods of 2.
                defaultConfig = {
                  "enabled": True,
                  "pollingInterval": 300,
                  "numPeriods": 2,
                  "_key": ""
                };
                logger.info('Inserting default alert recovery configuration: ' + json.dumps(defaultConfig));
                collection.data.insert(json.dumps(defaultConfig));
                logger.info('Alert recovery config not found, created default config entry in KV store' + json.dumps(defaultConfig));
                return defaultConfig;

        except Exception as e:
            logger.error(e);
            logger.error('Alert recovery config search error, returning default config');

    defaultConfig = { "enabled" : True, "pollingInterval": 300, "numPeriods": 2, "_key": "" };
    logger.warn('Recovery config collection not found, not found returning default config' + json.dumps(defaultConfig));
    return defaultConfig;

# Retrieve all rows from the active alerts collection.
def getActiveAlerts(sessionKey):
    collection_name = 'activealerts';
    service = voUtils.getService(sessionKey, myapp, logger)
    query = json.dumps({});

    collection = service.kvstore[collection_name];

    # Lookup Alert recovery configuration from the KV store.
    if collection_name in service.kvstore:
        result = None;
        try:
            return collection.data.query(query=query);
        except Exception as e:
            logger.error(e);
            raise Exception('Active alerts not found!');

    logger.info('No active alerts found, returning empty results!');
    return [];

def sendNotification(sessionKey,alertRecord):
    logger.info('Recovering alert: ' + json.dumps(alertRecord));

    # Here's what alertRecord looks like:
    # {"_key": "5dcadfae8f77d312ad30d821", "apiKeyId": "5d98abc28f77d39bde465a31",
    #  "routingKey": "", "messageType": "CRITICAL", "lastGeneratedTime": "1573576622.126897",
    # "monitoringTool": "splunk", "_user": "nobody", "entityId": "Splunk Alert: None", "apiEndpoint": "/someUrl"}

    # Retrieve the API key from the storage passwords endpoint, this attribute is used to build endpoint URL.
    apiKey = None;
    try:
        apiKeyResults = voUtils.getCredentials(sessionKey,alertRecord.get('apiKeyId'),'',logger);
        if len(apiKeyResults) > 0:
            # apiKeyResults is array: ['api_key','routing_key], extract api_key
            apiKey = apiKeyResults[0];

        if apiKey == '-1':
            logger.info("apiKey is -1")

    except Exception as e:
        # Hit a case where an active alert referenced a key that no longer exists, get the default key
        logger.error('Failed to get API Key for entry with key: ' + alertRecord.get('apiKeyId'));
        logger.error('Ignoring alert that references invalid api key');
        logger.error(e);
        # For the active alert to be removed by the caller.
        return True;

    # Retrieve optional routing key from alertRecord, this value is optional and might be 'None'.
    routingKey = alertRecord.get('routingKey');
    # App version for notification below.
    appVersion = voUtils.getAppVersion();
    # Alert Endpoint
    apiEndpoint = alertRecord.get('apiEndpoint');
    apiEndpoint = "%s/%s" % (alertRecord.get('apiEndpoint'), apiKey);
    # Optional Routing key for URL
    routingKey = alertRecord.get('routingKey');
    if routingKey == 'No Routing Keys Found':
        routingKey = '';
    if routingKey:
        apiEndpoint = "%s/%s" % (apiEndpoint, routingKey);

    data = dict(
        message_type='recovery',
        monitoring_tool=alertRecord.get('monitoringTool'),
        entity_id=alertRecord.get('entityId'),
        state_message='This alert has been recovered',
        version=appVersion
    );

    # Web proxy configuration.
    proxyConfig = {}
    try:
        proxyConfig = voUtils.getWebProxyConfig(sessionKey,logger);
    except Exception as e:
        logger.error('Exception retrieving webProxy config');
        logger.error(e);

    return voUtils.send_notification(sessionKey, apiEndpoint, proxyConfig, data, logger);

def removeActiveAlert(sessionKey,alertKey):
    collection_name = 'activealerts';
    service = voUtils.getService(sessionKey, myapp, logger)
    query = json.dumps({"_key" : alertKey});

    collection = service.kvstore[collection_name];

    # Lookup Alert recovery configuration from the KV store.
    if collection_name in service.kvstore:
        try:
            logger.info('Removing active alert with key: ' +  alertKey);
            return collection.data.delete(query=query);
        except Exception as e:
            logger.error(e);
            raise Exception('Active alerts not found!');
    else:
        logger.warn('Failed to remove active alert because collection: ' + collection_name + ' does not exist!');

def recoverAlerts(sessionKey):
    # First, retreive active alerts from the activealerts kvstore collection.
    # NOTE: This command must be ran in the victorops app context.
    config = getRecoveryConfig(sessionKey);
    logger.info('Retrieved alert recovery config: ' + json.dumps(config));

    if config.get('enabled') != True:
        # Done
        logger.debug('Alert Recovery is not enabled!');
        return;

    # Get attributes needed to recover alerts.
    pollingInterval = Decimal(config.get('pollingInterval'));
    numPeriods = Decimal(config.get('numPeriods'));
    logger.info('Alert Recovery is enabled, polling interval: ' + str(pollingInterval) + ' seconds, numPeriods invactive before recovery: ' + str(numPeriods));

    activeAlerts = getActiveAlerts(sessionKey);
    logger.info('Retrieved active alerts: ' + json.dumps(activeAlerts));
    if activeAlerts == None or len(activeAlerts) == 0:
        logger.info('No active alerts found, done!');
        return;

    logger.info('Found ' + str(len(activeAlerts)) + ' active alerts to process!');
    for record in activeAlerts:

        logger.info('Processing active alert: ' + json.dumps(record));

        # An active alert record looks like this:
        # {"_user": "nobody", "messageType": "CRITICAL", "monitoringTool": "splunk", "routingKey": "",
        # "apiKeyId": "5d98abc28f77d39bde465a31", "lastGeneratedTime": "1572857282.437252", "entityId": "Splunk Alert: None",
        # "apiEndpoint" : "/someUrl/" "_key": "5dbf116a8f77d340492e41da"}
        alertLastSent = float(record.get('lastGeneratedTime'));
        alertLastSent = Decimal('%.0f' % alertLastSent)
        alertKey = record.get('_key')
        curTime = Decimal('%.0f' % time.time())
        overridePollingInterval = record.get('poll_interval')
        overrideInactivePolls = record.get('inactive_polls')

        if overridePollingInterval != None and overridePollingInterval != '':
            logger.info("setting pollingInterval with override: " + str(overridePollingInterval))
            pollingInterval = Decimal(str(overridePollingInterval))

        if overrideInactivePolls != None and overrideInactivePolls != '':
            logger.info("setting numPeriods with override: " + str(overrideInactivePolls))
            numPeriods = Decimal(str(overrideInactivePolls))

        # Using polling interval and last alert generation time see if this alert should be cleared.
        clearTime = (alertLastSent + (pollingInterval*numPeriods));
        logger.info('alertLastSent: ' + str(alertLastSent) + ', clearTime: ' + str(clearTime) + ', curTime: ' + str(curTime));


        if clearTime < curTime or (alertLastSent == '-1'):
            # Send alert recovery notification.
            logger.info('Found alert that should be recovered because it has not been generated for ' + str(pollingInterval*numPeriods) + ' seconds, last sent time: ' + str(alertLastSent) + ', curTime: ' + str(curTime));
            success = sendNotification(sessionKey,record);
            if success == True:
                # Remove record from active alerts collection
                removeActiveAlert(sessionKey,alertKey);
                # Remove internal key
            else:
                logger.warn('Failed to send recovery alert, not removing active alert!');
        else:
            logger.info('Found alert that should NOT be recovered because not enough time has elapsed since last genertion time, expecting ' + str(pollingInterval*numPeriods) + ' seconds to elapse before its cleared, last sent time: ' + str(alertLastSent) + ', curTime: ' + str(curTime));

if __name__ == '__main__':

    global settings
    global sessionKey

    logger.info("---------------------------------------------------------------------------------------")
    logger.info("recoverAlerts starting");

    try:
        # Read splunk header and extract session key required to interact with the KV store.
        settings = getSettings(sys.stdin);

        sessionKey = settings.get('sessionKey');
        systemSessionKey = voUtils.getSystemSessionKey(sessionKey, logger)

        #recoverAlerts(sessionKey);
        recoverAlerts(systemSessionKey);

    except Exception as e:
        logger.error('alert recovery Exception:');
        logger.error(e);

    logger.info("recoverAlerts completed");
    logger.info("---------------------------------------------------------------------------------------")
