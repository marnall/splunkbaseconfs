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
import requests

logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','victorops_retrieve_routing_keys.log'),
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

def getTeams(sessionKey, recordId):
    name,api_id,api_key = voUtils.getDataKey(sessionKey,recordId,'',logger)

    if api_id == "":
        # Done
        logger.debug('Data Key is not configured!');
        return;
    api_endpoint = 'https://api.victorops.com/api-public/v1/team'
    body = ''
    try:
        req = Request(api_endpoint, None, {"Content-Type": "application/json", "X-VO-Api-Id":api_id, "X-VO-Api-Key":api_key})
        res = urlopen(req);
        body = res.read();
        d = json.loads(body.decode())
        logger.info(body.decode())
        return d;

    except HTTPError as e:
        raise;

def getRoutingKeys(sessionKey, recordId):

    name,api_id,api_key = voUtils.getDataKey(sessionKey,recordId,'',logger)

    if api_id == "":
        # Done
        logger.debug('Data Key is not configured!');
        return;

    api_endpoint = 'https://api.victorops.com/api-public/v1/org/routing-keys'
    body = ''

    try:
        req = Request(api_endpoint, None, {"Content-Type": "application/json", "X-VO-Api-Id":api_id, "X-VO-Api-Key":api_key})
        res = urlopen(req);
        body = res.read();
        d = json.loads(body.decode())
        logger.info(body.decode())
        return d;

    except HTTPError as e:
        raise;

if __name__ == '__main__':

    global settings
    global sessionKey
    name = ''
    recordId = ''

    logger.info("---------------------------------------------------------------------------------------")
    logger.info("retrieveRoutingKeys starting");

    if len(sys.argv) >1:
        for arg in sys.argv[1:]:
            recordId = arg

    try:
        # Read splunk header and extract session key required to interact with the KV store.
        print ('routingKey,policyName,teamName')
        settings = getSettings(sys.stdin);

        sessionKey = settings.get('sessionKey');
        systemSessionKey = voUtils.getSystemSessionKey(sessionKey, logger)

        # Get web proxy configuration.
        proxyConfig = {}
        try:
            proxyConfig = voUtils.getWebProxyConfig(sessionKey,logger);
        except Exception as e:
            logger.error('Exception retrieving webProxy config');
            logger.error(e);

        if 'host' in proxyConfig and proxyConfig['host'] != '':
            proto = proxyConfig['protocol'];
            proxyUrl = proto + '://' + proxyConfig['host'] + ':' + proxyConfig['port'] + '/';
            conf = {};

            # All calls to VictorOps API are https, setup proxy URL to reference
            # the proxy which could be http or https.
            conf['https'] = proxyUrl;
            conf['http'] = proxyUrl;
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

        d = getRoutingKeys(systemSessionKey, recordId);
        routingKeys = d['routingKeys']
        #logger.info(routingKeys)

        teams = getTeams(systemSessionKey,recordId);
        #logger.info(teams)

        for dic in routingKeys:
            routingKey = ''
            isDefault = ''
            targets = ''
            for key in dic:
                if key == 'routingKey':
                    routingKey = dic[key]
                elif key == 'isDefault':
                    isDefault = str(dic[key])
                    if isDefault == 'True':
                        isDefault = 'true'
                    else:
                        isDefault = 'false'
                elif key == 'targets':
                    targets = dic[key]

            if (routingKey != '') and (isDefault != '') and (targets != ''):
                for dic2 in targets:
                    policyName = ''
                    policySlug = ''
                    _teamUrl  = ''
                    for key2 in dic2:
                        if key2 == 'policyName':
                            policyName = dic2[key2]
                        elif key2 == 'policySlug':
                            policySlug = dic2[key2]
                        elif key2 == '_teamUrl':
                            _teamUrl = dic2[key2]

                    teamName = ''
                    for dic3 in teams:
                        teamUrl = ''
                        teamName = ''
                        found = False
                        for key3 in dic3:
                            if key3 == '_selfUrl':
                               selfUrl = dic3[key3]
                            elif key3 == 'name':
                                teamName = dic3[key3]
  
                        if selfUrl == _teamUrl:
                            logger.info("routingKey: " + routingKey + ", policyName: " + policyName + ", teamName: " + teamName)
                            print (routingKey + ',' + policyName + ',' + teamName)

 
    except Exception as e:
        logger.error('retrieveRoutingKeys Exception');
        print ("No Routing Keys Found,,")
        logger.error(e);
        #si.generateErrorResults(Exception("Failure Retrieving Routing Keys"))

    logger.info("retrieveRoutingKeys completed");
    logger.info("---------------------------------------------------------------------------------------")
