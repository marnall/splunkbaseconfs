#!/usr/bin/env python

################################################################################
# This is SSL Framework version 1.5
# SSL Framework is an application for integration of Qualys SSL Labs
# functionality with SIEM systems.
#
# With SSL Framework you can automate encryption certificates maintenance,
# upload and correlate their data and statistics in various SIEM systems through
# the use of supplied analytical content packages.
#
# SSL Framework works on Windows and *NIX.
#
# Copyright (C) 2015  Wantax Ltd.
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR APARTICULAR PURPOSE.
#
# See the GNU General Public License for more details. You should have received
# a copy of the GNU General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.
#
# To get a copy of the software, please send an e-mail to
# gpl-request@socprime.com <mailto:gpl-request@socprime.com>
# or write to Suite 1, 5 Percy Str. London, W1T 1DG, UK.
################################################################################

__author__ = 'Nikolay Trofimyuk'
__version__ = '1.5'
__license__ = 'GPLv3'

import os
import sys
import re
import json
import time
from datetime import datetime
import logging
import logging.handlers
from logging.handlers import SysLogHandler
import socket
import ConfigParser
import argparse
import requests

currentdir = os.path.dirname(os.path.abspath(sys.argv[0]))
cert_path = os.path.normpath(currentdir +'/cacert.pem')
if not os.path.exists(cert_path):
    cert_path = None


# create logger
LOG_FILENAME = os.path.normpath(currentdir +'/ssl-framework-report.log')
logger = logging.getLogger('ssl-framework-logger')
logger.setLevel(logging.INFO)
handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=5242880, backupCount=4)
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
logger.addHandler(handler)


# global vars
exportFormat = ''
rowsList = []


errorPatternsDict = {
    'cef':'CEF:0|SOC Prime|SSL Framework|'+ __version__ +'|slf:{eventId}|{eventName}|{severity}| msg={msg}\n',
    'leef':'LEEF:1.0|SOC Prime|SSL Framework|'+ __version__ +'|slf:{eventId}|\tmsg={msg}\n',
    'log':'vendor="SOC Prime", product="SSL Framework", version="'+ __version__ +'", eventId="slf:{eventId}", eventName="{eventName}", severity={severity}, msg="{msg}"\n'
    }  

errorNamesDict= {
    '001':{'name':'Could not connect to server', 'sev':7},    
    '002':{'name':'Server returned error', 'sev':7},
    '003':{'name':'Server returned error', 'sev':5},
    '004':{'name':'Server returned error', 'sev':5},
    '005':{'name':'Invalid domain name', 'sev':5},
    '006':{'name':'Could not read file', 'sev':7},
    '007':{'name':'Report for domain not completed', 'sev':7},
    '008':{'name':'Domain list is empty', 'sev':5}
    }

    
def add_event_to_flow(eventDict):
    global rowsList
    evId = eventDict['eventId']
    eventDict['eventName'] = errorNamesDict[evId]['name']
    eventDict['severity'] = errorNamesDict[evId]['sev']
    event = errorPatternsDict[exportFormat].format(**eventDict)
    rowsList.append(event)
    

def raiseException(msg):
    logger.error(msg)
    raise Exception(msg)    #terminate script


def request(r_type, domain='', ip=''):
    requestStr = ''
    if r_type == 'info':
        requestStr = '{0}info'.format(BASEURL)
    elif r_type == 'analyze':
        requestStr = '{0}analyze?host={1}&publish=off&fromCache=on&maxAge={2}&all=done&ignoreMismatch=on'.format(BASEURL, domain, maxCacheAge)
#    elif r_type == 'getEndpointData':
#        requestStr = '{0}getEndpointData?host={1}&s={2}'.format(BASEURL, domain, ip)

    attempt = 0   
    while attempt < connectMaxRetries:
        
        try:
            attempt += 1
            if cert_path:
                r = requests.get(requestStr, verify=False, proxies=proxySettings)
            else:
                r = requests.get(requestStr, proxies=proxySettings, verify=False)
        except Exception as e:
            if attempt == connectMaxRetries:
                msg = 'Could not perform request to ssl-lab: '+str(e)
                add_event_to_flow({'eventId':'001', 'msg':msg})
                raiseException(msg)
            else:    
                logger.error('Could not perform request to ssl-lab: '+str(e))
                logger.info('Waiting and trying again')
                time.sleep(connectRetryTimeout)
                continue
        else:
            break


    if r.status_code == 200:
##################################
##        with open(domain + '.txt', 'w') as f:
##            json.dump(r.json(), f, sort_keys=False, indent=4, separators=(',', ': '))
##################################        
        return r.json()
    elif r.status_code == 400:
        msg = 'ssl-labs returned an error, code:[{0}], reason:[{1}], message:[{2}]'.format(r.status_code, r.reason, r.content)
        add_event_to_flow({'eventId':'002', 'msg':msg})
        raiseException(msg)
    elif r.status_code in [429, 503, 529]:
        msg = 'ssl-labs returned an error, code:[{0}], reason:[{1}]'.format(r.status_code, r.reason)
        logger.warning(msg)
        add_event_to_flow({'eventId':'003', 'msg':msg})
        time.sleep(maxAssessmentsTimeout)
 #  elif r.status_code == 500:
 #       raiseException('ssl-labs returned an error, code:[{0}], reason:[{1}]'.format(r.status_code, r.reason))
    else:
        msg = 'ssl-labs returned an error, code:[{0}], reason:[{1}]'.format(r.status_code, r.reason)
        add_event_to_flow({'eventId':'003', 'msg':msg})
        raiseException(msg)

##-400 - invocation error (e.g., invalid parameters)
##-429 - client request rate too high
##500 - internal error
##-503 - the service is not available (e.g., down for maintenance)
##-529 - the service is overloaded
##If you get 429, 503, 529, you should sleep for several minutes (e.g., 5, 15, 30 minutes, respectively)
##then try again. If you're writing an API client tool and get a 529 response, randomize the back-off time.
##If you get 500, it's best to give up.


def start_scan(domain):
    logger.info('Start of requesting report for domain [{0}]'.format(domain))
    while True:
        rjson = request('info')
        if rjson['maxAssessments'] <= rjson['currentAssessments']:
            # wait
            time.sleep(maxAssessmentsTimeout)
        else:
            break
    # start scan
    while True:
        rjson = request('analyze', domain)
        if rjson['status'] == 'READY':
            logger.info('Received report for domain [{0}]'.format(domain))                                  
            return rjson
        elif rjson['status'] == 'ERROR':
            msg = 'While requesting report for domain [{0}] ssl-labs returned an error: {1}'.format(domain, rjson['statusMessage'])
            add_event_to_flow({'eventId':'004', 'msg':msg})
            logger.error(msg)
            return
        else:   # DNS, IN_PROGRESS
            # wait result
            time.sleep(waitResultTimeout)



pattHostName = '^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9_\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9_\-]*[A-Za-z0-9])$'

def get_list_from_file():
    lines = []
    try:
        with open(domainsListFile, 'r') as f:
            for line in f:
                domain = line.strip()
                if line[0] != '#':
                    if re.match(pattHostName, domain) == None:
                        msg = 'Invalid domain name: ['+ domain +'], skip'
                        add_event_to_flow({'eventId':'005', 'msg':msg})
                        logger.warning(msg)
                    else:
                        lines.append(domain)

    except Exception as e:
        msg = 'Could not read file: '+str(e)
        add_event_to_flow({'eventId':'006', 'msg':msg})
        raiseException(msg)

    return lines[0:200]


def get_dict_field(val, path):
    for key in path:
        if type(val)==type({}) and key in val:
            val = val[key]               
        else:
            logger.debug('Key ['+ key +'] not found!')
            return ''
    
    if type(val) in [str, unicode]:                   
        val = val.encode("utf-8")
    return val


def datetime_from_utc_to_local(utc_datetime):
    utc_datetime = datetime.utcfromtimestamp(utc_datetime/1000)
    now_timestamp = time.time()
    offset = datetime.fromtimestamp(now_timestamp) - datetime.utcfromtimestamp(now_timestamp)
    return (utc_datetime + offset).strftime('%b %d %Y %H:%M:%S').upper()


def calc_valid_until_days(utc_datetime):
    utc_datetime = datetime.utcfromtimestamp(utc_datetime/1000)
    utc_date = datetime.date(utc_datetime)
    utc_now = datetime.utcnow().date()
    diff = (utc_date - utc_now).days
    if diff < 0:
        diff = 0
    return diff

revocationStatusDict = {
    0:'Not Defined (not checked)',
    1:'Bad (revoked)',
    2:'Good (not revoked)',
    3:'Not Defined (not checked)',
    4:'Bad (no revocation information)',
    5:'Not Defined (not checked)'
    }

vulnerabilitiesTxtDict = {
    'vulnBeast':'BEAST attack',
    'heartbleed':'Heartbleed (vulnerability)',
#    'heartbeat':'Heartbeat (extension)',
    'openSslCcs':'OpenSSL CCS vuln. (CVE-2014-0224)',
    'poodle':'POODLE (SSLv3)',
    'poodleTls':'POODLE (TLS)',
    'freak':'FREAK attack'
}

def get_vulns_list(endpoint):
    vulnsList = []
    for vulnName in vulnerabilitiesTxtDict.keys():
        val = get_dict_field(endpoint, ['details',vulnName])
        if vulnName == 'openSslCcs':
            if val in [2,3]:
                vulnsList.append(vulnerabilitiesTxtDict[vulnName])
        elif vulnName == 'poodleTls':
            if val == 2:
                vulnsList.append(vulnerabilitiesTxtDict[vulnName])
        elif val == True:
            vulnsList.append(vulnerabilitiesTxtDict[vulnName])
        else:
            continue

    if vulnsList:
        return ','.join(vulnsList)
    else:
        return 'Not found'



def get_trusted_status(issuerLabel, revocationStatus, certIssues):
    trusted = ''
    noTrustReason = ''

    if issuerLabel == '':
        noTrustReason = 'No Issuer'

    elif revocationStatus == 0:
        noTrustReason = 'RevocationStatus Not Defined'
    elif revocationStatus == 1:
        noTrustReason = 'Certificate Revoked'
    elif revocationStatus == 3:
        noTrustReason = 'RevocationStatus Not Checked'
    elif revocationStatus == 4:
        noTrustReason = 'No Revocation Information'
    elif revocationStatus == 5:
        noTrustReason = 'RevocationStatus not Defined'

    elif (certIssues & 1) == 1:
        noTrustReason = 'No Chain Of Trust'
    elif (certIssues & 2) == 2:
        noTrustReason = 'Certificate Not Yet Valid'
    elif (certIssues & 4) == 4:
        noTrustReason = 'Certificate Expired'
    elif (certIssues & 8) == 8:
        noTrustReason = 'Hostname Mismatch'
    elif (certIssues & 16) == 16:
        noTrustReason = 'Certificate Revoked'
    elif (certIssues & 32) == 32:
        noTrustReason = 'Bad Common Name'
    elif (certIssues & 64) == 64:
        noTrustReason = 'Certificate Self-Signed'
    elif (certIssues & 128) == 128:
        noTrustReason = 'Certificate Blacklisted'

    if noTrustReason:
        trusted = 'No ({0})'.format(noTrustReason)
    else:
        trusted = 'Yes'

    return trusted


def get_report_data(rjson):
    # get ip-list
    domain = rjson['host']
    endpointsList = rjson['endpoints']
    rowsList = []
    for endpoint in endpointsList:
        statusMessage = get_dict_field(endpoint, ['statusMessage'])
        if statusMessage != 'Ready':            
            msg = 'Report for domain:[{0}] not complete, reason:[{1}]'.format(domain, statusMessage)
            add_event_to_flow({'eventId':'007', 'msg':msg})            
            logger.warning(msg)
            continue

        rowDict = {}
        commonNames = get_dict_field(endpoint, ['details','cert','commonNames'])
        issuerLabel = get_dict_field(endpoint, ['details','cert','issuerLabel'])
        revocationStatus = get_dict_field(endpoint, ['details','cert','revocationStatus'])
        certIssues = get_dict_field(endpoint, ['details','cert','issues'])

        trusted = get_trusted_status(issuerLabel, revocationStatus, certIssues)
        
        rowDict['domain'] = domain
        rowDict['ip'] = get_dict_field(endpoint, ['ipAddress'])
        rowDict['grade'] = get_dict_field(endpoint, ['grade'])
        rowDict['commonNames'] = ','.join(commonNames)
        rowDict['altNames'] = ','.join(get_dict_field(endpoint, ['details','cert','altNames']))
        rowDict['notBefore'] = datetime_from_utc_to_local(get_dict_field(endpoint, ['details','cert','notBefore']))
        rowDict['notAfter'] = datetime_from_utc_to_local(get_dict_field(endpoint, ['details','cert','notAfter']))
        rowDict['validUntilD'] = calc_valid_until_days(get_dict_field(endpoint, ['details','cert','notAfter']))
        rowDict['key'] = '{0} {1} bits'.format(get_dict_field(endpoint, ['details','key','alg']), get_dict_field(endpoint, ['details','key','size']))
        rowDict['issuerLabel'] = issuerLabel
        rowDict['revocationStatus'] = revocationStatusDict[revocationStatus]
        rowDict['trusted'] = trusted
        rowDict['testTime'] = datetime_from_utc_to_local(rjson['testTime'])
        rowDict['httpStatusCode'] = get_dict_field(endpoint, ['details','httpStatusCode'])
        rowDict['httpForwarding'] = get_dict_field(endpoint, ['details','httpForwarding'])
        rowDict['serverSignature'] = get_dict_field(endpoint, ['details','serverSignature'])
        rowDict['serverName'] = get_dict_field(endpoint, ['serverName'])
        rowDict['reportUrl'] = 'https://www.ssllabs.com/ssltest/analyze.html?d={0}&hideResults=on'.format(domain)
        rowDict['sigAlg'] = get_dict_field(endpoint, ['details','cert','sigAlg'])
        rowDict['vulnsList'] = get_vulns_list(endpoint)

        rowsList.append(rowDict)

    return rowsList

#################################################################################
delimitersDict = {'cef':' ', 'leef':'\t', 'log':', '}

patternsDict = {
    'cef':'CEF:0|SOC Prime|SSL Framework|'+ __version__ +'|slf:101|SSL Labs Check|3|{0}\n',
    'leef':'LEEF:1.0|SOC Prime|SSL Framework|'+ __version__ +'|slf:101|{0}\n',
    'log':'vendor="SOC Prime", product="SSL Framework", version="'+ __version__ +'", eventId="slf:101", eventName="SSL Labs Check", severity=3{0}\n'
    }
    
mapDict = {
    'cef': {
        'domain':'fname={0}',
        'ip':'src={0}',
        'grade':'outcome={0}',
        'commonNames':'cs1={0} cs1Label=Common names',
        'altNames':'cs2={0} cs2Label=Alternative names',
        'notBefore':'deviceCustomDate1={0} deviceCustomDate1Label=Valid from',
        'notAfter':'deviceCustomDate2={0} deviceCustomDate2Label=Valid until',
        'validUntilD':'',
        'key':'filePermission={0}',
        'issuerLabel':'filePath={0}',
        'revocationStatus':'cs5={0} cs5Label=Revocation status',
        'trusted':'cs6={0} cs6Label=Trusted',
        'testTime':'end={0}',
        'httpStatusCode':'sourceUserId={0}',
        'httpForwarding':'sproc={0}',
        'serverSignature':'sourceServiceName={0}',
        'serverName':'shost={0}',
        'reportUrl':'request={0}',
        'sigAlg':'cs4={0} cs4Label=Signature algorithm',
        'vulnsList':'cs3={0} cs3Label=Vulnerabilities'
        },

    'leef': {
        'domain':'DomainName={0}',
        'ip':'src={0}',
        'grade':'Rating={0}',
        'commonNames':'commonNames={0}',
        'altNames':'altNames={0}',
        'notBefore':'validFrom={0}',
        'notAfter':'validUntil={0}',
        'validUntilD':'validUntilD={0}',
        'key':'keySign={0}',
        'issuerLabel':'certIssuer={0}',
        'revocationStatus':'revocStatus={0}',
        'trusted':'trustStatus={0}',
        'testTime':'devTime={0}\tdevTimeFormat=MMM dd yyyy HH:mm:ss',
        'httpStatusCode':'httpStatus={0}',
        'httpForwarding':'httpForw={0}',
        'serverSignature':'httpServSign={0}',
        'serverName':'serverHost={0}',
        'reportUrl':'FullReportUrl={0}',
        'sigAlg':'signAlgorithm={0}',
        'vulnsList':'vulnerabilitiesDomain={0}'
        },

    'log': {
        'domain':'domainName="{0}"',
        'ip':'src="{0}"',
        'grade':'rating="{0}"',
        'commonNames':'commonNames="{0}"',
        'altNames':'altNames="{0}"',
        'notBefore':'validFrom="{0}"',
        'notAfter':'validUntil="{0}"',
        'validUntilD':'validUntilD={0}',
        'key':'keySign="{0}"',
        'issuerLabel':'certIssuer="{0}"',
        'revocationStatus':'revocStatus="{0}"',
        'trusted':'trustStatus="{0}"',
        'testTime':'devTime="{0}"',
        'httpStatusCode':'httpStatus={0}',
        'httpForwarding':'httpForw="{0}"',
        'serverSignature':'httpServSign="{0}"',
        'serverName':'serverHost="{0}"',
        'reportUrl':'fullReportUrl="{0}"',
        'sigAlg':'signAlgorithm="{0}"',
        'vulnsList':'vulnerabilitiesDomain="{0}"'
        }
}

def dict_to_str(values): 
##    if isinstance(values, dict):
        cefstr = ''
        delimiter = delimitersDict[exportFormat]
        for key in reversed(values.keys()):
            if values[key]:                
##                if type(values[key]) in [str, unicode]:                   
##                    val = values[key].encode("utf-8")
##                else:
##                    val = values[key]
                cefstr = cefstr + delimiter + mapDict[exportFormat][key].format(values[key])
        return cefstr
##    else:
##        return values

def export_report(rowsList):
    pattern = patternsDict[exportFormat]
    rowsPerFile =  5000
    filescount = (len(rowsList) // rowsPerFile) + 1
    for filenum in range(1, filescount+1):
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
            filename = os.path.normpath('{0}/ssl-framework-report-{1}.{2}.{3}'.format(reportsPath, timestamp, filenum, 'tmp'))
            with open(filename, 'w') as f:
                logger.debug('File '+ filename +' created')
                for row in rowsList[(filenum-1)*rowsPerFile : filenum*rowsPerFile]:
                    if isinstance(row, dict):                     
                        try:                       
                            f.write(pattern.format(dict_to_str(row)))
                        except Exception as e:    
                            logger.debug('Can not format message: '+ str(row))
                            raise
                    else:                        
                        try:                       
                            f.write(row)
                        except Exception as e:    
                            logger.debug('Can not write message: '+ str(row))
                            raise                        
            
            logger.debug('File was exported')            
            newfname = filename[:-3]+exportFormat
            os.rename(filename, newfname)
            logger.debug('File was renamed') 
            filename = newfname
            logger.info('Ssl-framework-report was successfully created, file: {0}'.format(filename))
        except Exception as e:
            msg = 'Could not write file: '+str(e)
            logger.error(msg)
            raise Exception(msg)    #terminate script


def send_report_via_syslog(rowsList):
    try:
        syslogger = logging.getLogger('syslog')
        syslogger.setLevel(logging.INFO)
        
        if syslogProtocol == 'udp':
            syslogger.addHandler(SysLogHandler(address=(syslogHost, syslogPort)))                  
        else: # TCP only for Python 2.7+ 
            syslogger.addHandler(SysLogHandler(address=(syslogHost, syslogPort), socktype=socket.SOCK_STREAM))       

        pattern = patternsDict[exportFormat]
        for row in rowsList:
            if isinstance(row, dict):                     
                syslogger.info(pattern.format(dict_to_str(row)))  
            else:
                syslogger.info(row)              
                    
        logger.info('Ssl-framework-report was successfully created and sent to [{0}:{1}]'.format(syslogHost, syslogPort))
    except Exception as e:
        msg = 'Could not send syslog: '+str(e)
        logger.error(msg)
        raise Exception(msg)    #terminate script        

    
    
def get_config(filename):    
    _default_config = {
        'main':{
            'maxassessmentstimeout': 60,    #sec
            'waitresulttimeout': 60,        #sec
            'maxcacheage': 1,               #hours
            'reportspath': os.path.normpath(currentdir +'/reports/'),
            'domainslistfile': os.path.normpath(currentdir +'/domainlist.txt'),
            'exportformat':'cef',           #CEF, LEEF, SPLUNK
            'connectmaxretries': 10,
            'connectretrytimeout': 60,       #sec
            'use_splunk':0,
            'proxy_used':0,
            'proxy_auth_used':0
            }
        }
    config = ConfigParser.RawConfigParser()
    if os.path.exists(filename):
        config.read(filename)
    else:
        # create default config
        for section in _default_config:
            config.add_section(section)
            for option in _default_config[section]:
                config.set(section, option, _default_config[section][option])
        try:
            logger.info('Create default config: '+filename)
            with open(filename, 'wb') as configfile:
                config.write(configfile)
        except Exception as e:
            errmsg = 'Could not create config file: '+str(filename)
            logger.error(errmsg)
            raise Exception(errmsg)    
    
    return config

# ########################################################################
# access the credentials in /servicesNS/nobody/<YourApp>/storage/passwords
def getCredentials(sessionKey):
    myapp = 'SOCPrimeSSLFramework'
    try:
        import splunk.entity as entity
    except Exception as e:
        raise Exception('Can not import splunk.entity module')  
    else:
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
# ########################################################################

def get_proxy_settings(config, use_splunk):
    
    proxy_url = {}
    
    if config.has_section('main'):
        
        proxy_used = config.getint('main', 'proxy_used')
        proxy_auth_used = config.getint('main', 'proxy_auth_used')
                
        if proxy_used:
            
            host = config.get('main', 'proxy_host')
            port = config.getint('main', 'proxy_port')            
            
            if proxy_auth_used:                
                if use_splunk:
                    # get cred from splunk storage                     
                    # read session key sent from splunkd
                    sessionKey = sys.stdin.readline().strip()
                                
                    if len(sessionKey) == 0:                        
                       raise Exception("Did not receive a session key from splunkd. " + 
                                        "Please enable passAuth in inputs.conf for this " +
                                        "script\n")           
                    login, password = getCredentials(sessionKey)

                else:
                    #get cred from config
                    login = config.get('main', 'proxy_login') 
                    password = config.get('main', 'proxy_password')           
                       
                proxy_url = { "https": "https://{0}:{1}@{2}:{3}/".format(login, password, host, port) }
            else:
                proxy_url = { "https": "https://{0}:{1}/".format(host, port) }            

    return proxy_url 



#############################################################

if __name__ == '__main__':
    
    try:
        argparser = argparse.ArgumentParser()
        argparser.add_argument("-d", "--domain", help="Scan specified domain", action="store")
        argparser.add_argument("-c", "--config", help="Full path to application folder", action="store")
    
        args = argparser.parse_args()
    
        if args.config:
            _cfgfilename_default = os.path.normpath(args.config)        
        else:
            _cfgfilename_default = os.path.normpath(currentdir +'/ssl-framework.cfg') 
    
        # read config ###########################################
        logger.info('Start. Initialization...')
    
        config_default = get_config(_cfgfilename_default)
        
        BASEURL = 'https://api.ssllabs.com/api/v2/'
        reportsPath = os.path.normpath(os.path.abspath(config_default.get('main', 'reportspath')))
    
        if not os.path.exists(reportsPath):
            reportsPath = os.path.normpath(currentdir +'/' + config_default.get('main', 'reportsPath'))
    
        maxAssessmentsTimeout = config_default.getint('main', 'maxassessmentstimeout')
        waitResultTimeout = config_default.getint('main', 'waitresulttimeout')
        domainsListFile = os.path.normpath(os.path.abspath(config_default.get('main', 'domainslistfile')))
    
        if not os.path.exists(domainsListFile):
            domainsListFile = os.path.normpath(currentdir +'/' + config_default.get('main', 'domainslistfile'))
    
        maxCacheAge = config_default.getint('main', 'maxcacheage')
        exportFormat = config_default.get('main', 'exportformat').lower()
    
        if exportFormat == 'splunk':
            exportFormat = 'log'   
        
        # ########################           
        connectMaxRetries = config_default.getint('main', 'connectmaxretries')
        connectRetryTimeout = config_default.getint('main', 'connectretrytimeout')
        
        sendReportViaSyslog = False
        if config_default.has_section('syslog'):
            sendReportViaSyslog = True
            syslogProtocol = config_default.get('syslog', 'protocol').lower()
            
            if (sys.version_info < (2, 7)) and (syslogProtocol == 'tcp'):
                logger.warning('Sending syslog over TCP protocol is available only for Python 2.7+')
                   
            syslogHost = config_default.get('syslog', 'host')
            syslogPort = config_default.getint('syslog', 'port')
        
            
        if config_default.has_option('main', 'use_splunk'):
            use_splunk = config_default.getint('main', 'use_splunk')
        else:
            use_splunk = 0
            
        if use_splunk:
            _cfgfilename_local = os.path.normpath(os.path.dirname(args.config) + '/../local/sslframework.conf') 
            config_local = get_config(_cfgfilename_local) 
            proxySettings = get_proxy_settings(config_local, use_splunk)    
        else:
            proxySettings = get_proxy_settings(config_default, use_splunk)
    
        # ######################## 
    
        if args.domain:
            domainList = [args.domain]
        else:
            domainList = get_list_from_file()
    except Exception as e:
        logger.error('Error occurred: '+ str(e) +'. Terminate script.')
        raise
    # #####################################################################       
    try:
        if not domainList:
            msg = 'Domain names list is empty'
            add_event_to_flow({'eventId':'008', 'msg':msg})     
            logger.warning(msg)
        else:       
            for domain in domainList:
                result = start_scan(domain)
                if result:
                    rList = get_report_data(result)
                    rowsList.extend(rList)
                else:
                    continue
  
    except Exception as e:
        logger.warning('Error occurred: '+ str(e) +'. Exporting the collected data.')
        raise
   
    finally:
        if rowsList:
            if sendReportViaSyslog:
                send_report_via_syslog(rowsList)
            else:
                export_report(rowsList)
        else:
            logger.warning('Cannot create report, result is empty')

