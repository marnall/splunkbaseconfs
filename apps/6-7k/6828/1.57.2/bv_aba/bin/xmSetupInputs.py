#
# Copyright 2023 BlueVoyant Inc.   All Rights Reserved.
# Reproduction or unauthorized use is prohibited. Unauthorized
# use is illegal. Violators will be prosecuted. This software
# contains proprietary trade and business secrets.
#
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
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s %(message)s',datefmt='%m-%d-%Y %H:%M:%S %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

if __name__ == '__main__':
    try:
        print ('Status')

        settings = saUtils.getSettings(sys.stdin)
        authString = settings['authString'];
        p = re.compile('<username>(.*)\<\/username>')
        user= p.search(authString).group(1)

        endpoint = '/services/data/inputs/http/http/enable'

        response, content = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=settings['sessionKey'], raiseAllErrors=False)

        if response.status == 200:
            logger.info("xmSetupInputs - Success Setting HTTP Inputs");
            print ("SUCCESS")
        else:
            logger.info("xmSetupInputs - Failure Setting HTTP Inputs, response.status=" + str(response.status));
            print ("FAILURE")

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        si.generateErrorResults(e)

