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
    try:
        print ('Response')

        settings = saUtils.getSettings(sys.stdin)
        authString = settings['authString'];
        p = re.compile('<username>(.*)\<\/username>')
        user= p.search(authString).group(1)

        endpoint = '/servicesNS/nobody/bv_aba/configs/conf-app/install'
        postArgs = {'is_configured':1}
        response, content = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=settings['sessionKey'], raiseAllErrors=False, postargs=postArgs)

        if response.status != 200:
            logger.info("xmSetupComplete - Failure Setting [role_splunk-system-role], response.status=" + str(response.status));
            print ("FAILURE")
        else:
            logger.info("xmSetupComplete - Success Setting [role_splunk-system-role]");
            print ("SUCCESS")

        # Issue restart message.
        #postargs = {'severity': 'warn', 'name': 'restart_required', 'value': 'Splunk must be restarted for BV ABA Setup to take effect.'}
        #response, content = splunk.rest.simpleRequest('/services/messages', self.getSessionKey(), postargs=postargs)

        # Issue reload
        endpoint = '/servicesNS/-/search/admin/localapps/_reload'
        response, content = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=settings['sessionKey'], raiseAllErrors=False)
        if response.status != 200:
            logger.info("xmSetupComplete - Failure Reloading App Conf File  response.status=" + str(response.status));
            print ("FAILURE")
        else:
            logger.info("xmSetupComplete - Success Reloading App Conf File");
            print ("SUCCESS")

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        si.generateErrorResults(e)

