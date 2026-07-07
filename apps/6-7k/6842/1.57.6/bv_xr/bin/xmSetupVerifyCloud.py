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
import json
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

        #endpoint = '/services/server/info/server-info'
        endpoint = '/services/server/info/server-info?output_mode=json'
        response, content = splunk.rest.simpleRequest(endpoint, method='GET', sessionKey=settings['sessionKey'], raiseAllErrors=False)
        #if response.status == 201 or response.status == 409:
            # 201 = index created successfully
            # 409 = index already exists

        try:
            instance_type = json.loads(content)['entry'][0]['content']['instance_type']
            if instance_type == 'cloud':
                print ("true")
            else:
                print ("false")
        except:
            # if this isn't cloud, then there is no "instance_type" field and an exception is thrown
            print ("false")

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        logger.error ("Exception!");
        si.generateErrorResults(e)
