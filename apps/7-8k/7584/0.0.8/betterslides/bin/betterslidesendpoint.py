import sys
import logging
import time
import json
from io import BytesIO
import io
import re
import os
import splunk
import splunk.rest as rest
import splunk.entity as entity
import splunk.auth
import fnmatch
import urllib.parse
import subprocess
import ssl
import datetime
from datetime import date
import requests
import base64
import csv
import gzip
from typing import Optional
from future.moves.urllib.parse import unquote

#############################
# v 0.1.3
#############################

app_name = "betterslides"
SPLUNK_HOME = os.environ["SPLUNK_HOME"]

# load own libs from ../lib
#sys.path.append(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib import client
from splunklib import results
from solnlib import credentials
import jsonpickle

# From here: http://dev.splunk.com/view/logging/SP-CAAAFCN
def setup_logging():
    """set up the logger for the handler"""
    logger = logging.getLogger("a")
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(SPLUNK_HOME, "var", "log", "splunk", app_name + ".log"),
        mode="a",
        maxBytes=25000000,
        backupCount=2,
    )
    formatter = logging.Formatter(
        "%(created)f %(levelname)s pid=%(process)d file=%(filename)s line=%(lineno)d %(message)s"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    # logger.setLevel("INFO");
    logger.setLevel("DEBUG")
    logger.info(f"initializing {app_name}")
    return logger


logger = setup_logging()
userName = ""  # initialize
transaction = ""

# for static includes like watermarks etc
resourcepath = os.path.dirname(__file__)
localpath = os.path.join(os.path.dirname(__file__), "..", "local")

try:
    # Determine the absolute path of the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
        
    # Append the script's directory to sys.path
    sys.path.append(script_dir)
    from dashboard_exporter import DashboardExporter
    logger.info("load library success")
except Exception as e:
    errorMsg = "Exception raised while trying to respond."
    import traceback
    stack = traceback.format_exc()
    logger.error(stack)
    logger.info(sys.path)

class ArgError(Exception):
    def __init__(self, message):
        super(ArgError, self).__init__(message)

    def __str__(self):
        return repr(self.value)


class TimeoutError(Exception):
    def __str__(self):
        return repr(self.value)


class betterslidesHandler(splunk.rest.BaseRestHandler):
    _title = "Untitled"

    def handle_GET(self):
        logger.info("GET request")
        self._handleRequest()

    def handle_POST(self):
        logger.info("POST request")
        self._handleRequest()

    def _handleRequest(self):
        userName = self.request["userName"]  # for nicer logging
        logger.info(self.method)
        transaction = str(time.time())

        if not self._initialize():
            # logger.debug(str(self.request))
            return

        if self.method == "POST":
            logger.info("handle POST request")
            logger.info(jsonpickle.dumps(self.request))
            logger.info(jsonpickle.dumps(self.request["form"]))

            self.response.setHeader("content-type", "application/json")
            self.response.setHeader("cache-control", "max-age=0, must-revalidate")
            self.response.write(
                '{"entry": [{"content": {"method":"post","status":"ok"}}]}'
            )
            self.response.setStatus(200)
            return True

        if self.method == "GET":
            logger.info("handle GET request")
            #logger.info(jsonpickle.dumps(self.request))

            try:
                # get auth token
                if "cookie" in self.request["headers"].keys():
                    cookies = dict(
                        i.split("=", 1)
                        for i in self.request["headers"]["cookie"].split("; ")
                    )

                    for key, value in cookies.items():
                        if fnmatch.fnmatch(key, "splunkd_*"):
                            authToken = value
                elif self.request["systemAuth"]:
                    authToken = self.request["systemAuth"]

                # log in using passed auth token
                service = client.connect(
                    splunkToken=authToken,
                    host="localhost",
                    port="8089",
                )

                """
                generate outputs
                """
                if "title" in self.request["query"].keys():
                    filename=self.request["query"]["filename"] + ".pptx"
                else:
                    filename="myslides.pptx"

                if "dashboards" in self.request["query"].keys():
                    logger.info("try to gather slides")
                    logger.info(self.request["query"]["dashboards"])
                    
                    # Split the string by semicolon
                    elements = self.request["query"]["dashboards"].split(';')
                    
                    # Remove any empty elements and strip whitespace from each element
                    dashboards = [elem.strip() for elem in elements if elem.strip()]

                    logger.info("instantiate own class")
                    exporter = DashboardExporter(authToken, logger)
                
                    # Initialize the presentation
                    exporter.initialize_presentation()

                    # Add slides for each dashboard
                    for dashboard in dashboards:
                        logger.info(f"Trying to export {dashboard}")
                        exporter.add_dashboard_slide(dashboard)

                    # Get the final presentation
                    pptx_bytes = exporter.get_presentation()

                    """
                    # Save the presentation to a file
                    with open("output_presentation.pptx", "wb") as f:
                        f.write(pptx_bytes.getbuffer())

                    import os

                    abspath = os.path.abspath(__file__)
                    dname = os.path.dirname(abspath)
                    os.chdir(dname)
                    logger.info(dname)

                    from pathlib import Path

                    contents = Path("output_presentation.pptx").read_bytes()
                    """

                    logger.info("try to service data")
                    disposition = "inline"
                    self.response.setHeader(
                        "content-disposition",
                        disposition + '; filename="' + filename + '"',
                    )
                    self.response.setHeader(
                        "content-type",
                        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    )
                    self.response.setHeader(
                        "cache-control", "max-age=0, must-revalidate"
                    )
                    self.response.write(pptx_bytes.getbuffer())
                    self.response.setStatus(200)

            except Exception as e:
                errorMsg = "Exception raised while trying to respond."
                self._outputError([errorMsg])
                import traceback

                stack = traceback.format_exc()
                logger.error(stack)
            return True

        self._respond()

    def _initialize(self):
        logger.info("setting up shop")
        """
        logger.info(jsonpickle.dumps(self.request))
        logger.info(self.method)
        logger.info(jsonpickle.dumps(self))
        """
        return True

    def _respond(self):
        logger.info("handling response")
        logger.info(self.response)
        # save and write out the file
        try:
            """ """

        except Exception as e:
            errorMsg = "Exception raised while trying to respond."
            self._outputError([errorMsg])
            import traceback

            stack = traceback.format_exc()
            logger.error(stack)
            return False
        return True

    def _outputTimeoutError(self, message):
        logger.info(
            "transaction="
            + transaction
            + " user="
            + userName
            + " action=outputTimeoutError"
        )
        self.response.write("timeout")
        self.response.setHeader("content-type", "text/html")
        self.response.setStatus(408)

    def _outputError(self, errorDetailsArray):
        logger.info(
            "transaction="
            + transaction
            + " user="
            + userName
            + " action=outputError errorDetails="
            + str(errorDetailsArray)
        )
        self.request["systemAuth"] = "-redacted-"
        self.request["headers"]["cookie"] = "-redacted-"
        # outputErrorMsg = ERROR_MSG + "<br/><ul>"
        if errorDetailsArray is None:
            errorDetailsArray = [""]  # rather print empty nothingness then fail
        for errorDetail in errorDetailsArray:
            logger.info(
                "transaction="
                + transaction
                + " user="
                + userName
                + " errorDetail="
                + errorDetail
            )
            outputErrorMsg = "<b>" + errorDetail + "<br/><br/>"
        outputErrorMsg += "Request details: </b>" + json.dumps(self.request)
        self.response.write(outputErrorMsg)
        self.response.setHeader("content-type", "text/html")
        self.response.setStatus(400)
