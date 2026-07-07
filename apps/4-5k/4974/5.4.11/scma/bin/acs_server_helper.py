import sys
import requests
from datetime import datetime
import uuid
import splunk
import splunk.util
import splunk.clilib.cli_common
import shutil
import gzip
import tarfile
from shutil import ignore_patterns
import errno

if sys.version_info >= (3, 0):
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError, URLError
    import time, os, re, json, urllib.request, urllib.parse, urllib.error, requests
    import logging, logging.handlers
    import splunk.rest as rest, splunk.Intersplunk as si
else:
    from urllib2 import urlopen, Request, HTTPError, URLError
    import sys, time, os, re, json, urllib, requests
    import logging, logging.handlers
    import splunk.rest as rest, splunk.Intersplunk as si

'''
# !!!!! DEBUG !!!!
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
import splunk_debug as dbg
dbg.enable_debugging(timeout=25)
#################
'''

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


splunk_home = os.environ['SPLUNK_HOME']
LOG_LEVEL = logging.INFO
LOG_FILE_NAME = "rad.log"

def setup_logger():  # setup logging
    global SPLUNK_HOME, LOG_LEVEL, LOG_FILE_NAME
    if 'SPLUNK_HOME' in os.environ:
        SPLUNK_HOME = os.environ['SPLUNK_HOME']

    log_format = "%(asctime)s %(levelname)-s\t%(module)s[%(process)d]:%(lineno)d - %(message)s"
    logger = logging.getLogger('v')
    logger.setLevel(LOG_LEVEL)

    l = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, 'var', 'log', 'splunk', LOG_FILE_NAME), mode='a', maxBytes=1000000, backupCount=2)
    l.setFormatter(logging.Formatter(log_format))
    logger.addHandler(l)

    # ..and (optionally) output to console
    logH = logging.StreamHandler()
    logH.setFormatter(logging.Formatter(fmt=log_format))
    # logger.addHandler(logH)

    logger.propagate = False
    return logger

def die(msg):
    logger.error(msg)
    exit(msg)


if __name__ == '__main__':
    #global DEBUG_MODE


    logger = setup_logger()
    logger.info('starting..')

    #dbg.set_breakpoint()

    try:

        
        # Parse the arguments
        args = dict()
        # get checks name from args if exists
        for x, opt in enumerate(sys.argv):
            if x > 0 :
                args[opt.split("=")[0]] = opt.split("=")[1]


        stackname = ""
        if "server" in args :
            stackname = args['server']
        
        action = ""
        if "action" in args :
            action = args['action']

        stacktoken = ""
        if "stacktoken" in args :
            stacktoken = args['stacktoken']

        action_output = {
                        '_time': time.time(),
                        'stack': stackname,
                        'action': action 
                    }

        result_bundle = []
        headers = {
                            'Authorization': 'Bearer '+stacktoken
                        }

        if action == "status" :
            response = requests.get('https://staging.admin.splunk.com/'+stackname+'/adminconfig/v2/status', headers=headers, verify=False)  # nosemgrep
            if response != None :
                if response.status_code == 200 :
                    action_output["result"] = response.text
                else :
                    action_output["result"] = "ERROR"
                    
        elif action == "restart" :
            response = requests.post('https://staging.admin.splunk.com/'+stackname+'/adminconfig/v2/restart-now', headers=headers, verify=False)  # nosemgrep
                    
            if response != None :
                if response.status_code == 200  or response.status_code == 202:
                    time.sleep(10)
                    while True :
                        response = requests.get('https://staging.admin.splunk.com/'+stackname+'/adminconfig/v2/status', headers=headers, verify=False)  # nosemgrep
                        if response != None :
                            if response.status_code == 200 :
                                text = json.loads(response.text)
                                action_output["result"] = "SUCCESS"
                                break
                            else :
                                time.sleep(10)



                else :
                    action_output["result"] = "ERROR"
        
        result_bundle.append(action_output)
        si.outputResults(result_bundle)
        logger.info("[SERVER HELPER] action="+action+" server="+stackname+" global_status=completed")

    except Exception as e:
        logger.error("[SERVER HELPER] action="+action+" server="+stackname+" global_status=Error")
        si.generateErrorResults(e)
        
