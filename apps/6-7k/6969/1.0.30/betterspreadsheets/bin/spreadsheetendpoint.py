import sys
import logging
import json
import time
from datetime import datetime
import os
import splunk
import splunk.rest as rest
import base64
import fnmatch
from future.moves.urllib.parse import unquote
import subprocess
import ssl

from splunklib import client
from splunklib import results
from solnlib import credentials
import jsonpickle

# Setup environment paths
SPLUNK_HOME = os.environ['SPLUNK_HOME']
app_name = "spreadsheetendpoint"

#sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

import license_handler
import onedrive_settings
import search_reader
import spreadsheet_generator

# Logging Setup
def setup_logging():
    logger = logging.getLogger("a")
    file_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, 'var', 'log', 'splunk', app_name + ".log"), mode='a', maxBytes=25000000, backupCount=2)
    formatter = logging.Formatter("%(created)f log_level=%(levelname)s, pid=%(process)d, line=%(lineno)d, %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.setLevel("DEBUG")
    return logger

logger = setup_logging()

import splunk.entity as entity
import splunk.auth
from spreadsheet_generator import safe_open_wb, safe_open_w


ERROR_MSG = "Unable to serve the request."

class ArgError(Exception):
    pass

class TimeoutError(Exception):
    pass

class spreadsheetHandler(splunk.rest.BaseRestHandler):

    def handle_GET(self):
        logger.debug("GET request")
        self._handleRequest()

    def handle_POST(self):
        logger.debug("POST request")
        # If POST logic is only for updating logo or test endpoints, you can route here
        try:
            logger.debug(jsonpickle.dumps(self.request))
            logger.debug(jsonpickle.dumps(self.request["form"]))

            if "test" in self.request["query"].keys():
                # Just a test endpoint
                self.response.setHeader('content-type', 'application/json')
                self.response.setHeader('cache-control', 'max-age=0, must-revalidate')
                self.response.write('{"entry": [{"content": {"logoupload":"ok"}}]}')
                self.response.setStatus(200)

            elif "install_logo" in self.request["query"].keys():
                imgdata = base64.urlsafe_b64decode(self.request["form"])
                localpath = os.path.join(os.path.dirname(__file__), '..', 'local')
                with safe_open_wb(os.path.join(localpath, "customlogo")) as f:
                    f.write(imgdata)

                self.response.setHeader('content-type', 'application/json')
                self.response.setHeader('cache-control', 'max-age=0, must-revalidate')
                self.response.write('{"entry": [{"content": {"logoupload_post":"ok"}}]}')
                self.response.setStatus(200)

        except Exception as e:
            logger.exception("Exception in POST method.")
            # Return an error if needed
            pass

    def _handleRequest(self):
        userName = self.request["userName"] if "userName" in self.request else "unknown"
        transaction = str(time.time())
        logger.debug(self.method)
        logger.debug("transaction=" + transaction + " user=" + userName + " handle request=" + str(json.dumps(self.request)))

        if not self._initialize():
            logger.debug(str(self.request))
            return

        if self.method == 'GET':
            # Handle all GET requests
            try:
                requestpath = self.request["path"].split("/")
                query = self.request["query"]
                logger.debug(query)

                # Extract auth token
                authToken = None
                if "cookie" in self.request["headers"].keys():
                    cookies = (dict(i.split('=', 1) for i in self.request["headers"]["cookie"].split('; ')))
                    for key, value in cookies.items():
                        if fnmatch.fnmatch(key, "splunkd_*"):
                            authToken = value
                elif self.request["systemAuth"]:
                    authToken = self.request["systemAuth"]
                
                logger.debug(authToken)

                localpath = os.path.join(os.path.dirname(__file__), '..', 'local')
                resourcepath = os.path.dirname(__file__)

                # Read formatting from conf
                formating = spreadsheet_generator.get_formatting_settings(authToken)

                # License handling
                licensestatus, cn, licensemtime, enddate, triallicense = license_handler.check_license(localpath, resourcepath, transaction, userName, logger)

                # Onedrive config retrieval or update
                if "license_status" in query:
                    license_handler.respond_license_status(self.response, licensestatus, cn, licensemtime, enddate, triallicense)
                    return

                elif "install_license" in query:
                    license_handler.install_license(self.response, query["install_license"], localpath, logger)
                    return

                elif "update_config" in query:
                    # Update formatting config
                    spreadsheet_generator.update_formatting_config(self.response, authToken, query, logger)
                    return

                elif "get_config" in query:
                    spreadsheet_generator.respond_formatting_config(self.response, formating)
                    return

                elif "get_onedriveconfig" in query:
                    onedrive_settings.get_onedriveconfig(self.response, authToken, logger)
                    return

                elif "set_onedriveconfig" in query:
                    onedrive_settings.set_onedriveconfig(self.response, authToken, query, logger)
                    return

                elif "install_logo" in query:
                    spreadsheet_generator.install_logo_get_method(self.response, query, localpath, logger)
                    return

                elif "get_logo" in query:
                    spreadsheet_generator.get_logo(self.response, localpath, resourcepath, logger)
                    return

                # If license is valid
                if licensestatus == "pass":

                    # connect to Splunk
                    service = client.connect(
                        splunkToken=authToken, 
                        host='localhost', 
                        port='8089', 
                        owner="-", 
                        app="-"
                    )

                    # Process the search results 
                    records, jobinfo, filename = search_reader.load_results(service, query, logger)

                    # Generate spreadsheet
                    spreadsheet_generator.generate_spreadsheet(self.response, authToken, userName, records, jobinfo, filename, formating, licensestatus, cn, triallicense, logger)

                else:
                    # License fail
                    license_handler.respond_license_status(self.response, licensestatus, cn, licensemtime, enddate, triallicense)

            except Exception as e:
                errorMsg = str(e)
                logger.info("transaction=" + transaction + " user=" + userName + " errorMsg=" + errorMsg)
                self._outputError([errorMsg])
                import traceback
                stack = traceback.format_exc()
                logger.error(stack)

        self._respond()

    def _initialize(self):
        logger.debug("setting up shop")
        logger.debug(jsonpickle.dumps(self.request))
        logger.debug(self.method)
        logger.debug(jsonpickle.dumps(self))
        return True

    def _respond(self):
        # If needed, finalize response
        pass

    def _outputTimeoutError(self, message):
        self.response.write("Generation timed out: %s" % message)
        self.response.setHeader('content-type', 'text/html')
        self.response.setStatus(408)

    def _outputError(self, errorDetailsArray):
        if errorDetailsArray is None:
            errorDetailsArray = [""]
        outputErrorMsg = "<b>" + "<br/><br/>".join(errorDetailsArray) + "</b>"
        outputErrorMsg += "<br/>Request details: " + json.dumps(self.request)
        self.response.write(outputErrorMsg)
        self.response.setHeader('content-type', 'text/html')
        self.response.setStatus(400)
