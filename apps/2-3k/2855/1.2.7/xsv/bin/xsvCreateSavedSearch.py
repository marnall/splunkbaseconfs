#
# Copyright 2012-2016 Scianta Analytics LLC   All Rights Reserved.
# Reproduction or unauthorized use is prohibited. Unauthorized
# use is illegal. Violators will be prosecuted. This software
# contains proprietary trade and business secrets.
#
import fnmatch
import os
import re
import csv
import sys
import saUtils
import platform,time
import splunk.Intersplunk as si
from xml.dom.minidom import parseString
import splunk.rest

if __name__ == '__main__':
    app = ''
    name = ''
    search = ''
    try:
        print 'Response'
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
        else:
            raise Exception('xsvCreateSavedSearch-F-001: Usage: xsvCreateSavedSearch name=<string> search=<string> app=<string>')

        settings = saUtils.getSettings(sys.stdin)
        authString = settings['authString'];
        p = re.compile('<username>(.*)\<\/username>')
        user= p.search(authString).group(1)
        search = search.replace("'",'"');

        endpoint = '/servicesNS/'+user+'/'+app+'/saved/searches'
        postArgs = {'name': name,'search':search};
        response, content = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=settings['sessionKey'], raiseAllErrors=False, postargs=postArgs)

        print response.status

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception, e:
        si.generateErrorResults(e)

