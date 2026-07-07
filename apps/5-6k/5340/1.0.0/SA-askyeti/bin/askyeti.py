from __future__ import print_function
import sys, os
import splunk.Intersplunk
import json
from pyeti.api import YetiApi
import re
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

def getYetiValues(observable):
    data = []
    resData = {}
    results = api.observable_search(value = observable + "[a-zA-Z0-9]*", regex=True)
    if results:
        for item in results:
            resData = {}
            maininfo = api.observable_details(item['id'])

            if maininfo['context']:
                for det in maininfo['context']:
                    resData = {}
                    if not "contacted_by" in det:
                        resData['id'] = item['id']
                        resData['date_added'] = det["date_added"]
                        resData['description'] = det["description"]
                        resData['reference'] = det["reference"]
                        resData['source'] = det["source"]
                        resData['value'] = item['value']
                    else:
                        obsID = det['contacted_by'].get('id')
                        info = api.observable_details(obsID)

                        for dt in info['context']:
                            resData = {}

                            resData['date'] = dt["date"]
                            resData['et_alerts_total'] = dt["et_alerts_total"]
                            resData['size'] = dt["size"]
                            resData['source'] = dt["source"]
                            resData['threatlevel'] = dt['threatlevel']
                            resData['threatlevel_human'] = dt['threatlevel_human']
                            resData['type'] = dt['type']
                            resData['url'] = dt['url']
                            resData['virustotal_score'] = dt['virustotal_score']
                            resData['vxfamily'] = dt['vxfamily']
                            
                            resData['id'] = info["id"]
                            resData['description'] = info["description"]
                            resData['types'] = info["type"]
                            resData['human_url'] = info["human_url"]
                            resData['value'] = info["value"]
                            
            else:
                resData['created'] = maininfo["created"]
                resData['description'] = maininfo["description"]
                resData['human_url'] = maininfo["human_url"]
                resData['id'] = maininfo["id"]
                resData['sources'] = maininfo["sources"]
                resData['type'] = maininfo["type"]
                resData['value'] = maininfo["value"]
                
            data.append(resData)
    else:
        data.append({'info' : 'NOT FOUND'})
        
    return data


try:
    stanza = "yeti_config"
    conffile = "yeti.conf"     

    getStanza = getSelfConfStanza(stanza, conffile)
    yetiURL = getStanza['yetiURL']
    verifySSL = getStanza['verifySSL']
    api = YetiApi(yetiURL, verify_ssl = verifySSL)

    # Search for observables
    observable = sys.argv[1]
    
    if len(sys.argv) == 2:
        observable = sys.argv[1]
        askyeti = getYetiValues(observable)
        splunk.Intersplunk.outputResults(askyeti)

except Exception as e:
    print(e)
