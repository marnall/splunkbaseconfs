from __future__ import absolute_import
from __future__ import print_function
import sys
import os
import time
import re
from decimal import Decimal
import splunk.Intersplunk as si
import json
import logging as logger
import voUtils
import requests
import datetime

logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','create_incident.log'),
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

def getApiId(sessionKey):
    global org
    global incidentName
    logger.info("getApiId() entry")
    try:
        endpoint = '/servicesNS/nobody/TA-splunk-add-on-for-victorops/ta_victorops_victorops_incidents?output_mode=json'
        response, content = splunk.rest.simpleRequest(endpoint, method='GET', sessionKey=sessionKey, raiseAllErrors=False)
        logger.info(content)
        tmp = json.loads(content)

        entries = tmp['entry']
        for item in entries:
            logger.info("organization_id="+item['content']['organization_id'])
            if item['content']['organization_id'] == org:
                api_id= item['content']['api_id']
                logger.info("selected api_id="+api_id)
                incidentName= item['name']

        #api_id= tmp['entry'][0]['content']['api_id']
        #incidentName= tmp['entry'][0]['name']
        #logger.info("incidentName="+incidentName)
        return api_id

    except Exception as e:
        raise;

def getApiKey(sessionKey):
    global org
    global incidentName
    logger.info("getApiKey() entry")
    try:
        passwdEndpoint = "/servicesNS/nobody/TA-splunk-add-on-for-victorops/storage/passwords/__REST_CREDENTIAL__%23TA-splunk-add-on-for-victorops%23data%252Finputs%252Fvictorops_incidents%3A"+incidentName+"%60%60splunk_cred_sep%60%601%3A?output_mode=json"
        passwdResponse, passwdContent = splunk.rest.simpleRequest (passwdEndpoint, method='GET', sessionKey=settings['sessionKey'], raiseAllErrors=False)
        #logger.info(passwdContent)
        tmp = json.loads(passwdContent)
        api_key= tmp['entry'][0]['content']['clear_password']
        tmp = json.loads(api_key);
        api_key = tmp.get("api_key")
        return api_key
    except Exception as e:
        raise;

def createIncident(sessionKey, api_id, api_key, incident):

    if api_id == "":
        # Done
        logger.debug('Data Key is not configured!');
        return;

    api_endpoint = 'https://api.victorops.com/api-public/v1/incidents'


    appVersion = voUtils.getAppVersion().strip();
    splunkVersion = voUtils.getSplunkVersion()
    pythonVersion =  sys.version
    index = pythonVersion.find(' ')
    pythonVersion =  pythonVersion[:index-1]

    userAgent = "VictorOpsTA/" + appVersion + " Splunk/" + splunkVersion + " Python/" + str(pythonVersion)

    try:

        req = Request(api_endpoint, json.dumps(incident).encode('utf-8'), {"Content-Type": "application/json", "Accept": "application/json", "X-VO-Api-Id":api_id, "X-VO-Api-Key":api_key})
        res = urlopen(req);
        body = res.read()
        d = json.loads(body.decode())
        return d;

    except HTTPError as e:
        logger.info(e)
        raise;

if __name__ == '__main__':

    global settings
    global sessionKey
    org = '';
    summary = '';
    details = '';
    username = '';
    target_type = '';
    target_slug = '';
    ismultiresponder = '';
    bridge_url = '';
    bridge_phone = '';
    bridge_notes = '';

    logger.info("---------------------------------------------------------------------------------------")
    logger.info("createIncident starting");

    if len(sys.argv) >1:
        for arg in sys.argv[1:]:
            if arg.lower().startswith('org='):
                eqsign = arg.find('=')
                org = arg[eqsign+1:len(arg)]
            elif arg.lower().startswith('summary='):
                eqsign = arg.find('=')
                summary = arg[eqsign+1:len(arg)]
            elif arg.lower().startswith('details='):
                eqsign = arg.find('=')
                details = arg[eqsign+1:len(arg)]
            elif arg.lower().startswith('username='):
                eqsign = arg.find('=')
                username = arg[eqsign+1:len(arg)]
            elif arg.lower().startswith('target_type='):
                eqsign = arg.find('=')
                target_type = arg[eqsign+1:len(arg)]
            elif arg.lower().startswith('target_slug='):
                eqsign = arg.find('=')
                target_slug = arg[eqsign+1:len(arg)]
            elif arg.lower().startswith('ismultiresponder='):
                eqsign = arg.find('=')
                ismultiresponder = arg[eqsign+1:len(arg)]
            elif arg.lower().startswith('bridge_url='):
                eqsign = arg.find('=')
                bridge_url = arg[eqsign+1:len(arg)]
            elif arg.lower().startswith('bridge_phone='):
                eqsign = arg.find('=')
                bridge_phone = arg[eqsign+1:len(arg)]
            elif arg.lower().startswith('bridge_notes='):
                eqsign = arg.find('=')
                bridge_notes = arg[eqsign+1:len(arg)]
    try:

        # Read splunk header and extract session key required to interact with the KV store.
        #print ('_time,entry')
        print ('incident,entityId')
        settings = getSettings(sys.stdin);

        sessionKey = settings.get('sessionKey');
        systemSessionKey = voUtils.getSystemSessionKey(sessionKey)

        api_id = getApiId(sessionKey)
        api_key = getApiKey(sessionKey)

        # Get web proxy configuration.
        proxyConfig = {}
        try:
            proxyConfig = voUtils.getWebProxyConfig(sessionKey);
        except Exception as e:
            logger.error('Exception retrieving webProxy config');
            logger.error(e);

        if 'host' in proxyConfig and proxyConfig['host'] != '':
            logger.info('Using Web proxy for requests: ' + proxyConfig['protocol'] + '://' + proxyConfig['host'] + ':' + str(proxyConfig['port']));
            proto = proxyConfig['protocol'];
            proxyUrl = proto + '://' + proxyConfig['host'] + ':' + proxyConfig['port'] + '/';
            conf = {};

            # All calls to VictorOps API are https, setup proxy URL to reference
            # the proxy which could be http or https.
            conf['https'] = proxyUrl;
            conf['http'] = proxyUrl;
            logger.info('Proxy Configuration: ' + repr(conf));
            proxy_handler = ProxyHandler(conf);

            if 'user' in proxyConfig and proxyConfig['user'] != '' and 'pass' in proxyConfig and proxyConfig['pass'] != '':
                logger.info('Configuring proxy configuration to use authentication...');
                # Proxy https requests with auth.
                proxy_auth_handler = HTTPBasicAuthHandler();
                proxy_auth_handler.add_password(None, proxyUrl, proxyConfig['user'], proxyConfig['pass']);
                opener = build_opener(proxy_handler, proxy_auth_handler);
            else:
                # Auth not defined, proxy all https requests w/out auth.
                logger.info('Using http proxy w/out authentication...');
                opener = build_opener(proxy_handler);

            install_opener(opener);


        incident = {
            "summary": summary,
            "details": details,
            "userName": username,
            "targets": [
                {
                    "type": target_type,
                    "slug": target_slug
                }
            ],
            "isMultiResponder": bool(ismultiresponder)
        }


        if bridge_url != '':
            incident["conferenceBridge"] = { "url": bridge_url, "phone": bridge_phone, "notes": bridge_notes }
      
        logger.info(incident)
        d = createIncident(systemSessionKey, api_id, api_key, incident);
        logger.info(d)
        print(d["incidentNumber"]+","+d["entityId"])

    except Exception as e:
        logger.error('createIncident Exception');
        print ("Failure Creating Incident");
        logger.error(e);

    logger.info("createIncident completed");
    logger.info("---------------------------------------------------------------------------------------")
