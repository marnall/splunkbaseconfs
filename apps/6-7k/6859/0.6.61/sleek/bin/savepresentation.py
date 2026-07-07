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
from xml.dom import minidom
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
                                          'sleek.log']),
                                        maxBytes=25000000, backupCount=5)

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    return logger

logger = setup_logger()

class SavePresentation(PersistentServerConnectionApplication):
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

        # Parse the arguments
        args = self.parse_in_string(in_string)

        # Get the user information
        session_key = args['session']['authtoken']

        payload = json.loads(args['query_parameters']["payload"].replace("'",'"'))

        if payload["prezID"]=="" :
            payload["prezID"] = str(uuid.uuid4())
        
        if not os.path.exists(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','sleek','appserver','static','presentations')) :
            os.mkdir(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','sleek','appserver','static','presentations'))

        f = open(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','sleek','appserver','static','presentations',payload["prezID"]), "w+")
        f.write(json.dumps(payload))
        f.close()
        return {'payload': payload["prezID"] , 'status': 200}

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
