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
import datetime

logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','ta_splunk_add_on_for_victorops_user_oncall_schedule.log'),
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

def getApiId(sessionKey):
    logger.info("getApiId() entry")
    try:
        endpoint = '/servicesNS/nobody/SCM-Framework/configs/conf-inputs/victorops_oncall%3A%2F%2Fvo_oncall?output_mode=json'
        response, passwdContent = splunk.rest.simpleRequest(endpoint, method='GET', sessionKey=sessionKey, raiseAllErrors=False)
        tmp = json.loads(passwdContent)
        api_id = tmp['entry'][0]['content']['api_id']
        return api_id
    except Exception as e:
        raise;

def getApiKey(sessionKey):
    logger.info("getApiKey() entry")
    try:
        #[credential:__REST_CREDENTIAL__#TA-splunk-add-on-for-victorops#data/inputs/victorops_oncall:vo_oncall``splunk_cred_sep``1:]
        #[credential:__REST_CREDENTIAL__#TA-splunk-add-on-for-victorops#data/inputs/victorops_oncall:vo_oncall``splunk_cred_sep``2:]
        passwdEndpoint = "/servicesNS/nobody/TA-splunk-add-on-for-victorops/storage/passwords/__REST_CREDENTIAL__%23TA-splunk-add-on-for-victorops%23data%252Finputs%252Fvictorops_oncall%3Avo_oncall%60%60splunk_cred_sep%60%601%3A?output_mode=json"
        passwdResponse, passwdContent = splunk.rest.simpleRequest (passwdEndpoint, method='GET', sessionKey=settings['sessionKey'], raiseAllErrors=False)
        tmp = json.loads(passwdContent)
        api_key= tmp['entry'][0]['content']['clear_password']
        tmp = json.loads(api_key);
        api_key = tmp.get("api_key")
        return api_key
    except Exception as e:
        raise;

def getUserOnCallSchedule(sessionKey, userId):

    api_id = getApiId(sessionKey)
    api_key = getApiKey(sessionKey)

    if api_id == "":
        # Done
        logger.debug('Data Key is not configured!');
        return;

    api_endpoint = 'https://api.victorops.com/api-public/v2/user/'+userId+'/oncall/schedule';

    body = ''

    try:
        req = Request(api_endpoint, None, {"Content-Type": "application/json", "X-VO-Api-Id":api_id, "X-VO-Api-Key":api_key})
        res = urlopen(req);
        body = res.read();
        d = json.loads(body.decode())
        #logger.info(body.decode())
        return d;

    except HTTPError as e:
        raise;

if __name__ == '__main__':

    global settings
    global sessionKey
    name = ''
    userId = ''

    logger.info("---------------------------------------------------------------------------------------")
    logger.info("getUserOnCallSchedule starting");

    if len(sys.argv) >1:
        for arg in sys.argv[1:]:
            userId = arg

    try:
        # Read splunk header and extract session key required to interact with the KV store.
        #print ('_time,entry')
        print ('startTime,endTime,entry')
        settings = getSettings(sys.stdin);

        sessionKey = settings.get('sessionKey');
        systemSessionKey = voUtils.getSystemSessionKey(sessionKey)

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

        d = getUserOnCallSchedule(systemSessionKey, userId);
        #logger.info(d)
        teamSchedules = d['teamSchedules']
        logger.info(teamSchedules)
        for dic in teamSchedules:
            teamName = ''
            schedules = []
            for key in dic:
                if key == 'team':
                    team = dic[key]
                    teamName = team['name']
                    #logger.info("teamName=" + teamName)
                elif key == 'schedules':
                    schedules = dic['schedules']
                    #logger.info("got schedule", {schedules})
                    logger.info("got schedules")
                    for item in schedules:
                        logger.info("processing schedule")
                        policyName = item["policy"]["name"]
                        #logger.info("policyName="+policyName)
                        scheduleList = item["schedule"]
                        for schedule in scheduleList:
                            onCallType = schedule["onCallType"]
                            rotationName = schedule["rotationName"]
                            shiftName = schedule["shiftName"]
                            entry = teamName + " | " + policyName + " | " + rotationName + " | " + shiftName
                            logger.info(entry)
                            rolls = schedule["rolls"]
                            for roll in rolls:
                                startDate = roll["start"]
                                idx = startDate.rfind(":")
                                tmpDate = roll["start"][:idx] + "" + roll["start"][idx+1:]
                                startTime = datetime.datetime.strptime(tmpDate, "%Y-%m-%dT%H:%M:%S%z")

                                endDate = roll["end"]
                                idx = endDate.rfind(":")
                                tmpDate = roll["end"][:idx] + "" + roll["end"][idx+1:]
                                endTime = datetime.datetime.strptime(tmpDate, "%Y-%m-%dT%H:%M:%S%z")

                                #print(str(startTime.timestamp())+","+entry)
                                print(str(startTime.timestamp())+","+str(endTime.timestamp())+","+entry)

                                #delta = datetime.timedelta(hours=1)
                                #while startTime <= endTime:
                                #    print(str(startTime.timestamp())+","+entry)
                                #    #print (start_date.strftime("%Y-%m-%d"))
                                #    startTime += delta



    except Exception as e:
        logger.error('getUserOnCallSchedule Exception');
        print ("No Schedule Found,,")
        logger.error(e);
        #si.generateErrorResults(Exception("Failure Retrieving OnCall Schedule"))

    logger.info("getUserOnCallSchedule completed");
    logger.info("---------------------------------------------------------------------------------------")
