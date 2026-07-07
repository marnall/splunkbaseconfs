import os
import sys
import json as j
import datetime
import requests as r
from splunk.clilib import cli_common as cli
from HTMLParser import HTMLParser; h = HTMLParser()



# Gets what was provided in the App Setup for Operator Password:
def getAuth(key):
    endpoint = 'https://localhost:8089/servicesNS/admin/' + app + '/storage/passwords/:smOperator:'
    head = {'Authorization':''}
    head['Authorization'] = 'Splunk ' + key
    response = r.get( endpoint, headers=head, verify=False )
    start    = response.text.find( 'clear_password' )
    start    = start + 16
    end      = response.text.find( '</s:key>', start )
    clear    = response.text[start:end]
    purty    = h.unescape(clear);
    return purty



# Gets what was provided in Setup for Endpoint, Port, Field Captions, and Field Values:
def getIntegrationDetails(stanza):
    whereAmI    = os.path.dirname(os.path.dirname(__file__))
    defaultPath = os.path.join(whereAmI, "default", "app.conf")
    defaultConf = cli.readConfFile(defaultPath)
    localPath   = os.path.join(whereAmI, "local", "app.conf")
    if os.path.exists(localPath):
       localConf = cli.readConfFile(localPath)
       for name, content in localConf.items():
           if name in defaultConf:
              defaultConf[name].update(content)
           else:
              defaultConf[name] = content
    return defaultConf[stanza]



def log(msg):
    f = open(os.path.join(os.environ["SPLUNK_HOME"], "etc", "apps", app, "log", "createIncident.log"), "a")
    print >> f, '\n', str(datetime.datetime.now().isoformat()), msg
    f.close()



# Let's rock 'n' roll!
app    = 'smIntegration'
raw    = sys.stdin.read(); log('createIncident.py: STDIN was: ' + raw)
json   = j.loads(raw)
key    = json['session_key'];

stanza = getIntegrationDetails('createIncident')
if stanza['fqdn'] and stanza['port'] and stanza['endp']:
   url = 'http://' + stanza['fqdn'] + ':' + stanza['port'] + '/SM/9/rest/' + stanza['endp']

if stanza['user']: creds = ( stanza['user'], getAuth(key) )

payload = {}
payload['category'] = 'incident'
if json['configuration']['title']:       payload[stanza['title']]       = json['configuration']['title']

if json['configuration']['service']:     payload[stanza['service']]     = json['configuration']['service']

if json['configuration']['assignment']:  payload[stanza['assignment']]  = json['configuration']['assignment'] 

if json['configuration']['assignee']:    payload[stanza['assignee']]    = json['configuration']['assignee'] 

if json['configuration']['impact']:      payload[stanza['impact']]      = json['configuration']['impact'] 

if json['configuration']['urgency']:     payload[stanza['urgency']]     = json['configuration']['urgency']

if json['configuration']['subcategory']: payload[stanza['subcategory']] = json['configuration']['subcategory']

if json['configuration']['area']:        payload[stanza['area']]        = json['configuration']['area'] 

if json['configuration']['source']:      payload[stanza['source']]      = json['configuration']['source'] 

if json['result']['host']:               payload[stanza['ci']]          = json['result']['host']

desc = [ 'Raw Event found by Splunk was:', json['result']['_raw'], 'To view the search results which created this Incident, visit this URL:', json['results_link'] ]
if json['configuration']['description']: desc.insert(0, json['configuration']['description'])

payload[stanza['description']] = desc;
incident = {}
incident['Incident'] = payload
IM = j.dumps(incident)

if url and creds[0] and creds[1] and IM: create = r.post( url, auth=(creds[0], creds[1]), data=IM )

log('createIncident.py: POST response from Service Manager was: ' + create.text)


