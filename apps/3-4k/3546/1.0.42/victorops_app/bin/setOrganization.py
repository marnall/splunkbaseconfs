from __future__ import print_function
import fnmatch
import os
import platform
import time
import re
import csv
import sys
import splunk.Intersplunk as si
from xml.dom.minidom import parseString
import splunk.rest
import logging as logger
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','victorops_set_organization.log'),
     filemode='a')

myapp = 'victorops_app'

def unquote(s):
    """unquote('abc%20def') -> 'abc def'."""
    mychr = chr
    myatoi = int
    list = s.split('%')
    res = [list[0]]
    myappend = res.append
    del list[0]
    for item in list:
        if item[1:2]:
            try:
                myappend(mychr(myatoi(item[:2], 16))
                     + item[2:])
            except ValueError:
                myappend('%' + item)
        else:
            myappend('%' + item)
    return "".join(res)

# Internal method to read command header from splunk.
def getSettings(input_buf):

    settings = {}
    # get the header info
    input_buf = sys.stdin
    # until we get a blank line, read "attr:val" lines, setting the values in 'settings'
    attr = last_attr = None
    while True:
        line = input_buf.readline()
        line = line[:-1] # remove lastcharacter(newline)
        if len(line) == 0:
            break

        colon = line.find(':')
        if colon < 0:
            if last_attr:
               settings[attr] = settings[attr] + '\n' + unquote(line)
            else:
               continue

        # extract it and set value in settings
        last_attr = attr = line[:colon]
        val  = unquote(line[colon+1:])
        settings[attr] = val

    return(settings)

if __name__ == '__main__':

    organization = ''

    try:

        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                if arg.lower().startswith('organization='):
                    eqsign = arg.find('=')
                    organization = arg[eqsign+1:len(arg)]

        if organization == '':
            raise Exception('setOrganization-F-001: Usage: setOrganization organization=<string>')

        print ('Response')

        settings = getSettings(sys.stdin)
        authString = settings['authString'];
        p = re.compile('<username>(.*)\<\/username>')
        user= p.search(authString).group(1)

        endpoint = '/servicesNS/nobody/victorops_app/configs/conf-app/ui'
        postArgs = {'organization':organization}
        response, content = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=settings['sessionKey'], raiseAllErrors=False, postargs=postArgs)

        if response.status != 200:
            logger.info("setOrganization - Failure Setting [organzation], response.status=" + str(response.status));
            print ("FAILURE")
        else:
            logger.info("xmSetupComplete - Success Setting [organization]");

            # Issue restart message.
            #postargs = {'severity': 'warn', 'name': 'restart_required', 'value': 'Splunk must be restarted for SCM Framework Setup to take effect.'}
            #response, content = splunk.rest.simpleRequest('/services/messages', self.getSessionKey(), postargs=postargs)

            # Issue reload
            endpoint = '/servicesNS/-/search/admin/localapps/_reload'
            response, content = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=settings['sessionKey'], raiseAllErrors=False)
            if response.status != 200:
                logger.info("setOrganization - Failure Reloading App Conf File  response.status=" + str(response.status));
                print ("FAILURE")
            else:
                logger.info("setOrganization - Success Reloading App Conf File");
                print ("SUCCESS")

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        si.generateErrorResults(e)
