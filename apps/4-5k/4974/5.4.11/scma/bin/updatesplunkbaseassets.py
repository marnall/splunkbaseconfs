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
import tarfile
import os.path
from datetime import datetime

import urllib3
urllib3.disable_warnings()


splunk_home = os.environ['SPLUNK_HOME']

'''
# !!!!! DEBUG !!!!
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
import splunk_debug as dbg
dbg.enable_debugging(timeout=25)
#################
'''

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

class UpdateSplunkbaseAssets(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    ### Function that does an http get to download the list of apps that returned in JSON format
    def get_apps(self, limit, offset):

        ### Base URL to download list of apps
        base_url = "https://splunkbase.splunk.com/api/v1/app/?order=latest&limit=" + \
            str(limit) + "&include=support,created_by,categories,icon,screenshots,rating,releases,documentation,releases.content,releases.splunk_compatibility,releases.cim_compatibility,releases.install_method_single,releases.install_method_distributed,release,release.content,release.cim_compatibility,release.install_method_single,release.install_method_distributed,release.splunk_compatibility" + "&offset="

        ### Build the url to download the list of apps
        url = base_url + str(offset)

        valresponse = requests.request("GET", url, verify=False)  # nosemgrep
        valresponse_json = {}
        if valresponse.status_code == 200 :
            valresponse_json = valresponse.json()

        ### Return the json data
        return valresponse_json

    def write_to_lookup(self, apps, lookup_file, timestamp):

        for app in apps:
            
            csv_str = timestamp+ "," + str(app['uid']) +","+ app['appid'] +","+ app['title'] +","+app['updated_time'] +","+str(app['appinspect_passed']) +","+app['path']
            
            if app['release'] is None:
                csv_str += ",N/A"
            else :
                csv_str += ","+app['release']['title']

            if len (app['releases']) == 0 :
                csv_str += ",N/A,N/A\n"
            else :
                csv_str += ","+ json.dumps(app['releases'][0]['splunk_compatibility']).replace("]","").replace("[","").replace(","," ").replace("\""," ") +","+json.dumps(app['releases'][0]['product_compatibility']).replace("]","").replace("[","").replace(","," ").replace("\""," ")+"\n"
            
            lookup_file.write(csv_str);
        

    def iterate_apps(self):
        offset = 0
        limit = 100
        counter = 0
        total = 1
        splunkbase_file = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','scma','lookups','splunkbase_apps')
        f=open(splunkbase_file, "w+")
        f.write("timestamp,uid,appid,title,updated_time,appinspect_passed,path,release,compatibility,platform\n")

        # datetime object containing current date and time
        now = datetime.now()

        # dd/mm/YY H:M:S
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

        while counter < total:
            data = self.get_apps(limit, offset)  ### Download initial list of the apps    
            total = data['total']                       ### Get the total number of apps
            apps = data['results']                      ### Get the results
            self.write_to_lookup(apps,f, dt_string)
            offset += limit
            counter = counter + 100

        f.close()
        
    # Handle a syncronous from splunkd.
    def handle(self, in_string):
        """
        Called for a simple synchronous request.
        @param in_string: request data passed in
        @rtype: string or dict
        @return: String to return in response.  If a dict was passed in,
        it will automatically be JSON encoded before being returned.
        """
        # Parse the arguments
        args = self.parse_in_string(in_string)

        # Get the user information
        session_key = args['session']['authtoken']

        self.iterate_apps()
        
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
