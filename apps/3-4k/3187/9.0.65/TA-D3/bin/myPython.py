import splunk.entity as entity
import requests
import json
import os
import sys
from splunk.clilib import cli_common as cli

def getSelfConfStanza(stanza):
    appdir = os.path.dirname(os.path.dirname(__file__))
    apikeyconfpath = os.path.join(appdir, "default", "appsetup.conf")
    apikeyconf = cli.readConfFile(apikeyconfpath)
    localconfpath = os.path.join(appdir, "local", "appsetup.conf")
    if os.path.exists(localconfpath):
        localconf = cli.readConfFile(localconfpath)
        for name, content in localconf.items():
            if name in apikeyconf:
                apikeyconf[name].update(content)
            else:
                apikeyconf[name] = content
    return apikeyconf[stanza]

def getData(username, password, realm):
    if username == '' or password == '' or realm == '':
        return
    url = realm + "/D3RESTfulAPI4IRCase"
    myResponse = requests.get(url, auth=(username, password))
    if(myResponse.ok):
        myObjectArray = json.loads(myResponse.content)
        for myObject in myObjectArray:
            print json.dumps(myObject, sort_keys=True)
    else:
        myResponse.raise_for_status()

def getCredentials(sessionKey):
    username = ''
    password = ''
    realm = ''
    myapp = 'TA-D3'
    try:
        # Add filter only return TA-D3 credentials: search=TA-D3
        entities = entity.getEntities(['admin', 'passwords'], namespace=myapp, owner='nobody', sessionKey=sessionKey, search=myapp)
        #sys.stderr.write("[Debug] Entities: %s;" % entities)
    except Exception, e:
        return username, password, realm

    for i, c in entities.items():
        username = c['username']
        password = c['clear_password']
        orginuser = username

    username=username[:username.index("_d3tad3")]   #important: restore username to original username. 
    #Debug : output and verify final username and password                
    #sys.stderr.write("[Debug] UserOrigin: %s;" % orginuser)
    #sys.stderr.write("[Debug] UserName: %s;" % username)
    #sys.stderr.write("[Debug] Password: %s;" % password)

    stanz = getSelfConfStanza("setupentity")
    realm = stanz['host_1'];
    return username, password, realm

def main():
    sessionKey = sys.stdin.readline().strip()
    if len(sessionKey) == 0:
        sys.stderr.write("Did not receive a session key from splunkd. " +
                            "Please enable passAuth in inputs.conf for this " +
                            "script\n")
        exit(2)
    username, password, realm = getCredentials(sessionKey)
    if username != '' and password != '' and realm != '':
        getData(username, password, realm)

main()
