import requests
import logging
import os
import json
import sys
import logging.handlers

from splunk.persistconn.application import PersistentServerConnectionApplication
import signal
import subprocess

'''
# !!!!! DEBUG !!!!
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
import splunk_debug as dbg
dbg.enable_debugging(timeout=25)
#################
'''

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


class Stack_Connect(PersistentServerConnectionApplication):
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

        #dbg.set_breakpoint()

        acs_url = "https://admin.splunk.com/"
        rest_url = ".splunkcloud.com:8089/"

        # Parse the arguments
        args = self.parse_in_string(in_string)
        
        token = ""
        if "token" in args['form_parameters'] :
            token = args['form_parameters']['token']
        
        stackname = ""
        if "stackname" in args['form_parameters'] :
            stackname = args['form_parameters']['stackname']
            if "stg-" in stackname :
                acs_url = "https://staging.admin.splunk.com/"
                rest_url = ".stg.splunkcloud.com:8089/"
        
        headers = {
                'Authorization': 'Bearer '+ token,
                'User-Agent': 'ACS-Helper'
            }
        
        response = requests.get(acs_url+stackname+'/adminconfig/v2/status', headers=headers)
        
        if response.status_code == 404 :
            return {'payload': "", 'status': 404}
        elif response.status_code == 401 :
            return {'payload': "", 'status': 401}
        
        elif response.status_code == 200 :
            payload = json.loads(response.text)
            payload["infrastructure"]["APAV"] = "1"
            '''
            # get APAV status
            payload = json.loads(response.text)
            apav_endpoint = 'servicesNS/-/100-whisper/configs/conf-server/applicationsManagement'

            if payload["infrastructure"]["stackType"] == "classic" :
                apav_endpoint = '/servicesNS/-/dmc/configs/conf-dmc_agent'

            response = requests.get("https://"+stackname+rest_url+apav_endpoint+"?output_mode=json", headers=headers, verify=False)

            if "entry" in json.loads(response.text) :
                if isinstance(json.loads(response.text)["entry"],list) :
                    if "content" in json.loads(response.text)["entry"][0] :
                        if "private_app_vetting_global" in json.loads(response.text)["entry"][0]["content"] :
                            payload["infrastructure"]["APAV"] = json.loads(response.text)["entry"][0]["content"]["private_app_vetting_global"]
                else :
                    if "content" in json.loads(response.text)["entry"] :
                        if "private_app_vetting_global" in json.loads(response.text)["entry"]["content"] :
                            payload["infrastructure"]["APAV"] = json.loads(response.text)["entry"]["content"]["private_app_vetting_global"]
            '''

                
            return {'payload': payload, 'status': 200}
            
        return {'payload': "", 'status': response.status_code}

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
