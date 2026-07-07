# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
from __future__ import print_function
import fnmatch
import os
import platform
import time
import re
import csv
import sys
import saUtils
import splunk.Intersplunk as si
from xml.dom.minidom import parseString
import splunk.rest
import logging as logger
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

if __name__ == '__main__':
    title = ''        # incident title
    description = ''  # incident description
    time = ''         # epoch or string format ?
    severity = ''     # MINIMAL, LOW, MEDIUM, HIGH, EXTREME
    id = ''           # actorId or assetId
    name = ''         # actor or asset name
    type = ''         # ActorThreat or AssetThreat
    app = ''          # xv_actor_behavior, xv_anti_fraud, ...
    threat_score = '' # computed threat score 
    risk_score = ''   # computed risk score
    threat_link = ''  # link to threat detail view

    try:

        settings = saUtils.getSettings(sys.stdin)

        # How many params should be required? Assume All for now (10)
        print ('Response')
        if len(sys.argv) >10:
            for arg in sys.argv[1:]:
                if arg.lower().startswith('title='):
                    eqsign = arg.find('=')
                    title = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('description='):
                    eqsign = arg.find('=')
                    description = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('time='):
                    eqsign = arg.find('=')
                    time = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('severity='):
                    eqsign = arg.find('=')
                    severity = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('id='):
                    eqsign = arg.find('=')
                    id = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('name='):
                    eqsign = arg.find('=')
                    name = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('type='):
                    eqsign = arg.find('=')
                    type = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('threat_score='):
                    eqsign = arg.find('=')
                    threat_score = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('risk_score='):
                    eqsign = arg.find('=')
                    risk_score = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('threat_link='):
                    eqsign = arg.find('=')
                    threat_link = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('app='):
                    eqsign = arg.find('=')
                    app = arg[eqsign+1:len(arg)]
        else:
            raise Exception('xmSendIncident-F-001: Usage: xmSendIncident title=<string> description=<string> time=<string> severity=<string> id=<string> type=<string> threat_score=<string> risk_score=<string> threat_link=<string> app=<string>')

        #authString = settings['authString'];
        #p = re.compile('<username>(.*)\<\/username>')
        #user= p.search(authString).group(1)
        #search = search.replace("'",'"');
        #endpoint = '/servicesNS/nobody/'+app+'/saved/searches'
        #postArgs = {'name': name,'search':search, 'cron_schedule':cron, 'is_scheduled':"1"};
        #if cron == '':
        #    postArgs = {'name': name,'search':search, 'dispatch.earliest_time':earliest_time, 'dispatch.latest_time':latest_time};
        #response, content = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=settings['sessionKey'], raiseAllErrors=False, postargs=postArgs)
        #print (response.status)

        print ("SUCCESS")

        logger.info("xmSendIncident - : " + title);

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        si.generateErrorResults(e)

