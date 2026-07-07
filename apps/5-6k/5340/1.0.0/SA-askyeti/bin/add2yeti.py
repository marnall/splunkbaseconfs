from __future__ import print_function
import sys, os
import splunk.Intersplunk
from pyeti.api import YetiApi
import re
import socket
from splunk.clilib import cli_common as cli

def getSelfConfStanza(stanza, conffile):
    appdir = os.path.dirname(os.path.dirname(__file__))
    confpath = os.path.join(appdir, "default", conffile)
    conf = cli.readConfFile(confpath)
    localconfpath = os.path.join(appdir, "local", conffile)
    if os.path.exists(localconfpath):
        localconf = cli.readConfFile(localconfpath)
        for name, content in list(localconf.items()):
            if name in conf:
                conf[name].update(content)
            else:
                conf[name] = content

    return conf[stanza]

def isDomain(url):  
    regex = '[a-z0-9\._\/\:]+\w+[.]\w*\/?'
    if(re.search(regex, url)):  
        return True
    else:  
        return False

def isIP(address):
    try: 
        socket.inet_aton(address)
        return True
    except:
        return False

def isHash(text):
    if len(text) in (32, 40, 56, 64, 96, 128):
        return True
    else:
        return False

def checkValue(value):
    if isHash(value):
        return value
    elif isIP(value):
        return value
    elif isDomain(value):
        return value
    else:
        return

def addObservable(observable, tag):
    data = []
    tags = ['Splunk']

    if checkValue(observable) != None:
        tags.append(tag)
        addyeti = api.observable_add(observable, tags=tags)
        data.append({'ADDED' : observable})
    else:
        data.append({'ERROR' : "Observable must be valid IP, URL or HASH"})

    return data

	
try:
    stanza = "yeti_config"
    conffile = "yeti.conf"

    getStanza = getSelfConfStanza(stanza, conffile)
    yetiURL = getStanza['yetiURL']
    verifySSL = getStanza['verifySSL']
    
    api = YetiApi(yetiURL, verify_ssl = verifySSL)

    observable = sys.argv[1]
    tag = sys.argv[2]
		
    add2yeti = addObservable(observable, tag)
    splunk.Intersplunk.outputResults(add2yeti)

except Exception as e:
        print(e)
