# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
from __future__ import print_function
import fnmatch
import os, platform, time
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
    app = ''
    name = ''
    try:

        settings = saUtils.getSettings(sys.stdin)

        print ('Response')
        if len(sys.argv) >2:
            for arg in sys.argv[1:]:
                if arg.lower().startswith('name='):
                    eqsign = arg.find('=')
                    name = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('app='):
                    eqsign = arg.find('=')
                    app = arg[eqsign+1:len(arg)]
        else:
            raise Exception('xmDeleteSavedSearch-F-001: Usage: xmDeleteSavedSearch name=<string> app=<string>')

        authString = settings['authString'];
        p = re.compile('<username>(.*)\<\/username>')
        user= p.search(authString).group(1)

        endpoint = '/servicesNS/nobody/'+app+'/saved/searches/' + name
        response, content = splunk.rest.simpleRequest(endpoint, method='DELETE', sessionKey=settings['sessionKey'], raiseAllErrors=False)

        logger.info("xmDeleteSavedSearch - Deleted Saved Search: " + name);
        print (response.status)

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        si.generateErrorResults(e)
