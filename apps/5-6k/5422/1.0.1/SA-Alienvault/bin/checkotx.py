#!/usr/bin/env python
# Check for malicious indicators according to AlienVault OTX data

#from __future__ import print_function
import sys, os
import splunk.Intersplunk
import json
import re

from otx.OTXv2 import OTXv2
import otx.check_iocs as chkotx

from configparser import ConfigParser

def isUrl(url):  
    regex = '[a-z0-9\._\/\:]+\w+[.]\w*\/?'
    if(re.search(regex, url)):  
        return True
    else:  
        return False

def isIP(ip):
    regex = '^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])$'
    if(re.search(regex, ip)):
        return True
    else:
        return False

def isHash(text):
    regex = '^[a-z0-9]'
    if(re.search(regex, text)):
        if len(text) in (32, 40, 56, 64, 96, 128):
            return True
        else:
            return False
    else:
        return False

def checkValue(value):
    if isIP(value):
        return 'ip'
    elif isHash(value):
        return 'hash'
    elif isUrl(value):
        return 'url'
    else:
        return

def getSelfConfStanza(stanza, conffile):
    appdir = os.path.dirname(os.path.dirname(__file__))
    confpath = os.path.join(appdir, "default", conffile)

    #Get Configuration values
    jConf = {}
    config = ConfigParser()
    
    config.read(confpath)

    localconfpath = os.path.join(appdir, "local", conffile)
    if os.path.exists(localconfpath):
        localconf = config.read(localconfpath)
        jConf = {'otxURL':config.get('otx_config', 'otxURL'), 'otxTOKEN':config.get('otx_config', 'otxTOKEN')}
    
    return jConf

def getOTXValues(param1, param2):
    stanza = 'otx_config'
    conffile = 'otx.conf'     

    getStanza = getSelfConfStanza(stanza, conffile)
    otxURL = getStanza['otxURL']
    otxTOKEN = getStanza['otxTOKEN']
    
    #Init otx Object
    otx = OTXv2(otxTOKEN, server = otxURL)
    
    return chkotx.checkIOC(param1, param2, otx)


if len(sys.argv) == 2:
    # Search for IOCs
    param1 = sys.argv[1]
    param2 = checkValue(param1)
    
    try:
        ioc = json.loads(getOTXValues(param1, param2))
        splunk.Intersplunk.outputResults(ioc)
    
    except Exception as e:
        pass
