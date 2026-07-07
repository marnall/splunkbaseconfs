import splunk.entity as entity
import splunk
import requests
import sys
import json
import os
import random
import urllib
import base64
import urllib2
import re
from splunk.clilib import cli_common as cli

def getSelfConfStanza(stanza):
    appdir = os.path.dirname(os.path.dirname(__file__))
    apikeyconfpath = os.path.join(appdir, "default", "alert_actions.conf")
    apikeyconf = cli.readConfFile(apikeyconfpath)
    localconfpath = os.path.join(appdir, "local", "alert_actions.conf")
    if os.path.exists(localconfpath):
        localconf = cli.readConfFile(localconfpath)
        for name, content in localconf.items():
            if name in apikeyconf:
                apikeyconf[name].update(content)
            else:
                apikeyconf[name] = content
    return apikeyconf[stanza]

def getCredentials(sessionKey):
    username = ''
    password = ''
    restendpoint = ''
    myapp = 'd3_alert'
    try:
        # Add filter only return d3_alert credentials: search=d3_alert
        entities = entity.getEntities(['admin', 'passwords'], namespace=myapp, owner='nobody', sessionKey=sessionKey, search=myapp)
        #sys.stderr.write("[Debug] Entities: %s;" % entities)
    except Exception, e:
        sys.stderr.write("[Error] Cannot get credential information. error = %s ;" % e)
        return username, password, restendpoint

    for i, c in entities.items():
        username = c['username']
        password = c['clear_password']
        orginuser = username

    username=username[:username.index("_d3alert")]   #important: restore username to original username. 
    #Debug : output and verify final username and password                
    #sys.stderr.write("[Debug] UserOrigin: %s;" % orginuser)
    #sys.stderr.write("[Debug] UserName: %s;" % username)
    #sys.stderr.write("[Debug] Password: %s;" % password)

    stanz = getSelfConfStanza(myapp)
    restendpoint = stanz['restendpoint']
    return username, password, restendpoint

def send_message(settings):
    # Handle additional configuration fields 
    sessionKey = payload.get('session_key')

    username, password, restendpoint = getCredentials(sessionKey)
    if username == '' or password == '' or restendpoint == '':
        sys.stderr.write("Cannot get credential information. " +
                            "Please set up the credential information in app settings\n")
        return False
    if not restendpoint.startswith('https://'):
        print >> sys.stderr, "[ERROR] Request only can be sent in https. Please change your REST endpoint in setting to https: %s " % restendpoint
        return False

    body = build_post_body(settings)

    # POST TO API
    return make_post_request(restendpoint, username, password, body)
    
def build_post_body(bodyPayload):   
    payload = json.dumps(bodyPayload)
    body = {
		'splunkPayload': payload
	}
    return json.dumps(body)
	
def make_post_request(url, username, password, body):
    #body = urllib.urlencode(body)
    req = urllib2.Request(url, body)
    req.add_header('Content-Type', 'application/json')
    
    # Basic Authentication
    b64auth = make_basic_authentication(username, password)
    req.add_header('Authorization', 'Basic {0}'.format(b64auth))

    try:
        res = urllib2.urlopen(req)
        body = res.read()
        print >> sys.stderr, "[INFO] D3 API responded with HTTP status=%d" % res.code
        #print >> sys.stderr, "[INFO] server response: %s" % json.dumps(body)
        return 200 <= res.code < 300
    except urllib2.HTTPError, e:
        print >> sys.stderr, "[ERROR] Error sending message: %s" % e
        return False

def make_basic_authentication(username, password):
    return base64.encodestring('{0}:{1}'.format(username, password)).replace('\n', '')

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        
        if not send_message(payload):
            #print >> sys.stderr, "[ERROR] Failed trying to send data to D3"
            sys.exit(2)
        #else:
        #    print >> sys.stderr, "[INFO] Successfully sent to D3"
    else:
        print >> sys.stderr, "[ERROR] Unsupported execution mode (expected --execute flag)"
        sys.exit(1)
