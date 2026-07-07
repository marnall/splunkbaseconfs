import logging
import os
import sys
import json
import cherrypy
import splunk
import splunk.appserver.mrsparkle.controllers as controllers
import splunk.appserver.mrsparkle.lib.util as util
import splunk.util
import splunk.clilib.cli_common
import shutil
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
from splunk.appserver.mrsparkle.lib import jsonresponse
import urllib
import httplib2
from splunk.rest import simpleRequest
import base64
import requests

import subprocess
import shlex
import logging.handlers
import splunk.rest
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunk.clilib import cli_common as cli
import time
import tempfile
import uuid
import splunk.entity as entity
from subprocess import call
import splunk.entity, splunk.Intersplunk 

from splunk.persistconn.application import PersistentServerConnectionApplication
from splunk.util import normalizeBoolean

import urllib3
urllib3.disable_warnings()

'''
# !!!!! DEBUG !!!!
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
import splunk_debug as dbg
dbg.enable_debugging(timeout=25)
#################
'''

splunk_home = os.environ['SPLUNK_HOME']

def setup_logger():
    logger = logging.getLogger('samrt_services')
    logger.propagate = False
    logger.setLevel(logging.DEBUG)

    file_handler = logging.handlers.RotatingFileHandler(
                    make_splunkhome_path(['var', 'log', 'splunk', 
                                          'automatic-applications-assessment.log']),
                                        maxBytes=25000000, backupCount=5)

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    return logger

logger = setup_logger()

class VerifyStatus(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    def check_status(self, request_id,token):
        results_file = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','scma','lookups','scma_aaa_results.csv')
        reports_folder = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','scma','appserver','static','reports')

        if not os.path.exists(reports_folder) :
            os.mkdir(reports_folder)
            
        base_url = "https://appinspect.splunk.com"
        status_url = base_url + "/v1/app/validate/status/"+request_id
        
        headers = {"Authorization": "bearer {}".format(token), "max-messages": "all"}

        try:
            # start validating apps
            valresponse = requests.get( status_url, verify=False, headers=headers)  # nosemgrep
            valresponse_json = valresponse.json()

            if valresponse_json['status'] not in ['PROCESSING'] :
                # open the csv file to update the status
                index= -1
                newline = ""
                appname = ""
                f=open(results_file, "r")
                lines = f.readlines()
                for idx,line in enumerate(lines) :

                    # if the request id is in the file and it was in process status, update it
                    if line.find(request_id) > 0 :
                        if 'PROCESSING' in line :
                            newline = line.replace('PROCESSING',valresponse_json['status'])
                            if "info" in valresponse_json:
                                values = newline.split(",")
                                appname = values[4]
                                values[5] = str(valresponse_json['info']['error'])
                                values[6] = str(valresponse_json['info']['failure'])
                                values[7] = str(valresponse_json['info']['skipped'])
                                values[8] = str(valresponse_json['info']['manual_check'])
                                values[9] = str(valresponse_json['info']['not_applicable'])
                                values[10] = str(valresponse_json['info']['warning'])
                                values[11] = str(valresponse_json['info']['success'])
                                newline = values[0]+","+values[1]+","+values[2]+","+values[3]+","+values[4]+","+values[5]+","+values[6]+","+values[7]+","+values[8]+","+values[9]+","+values[10]+","+values[11]+","+values[12]+","+values[13]+","+values[14]+","+values[15]+","+values[16]+","+values[17]

                            index=idx

                if index > 0 :
                    fi=open(results_file, "w")
                    if '\n' not in newline:
                        newline = newline + "\n"

                    lines[index] = newline
                    fi.writelines(lines)
                    fi.close()

                    if valresponse_json['status'] in ['SUCCESS'] :
                        
                        header_report = {"Authorization": "bearer {}".format(token), "max-messages": "all", "Content-Type": "text/html"}
                        report_url = base_url + "/v1/app/report/"+request_id
                        valresponse = requests.request("GET", report_url, verify=False, headers=header_report)  # nosemgrep
                        o = open(os.path.join(reports_folder,appname + "_" + request_id+".html"),"w+")
                        o.write(valresponse.content.decode('utf-8'))
            
            return valresponse_json['status']

        except Exception as e :
            logger.error("Something Bad happened: {}".format(e))
            print("------ Error Inspecting : " + app_name)
            return "ERROR"


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

        # Parse the arguments
        args = self.parse_in_string(in_string)


        results_file = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','scma','lookups','scma_aaa_results.csv')


        f=open(results_file,"r")
        requests=f.readlines()

        token = args['query_parameters']["token"]
        jobid = args['query_parameters']["jobid"]

        isProcessing = 1
        while isProcessing > 0 :
            isProcessing = 0
            for idx,request in enumerate(requests) :
                if idx != 0 and (request.find(',') != -1):
                    # get reuest id
                    if request.split(',')[0] == jobid :
                        if request.split(',')[3] == "PROCESSING" :
                            if self.check_status(request.split(',')[2],token) in ["PROCESSING"] :
                                isProcessing = 1

            if isProcessing == 1:
                time.sleep(5)

        return {'payload': 'done', 'status': 200}

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
