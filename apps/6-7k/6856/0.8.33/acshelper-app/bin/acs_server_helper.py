import sys
import os
import requests
from datetime import datetime
import uuid
import splunk
import splunk.util
import splunk.clilib.cli_common
import shutil
import gzip
import tarfile
import splunk.Intersplunk
from shutil import ignore_patterns
import errno

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import splunklib.client as client

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

from splunk.persistconn.application import PersistentServerConnectionApplication
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators



# !!!!! DEBUG !!!!
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
import splunk_debug as dbg
dbg.enable_debugging(timeout=25)
#################



splunk_home = os.environ['SPLUNK_HOME']
LOG_LEVEL = logging.INFO
LOG_FILE_NAME = "acshelper.log"

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

logger = setup_logger()


class ACS_Server_Helper(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    # Handle a syncronous from splunkd.
    def handle(self, in_string):
        """
        Called for a simple synchronous request.
        @param in_string: request data passed in
        @rtype: string or dict
        @return: String to return in response.  If a dict was passed in,
                 it will automatically be JSON encoded before being returned.
        """

        dbg.set_breakpoint()

        acs_url = "https://admin.splunk.com/"

        # Parse the arguments
        args = self.parse_in_string(in_string)
        
        stackname = ""
        if "stackname" in args['form_parameters'] :
            stackname = args['form_parameters']['stackname']
            if "stg-" in stackname :
                acs_url = "https://staging.admin.splunk.com/"
        
        action = ""
        if "action" in args['form_parameters'] :
            action = args['form_parameters']['action']

        
        stacktoken = ""
        if "token" in args['form_parameters'] :
            stacktoken = args['form_parameters']['token']

        headers = {
                            'Authorization': 'Bearer '+stacktoken,
                            'User-Agent': 'ACS-Helper'
                        }

        result = ""
        response = {}
        
        if action == "status" :
            response = requests.get(acs_url+stackname+'/adminconfig/v2/status', headers=headers)
            if response != None :
                if response.status_code == 200 :
                    result = response.text
                else :
                    result = "ERROR"
                    
        elif action == "restart" :
            response = requests.post(acs_url+stackname+'/adminconfig/v2/restart-now', headers=headers)
                    
            if response != None :
                if response.status_code == 200  or response.status_code == 202:
                    time.sleep(10)
                    while True :
                        response = requests.get(acs_url+stackname+'/adminconfig/v2/status', headers=headers)
                        if response != None :
                            if response.status_code == 200 :
                                text = json.loads(response.text)
                                result = "SUCCESS"
                                break
                            else :
                                time.sleep(10)



                else :
                    result = "ERROR"
        
        
        logger.info("[SERVER HELPER] action="+action+" server="+stackname+" global_status=completed")


        return {'payload': result, 'status': response.status_code}

    def handleStream(self, handle, in_string):
        """
        For future use
        """
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")

    def done(self):
        """
        Virtual method which can be optionally overridden to receive a
        callback after the request completes.
        """
        pass

    def convert_to_dict(self, query):
        """
        Create a dictionary containing the parameters.
        """
        parameters = {}

        for key, val in query:

            # If the key is already in the list, but the existing entry isn't a list then make the
            # existing entry a list and add thi one
            if key in parameters and not isinstance(parameters[key], list):
                parameters[key] = [parameters[key], val]

            # If the entry is already included as a list, then just add the entry
            elif key in parameters:
                parameters[key].append(val)

            # Otherwise, just add the entry
            else:
                parameters[key] = val

        return parameters

    def parse_in_string(self, in_string):
        """
        Parse the in_string
        """

        params = json.loads(in_string)

        params['method'] = params['method'].lower()

        params['form_parameters'] = self.convert_to_dict(params.get('form', []))
        params['query_parameters'] = self.convert_to_dict(params.get('query', []))

        return params
