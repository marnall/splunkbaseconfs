import splunk
import splunk.util

import os
import sys


import httplib2

import splunk.clilib.cli_common as comm
import splunk.Intersplunk as si

from common import get_sos_server
import time
import socket
import subprocess
import os
import sys
import multiprocessing
import re

try:
    import ctypes
except:
    pass

_time=time.time()
sos_server=get_sos_server()


def running_as_root():
    #NOTE this does not check Windows

    try:
        if os.geteuid() == 0:
            return  True
        return False
    except Exception, e:
        return "Nil"


def using_default_cert():
    cert_conf = comm.getConfKeyValue('web', 'settings', 'caCertPath')
    cert_path = os.path.join( os.environ['SPLUNK_HOME'], cert_conf )
    cert_info = os.popen('openssl x509 -in ' + str(cert_path) + ' -noout -text').read()
    if cert_info.find("SplunkCommonCA") != -1:
            return True
    return False

def ssl_on_web():
    if comm.getWebConfKeyValue(comm.KEY_WEB_SSL).lower() == "true":
        return True
    else:
        return False

def using_default_pass():
    url = comm.getMgmtUri() +  '/services'
    # Create http request object
    h = httplib2.Http(disable_ssl_certificate_validation=True)
        
        
   # Try default creds
    h.add_credentials('admin', 'changeme')
    # Store response
    http_response = str(h.request(url, "GET"))
    if http_response.find("200") > -1:
        return True
    return False

def ssl_on_splunkd():
    if  comm.getConfKeyValue('server', 'sslConfig', 'enableSplunkdSSL'):
        return True
    else:
        return False


###################################
# main function
####################################
if __name__ == '__main__':
    try:
        keywords,options = si.getKeywordsAndOptions()
        if len(keywords) > 0:
            si.generateErrorResults('This command takes no arguments.')
            exit(0)
        conffile = ' '.join(keywords)

        results = []
        results.append({
            "sos_server" : sos_server,
            "running_as_root" : running_as_root(),
            "using_default_cert" : using_default_cert(),
            "ssl_on_web" : ssl_on_web(),
            "using_default_pass" : using_default_pass(),
            "ssl_on_splunkd" : ssl_on_splunkd(),
            "_time" : _time,
            "source" : "securityinfo",
            "sourcetype" : "securityinfo"})

        si.outputResults(results)

    except Exception, e:
        import traceback
        stack =  traceback.format_exc()
        si.generateErrorResults("Error '%s'. %s" % (e, stack))

