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
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','ta_splunk_add_on_for_victorops_team_oncall_schedule.log'),
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

teamName = ''
org = ''
utc_offset = ''

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
    global teamName
    global org
    logger.info("getApiId() entry")
    try:
        endpoint = '/servicesNS/nobody/TA-splunk-add-on-for-victorops/ta_victorops_victorops_teams?output_mode=json'
        response, content = splunk.rest.simpleRequest(endpoint, method='GET', sessionKey=sessionKey, raiseAllErrors=False)
        #logger.info(content)
        tmp = json.loads(content)

        entries = tmp['entry']
        logger.info("org="+org)
        for item in entries:
            #logger.info("organization_id="+item['content']['organization_id'])
            if item['content']['organization_id'] == org:
                api_id= item['content']['api_id']
                #logger.info("selected api_id="+api_id)
                teamName= item['name']
        #logger.info("returning api_id")
        return api_id

    except Exception as e:
        raise;

def getApiKey(sessionKey):
    global org
    global teamName
    logger.info("getApiKey() entry")
    try:
        #[credential:__REST_CREDENTIAL__#TA-splunk-add-on-for-victorops#data/inputs/victorops_oncall:vo_oncall``splunk_cred_sep``1:]
        #[credential:__REST_CREDENTIAL__#TA-splunk-add-on-for-victorops#data/inputs/victorops_oncall:vo_oncall``splunk_cred_sep``2:]
        #passwdEndpoint = "/servicesNS/nobody/TA-splunk-add-on-for-victorops/storage/passwords/__REST_CREDENTIAL__%23TA-splunk-add-on-for-victorops%23data%252Finputs%252Fvictorops_oncall%3Avo_oncall%60%60splunk_cred_sep%60%601%3A?output_mode=json"
        passwdEndpoint = "/servicesNS/nobody/TA-splunk-add-on-for-victorops/storage/passwords/__REST_CREDENTIAL__%23TA-splunk-add-on-for-victorops%23data%252Finputs%252Fvictorops_teams%3A"+teamName+"%60%60splunk_cred_sep%60%601%3A?output_mode=json"
        passwdResponse, passwdContent = splunk.rest.simpleRequest (passwdEndpoint, method='GET', sessionKey=sessionKey, raiseAllErrors=False)
        tmp = json.loads(passwdContent)
        api_key= tmp['entry'][0]['content']['clear_password']
        tmp = json.loads(api_key);
        api_key = tmp.get("api_key")
        return api_key
    except Exception as e:
        raise;

def getTeamOnCallSchedule(sessionKey, api_id, api_key, teamId):

    if api_id == "":
        # Done
        logger.debug('Data Key is not configured!');
        return;

    #api_endpoint = 'https://api.victorops.com/api-public/v2/team/'+teamId+'/oncall/schedule?daysForward=30';
    api_endpoint = 'https://api.victorops.com/api-public/v2/team/'+teamId+'/oncall/schedule?daysForward=123';
    #logger.info("api_endpoint="+api_endpoint)

    body = ''

    appVersion = voUtils.getAppVersion().strip();
    splunkVersion = voUtils.getSplunkVersion()
    pythonVersion =  sys.version
    index = pythonVersion.find(' ')
    pythonVersion =  pythonVersion[:index-1]

    userAgent = "VictorOpsTA/" + appVersion + " Splunk/" + splunkVersion + " Python/" + str(pythonVersion)

    try:
        req = Request(api_endpoint, None, {"Content-Type": "application/json", "X-VO-Api-Id":api_id, "X-VO-Api-Key":api_key, "User-Agent":userAgent})
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
    teamId = []
    team = []
    org = '*'

    logger.info("---------------------------------------------------------------------------------------")
    logger.info("getTeamOnCallSchedule starting");

    if len(sys.argv) >1:
        for arg in sys.argv[1:]:
            team.append(arg)
    try:

        # Read splunk header and extract session key required to interact with the KV store.
        #print ('_time,entry')
        print ('startTime,endTime,entry')
        settings = getSettings(sys.stdin);

        sessionKey = settings.get('sessionKey');
        systemSessionKey = voUtils.getSystemSessionKey(sessionKey)

        for item in team:
            tilda = item.find('~')
            org=item[:tilda]
            teamId=item[tilda+1:len(item)]
            logger.info("processing org="+org+", team="+teamId)

            #api_id = getApiId(sessionKey)
            #api_key = getApiKey(sessionKey)
            api_id = getApiId(systemSessionKey)
            api_key = getApiKey(systemSessionKey)

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

            d = getTeamOnCallSchedule(systemSessionKey, api_id, api_key, teamId);
            #logger.info(d)
            schedules = d['schedules']
            #logger.info(schedules)

            teamRecord = d['team']
            teamName = teamRecord['name']
            #logger.info(teamName)

            for item in schedules:
                #logger.info(item)

                logger.info("processing schedule")
                policyName = item["policy"]["name"]
                #logger.info("policyName="+policyName)
                scheduleList = item["schedule"]
                for schedule in scheduleList:
                    rolls = schedule["rolls"]
                    if not rolls:
                        logger.info("No Rolls for schedule")
                    else:
                        logger.info("Schedule Has Rolls ")
                        #onCallType = schedule["onCallType"]
                        #rotationName = schedule["rotationName"]
                        #shiftName = schedule["shiftName"]
                        for roll in rolls:
                            onCallUser = roll["onCallUser"]
                            userName = onCallUser['username']
                            #entry = teamName + " | " + policyName + " | " + userName
                            entry = teamName + " | " + userName + " | " + policyName
                            logger.info(entry)

                            startDate = roll["start"]
                            logger.info("Processing startDate: " + str(startDate))
                            if utc_offset == "":
                                p = re.compile('.*T[0-9][0-9]:[0-9][0-9]:[0-9][0-9](.*)')
                                match = p.search(startDate)
                                if not match:
                                    logger.error("Could not parse timezone from startDate: " + startDate)
                                    utc_offset = 0
                                    continue
                                tmp= match.group(1) 
                                idx = tmp.rfind(":")
                                hours = tmp[:idx]
                                utc_offset = int(hours)*60*60;
                                logger.info("utc_offset="+str(utc_offset))
                            p = re.compile('(.*T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]).*')
                            match = p.search(startDate)
                            if not match:
                                logger.error("Could not parse startDate: " + startDate)
                                continue
                            tmp= match.group(1) 
                            #logger.info(tmp)
                            tmpDate = tmp + "Z"
                            startTime = datetime.datetime.strptime(tmpDate, "%Y-%m-%dT%H:%M:%SZ")

                            endDate = roll["end"]
                            p = re.compile('(.*T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]).*')
                            match = p.search(endDate)
                            if not match:
                                logger.error("Could not parse endDate: " + endDate)
                                continue
                            tmp= match.group(1) 
                            tmpDate = tmp + "Z"
                            endTime = datetime.datetime.strptime(tmpDate, "%Y-%m-%dT%H:%M:%SZ")

                            logger.info(startTime);
                            # Convert to epoch timestamp reliably
                            startEpoch = int((startTime - datetime.datetime(1970, 1, 1)).total_seconds())
                            endEpoch = int((endTime - datetime.datetime(1970, 1, 1)).total_seconds())
                            logger.info("startEpoch="+str(startEpoch));
                            print(str(startEpoch)+","+str(endEpoch)+","+entry)

                logger.info("Checking for Overrides")
                #utc_offset_seconds = time.localtime().tm_gmtoff;
                #logger.info("utc_offset_seconds="+str(utc_offset_seconds))
                overrideList = item["overrides"]
                for override in overrideList:
                    #{'origOnCallUser': {'username': 'nharper'}, 'overrideOnCallUser': {'username': 'jmcglynn4'}, 'start': '2020-09-06T00:00:00Z', 'end': '2020-09-06T04:00:00Z', 'policy': {'name': 'Primary', 'slug': 'pol-6WXpi9lGIeUUjjNi'}}
                    logger.info(override)
                    userName = override['overrideOnCallUser']['username']
                    policyName = override['policy']['name']
                    entry = teamName + " | " + userName + " | " + policyName + " *"
                    logger.info(entry)

                    startDate = override["start"]
                    startTime = datetime.datetime.strptime(startDate, "%Y-%m-%dT%H:%M:%SZ")
                    startTime = startTime+datetime.timedelta(0,utc_offset)

                    endDate = override["end"]
                    endTime = datetime.datetime.strptime(endDate, "%Y-%m-%dT%H:%M:%SZ")
                    endTime = endTime+datetime.timedelta(0,utc_offset)

                    # Convert to epoch timestamp reliably
                    startEpoch = int((startTime - datetime.datetime(1970, 1, 1)).total_seconds())
                    endEpoch = int((endTime - datetime.datetime(1970, 1, 1)).total_seconds())
                    print(str(startEpoch)+","+str(endEpoch)+","+entry)

    except Exception as e:
        logger.error('getTeamOnCallSchedule Exception');
        print ("No Schedule Found,,")
        logger.error(e);
        #si.generateErrorResults(Exception("Failure Retrieving OnCall Schedule"))

    logger.info("getTeamOnCallSchedule completed");
    logger.info("---------------------------------------------------------------------------------------")
