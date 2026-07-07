# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
from __future__ import print_function
import fnmatch
import os
import re
import csv
import sys
import time
import platform
import saUtils
import splunk.Intersplunk as si
from xml.dom.minidom import parseString
import splunk.rest
import logging as logger
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

if __name__ == '__main__':
    try:
        print ('Response')

        settings = saUtils.getSettings(sys.stdin)
        authString = settings['authString'];
        p = re.compile('<username>(.*)\<\/username>')
        user= p.search(authString).group(1)

        endpoint = '/servicesNS/nobody/bv_xr/data/indexes'
        postArgs = {'name':'scm_signal','suspendHotRollByDeleteQuery':'true'}
        response, content = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=settings['sessionKey'], raiseAllErrors=False, postargs=postArgs)
        #if response.status == 201 or response.status == 409:
            # 201 = index created successfully
            # 409 = index already exists
        logger.info("xmSetupVerifyIndex - Create of scm_signal response code: " + str(response.status));

        postArgs = {'name':'scm_terrain_event','suspendHotRollByDeleteQuery':'true'} 
        response, content = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=settings['sessionKey'], raiseAllErrors=False, postargs=postArgs)
        logger.info("xmSetupVerifyIndex - Create of scm_terrain_event response code: " + str(response.status));

        postArgs = {'name':'scm_relevancy_graph','suspendHotRollByDeleteQuery':'true'}
        response, content = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=settings['sessionKey'], raiseAllErrors=False, postargs=postArgs)
        logger.info("xmSetupVerifyIndex - Create of scm_relevancy_graph response code: " + str(response.status));

        postArgs = {'name':'scm_transaction_instance','suspendHotRollByDeleteQuery':'true'}
        response, content = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=settings['sessionKey'], raiseAllErrors=False, postargs=postArgs)
        logger.info("xmSetupVerifyIndex - Create of scm_transaction_instance response code: " + str(response.status));

        print ("SUCCESS");

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        logger.error ("Exception!");
        si.generateErrorResults(e)

