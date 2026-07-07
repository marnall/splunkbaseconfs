# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
from __future__ import print_function
import os,platform,time
import sys
import platform
import time
import re
import json
import splunk.Intersplunk as si
import saUtils
import splunk.rest

import logging as logger
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

if __name__ == '__main__':

    try:

        # Retrieve log_review.conf entry for from splunk storage
        settings = saUtils.getSettings(sys.stdin)
        logEndpoint = "/services/configs/conf-log_review?output_mode=json"
        logResponse, logContent = splunk.rest.simpleRequest (logEndpoint, method='GET', sessionKey=settings['sessionKey'], raiseAllErrors=False)
        tmp = json.loads(logContent)
        test = tmp['entry'];

        print("Result")
        for i in test:
            name = i.get("name","none")
            if (name == 'incident_review'):
                event_attributes = json.loads(i['content']['event_attributes'])
                found  =  0
                for x in event_attributes:
                    label = x['label']
                    #print(label)
                    if (label == 'Taxonomy'):
                        found = 1
                if (found == 0):
                    #attr = [{"label":"Severity","field":"severity"},{"label":"Risk Score","field":"risk"},{"label":"Transaction Key","field":"transaction_key"},{"label":"Taxonomy","field":"taxonomy"},{"label":"Anomaly Time","field":"event_time"},{"label":"GUID","field":"guid"}]
                    #event_attributes.append({"label":"JAMMER","field":"_jammer"})
                    #event_attributes.append(attr)
                    event_attributes.append({"label":"Severity","field":"severity"})
                    event_attributes.append({"label":"Risk Score","field":"risk"})
                    event_attributes.append({"label":"Transaction Key","field":"transaction_key"})
                    event_attributes.append({"label":"Taxonomy","field":"taxonomy"})
                    event_attributes.append({"label":"Anomaly Time","field":"event_tim"})
                    event_attributes.append({"label":"GUID","field":"guid"})
                    postArgs =  {'event_attributes':json.dumps(event_attributes)}
                    logEndpoint = "/services/configs/conf-log_review/incident_review"
                    logResponse, logContent = splunk.rest.simpleRequest (logEndpoint, method='POST', sessionKey=settings['sessionKey'], raiseAllErrors=False,postargs=postArgs)
                    print ("SUCCESS")
                else:
                    print ("ALREADY EXISTS")


        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)


    except Exception as e:
        #logger.info("xmSetupLogReview - EXCEPTION:  " + str(e.output))
        logger.info("xmSetupLogReview - Failure adding XV/XR Attributes")
        logger.info(e)
        print ("FAILURE")
