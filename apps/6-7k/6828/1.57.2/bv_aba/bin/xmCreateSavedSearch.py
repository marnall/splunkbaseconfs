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
    search = ''
    cron = ''
    earliest_time = ''
    latest_time = ''
    try:

        settings = saUtils.getSettings(sys.stdin)

        print ('Response')
        if len(sys.argv) >3:
            for arg in sys.argv[1:]:
                if arg.lower().startswith('name='):
                    eqsign = arg.find('=')
                    name = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('search='):
                    eqsign = arg.find('=')
                    search = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('app='):
                    eqsign = arg.find('=')
                    app = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('cron='):
                    eqsign = arg.find('=')
                    cron = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('earliest_time='):
                    eqsign = arg.find('=')
                    earliest_time = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('latest_time='):
                    eqsign = arg.find('=')
                    latest_time = arg[eqsign+1:len(arg)]
        else:
            raise Exception('xmCreateSavedSearch-F-001: Usage: xmCreateSavedSearch name=<string> search=<string> app=<string> earliest_time=<string> latest_time=<string> cron=<string>')

        authString = settings['authString'];
        p = re.compile('<username>(.*)\<\/username>')
        user= p.search(authString).group(1)
        search = search.replace("'",'"');

        if app == 'ABA':
            endpoint = '/servicesNS/nobody/bv_aba/saved/searches'
        else:
            endpoint = '/servicesNS/nobody/SCM-Framework/saved/searches'
        postArgs = {'name': name,'search':search, 'cron_schedule':cron, 'is_scheduled':"1"};
        if cron == '':
            postArgs = {'name': name,'search':search, 'dispatch.earliest_time':earliest_time, 'dispatch.latest_time':latest_time};
        response, content = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=settings['sessionKey'], raiseAllErrors=False, postargs=postArgs)

        logger.info("xmCreateSavedSearch - Created Saved Search: " + name);
        print (response.status)

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        si.generateErrorResults(e)

