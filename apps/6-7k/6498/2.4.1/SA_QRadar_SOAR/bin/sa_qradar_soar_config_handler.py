# -*- coding: utf-8 -*-
# pragma pylint: disable=unused-argument, no-self-use, import-error

# (c) Copyright IBM Corp. 2024. All Rights Reserved.

import csv
import json

# use the default splunk logger -> splunk/var/log/splunk/python.log
import logging as logger
import os
import sys
import traceback

# import your required python modules
import requests
import splunk
import splunk.admin as admin

# contains the services for read/write to bundle system
import splunk.bundle as bundle
import splunk.entity as entity

# add . to the system path
sys.path.insert(0, os.path.dirname(__file__))
from resilient_client import ResilientClient

# Do not change the import order
from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk_sdk_utils import SplunkSdkUtils

sys.path.append(make_splunkhome_path(["etc", "apps", "Splunk_SA_CIM", "lib"]))
from cim_actions import ModularAction

# add ../lib to the system path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import splunklib
import splunklib.client as client

# Get the SA constants.
from app_constants import SA_ACTION_NAME, SA_APP_NAME

# class we will extend when making the custom endpoint handler
from splunk.persistconn.application import PersistentServerConnectionApplication

logger = ModularAction.setup_logger("qradar_soar_config_handler")

"""
    handleList method: lists configurable parameters in the configuration page
    corresponds to handleractions = list in restmap.conf

    handleEdit method: controls the parameters and saves the values
    corresponds to handleractions = edit in restmap.conf
"""


class QRadarSOARConfigHandler(PersistentServerConnectionApplication):
    """
    Set up supported arguments
    """

    APP_NAME = SA_APP_NAME
    ACTION_NAME = SA_ACTION_NAME

    # static Splunk endpoints
    MSG_URL = "/servicesNS/nobody/" + APP_NAME + "/messages"
    ALERT_URL = "/servicesNS/nobody/" + APP_NAME + "/data/ui/alerts/" + ACTION_NAME
    STATIC_DATA = os.path.join(
        os.environ["SPLUNK_HOME"], "etc", "apps", APP_NAME, "local/data"
    )

    splunksdk = SplunkSdkUtils(appName=APP_NAME, logger=logger)
    resilient_client = None
    service = None

    success = False

    # command_line and command_arg are passed to the handler from upstream
    # we must accept them in init and call init of PersistentServerConnectionApplication
    def __init__(self, _command_line, _command_arg, **kwargs):
        # PersistentServerConnectionApplication.__init__(self)
        super(PersistentServerConnectionApplication, self).__init__()

    # handle() is a required method
    # we must use handle to return a payload to the script called
    def handle(self, in_string, **kwargs):
        # get session key from user (must be admin role)
        input = json.loads(in_string)
        sessionKey = input["session"]["authtoken"]

        # instantiate Splunk and Resilient clients
        self.resilient_client = ResilientClient(logger=logger)
        self.service = self.getSplunkClient(sessionKey)

        """
        form arrives with a somewhat convoluted structure.
        The json object gets cast to a list of lists with key, value pairs
        ie [["host", "myhost"], ["verify", "true"] ...]
        We compare these values to what"s in the conf file
        to ensure that the write action worked.
        """
        form = input["form"]
        setup_data = self.formToDict(form)

        # cast strings from setup to booleans
        setup_data["api_keys"] = self.stringToBool(setup_data["api_keys"])
        setup_data["duplicates"] = self.stringToBool(setup_data["duplicates"])

        # verify can be True (boolean) or the path to the certificate (string) -> Can"t allow False (insecure connection)
        setup_data["verify"] = (
            True
            if setup_data["verify"] in ("1", "", None, "True", "true")
            else setup_data["verify"]
        )

        password = setup_data["secret"]

        logger.info("Received setup data.")
        logger.info(setup_data)

        nulls = self.checkForEmpty(setup_data)
        if nulls:
            text = "Empty field detected in the configuration. Please supply all values and ensure the information is correct."
            return self.formatResponse(False, text)

        try:
            # test the connection to QRadar SOAR
            self.testConnection(setup_data, password)
        except requests.exceptions.SSLError as e:
            # Log the error, post a message to splunk, and report a failure to the UI
            logger.error("QRadar SOAR connection failed due to SSL Error.")
            logger.error(
                "Verify from config resulted in verify parameter [%s]",
                str(setup_data["verify"]),
            )
            logger.error(traceback.format_exc())
            msg = {
                "name": "QRadar SOAR configuration not saved due to SSLError when connecting to QRadar SOAR host."
            }
            self.service.post(self.MSG_URL, name=self.APP_NAME, value=msg)

            text = (
                "QRadar SOAR connection test failed.\n"
                + msg["name"]
                + "\nConsult $SPLUNK_HOME/var/log/splunk/qradar_soar_config_handler.log for details."
            )
            return self.formatResponse(False, text)

        except Exception as e:
            # Log the error, post a message to splunk, and report a failure to the UI
            logger.error("QRadar SOAR connection verification failed: " + str(e))
            logger.error(traceback.format_exc())
            msg = {"name": "Verify your credentials are correct."}
            self.service.post(self.MSG_URL, name=self.APP_NAME, value=msg)

            text = (
                "QRadar SOAR connection test failed due to an exception.\n"
                + msg["name"]
                + "\nConsult $SPLUNK_HOME/var/log/splunk/qradar_soar_config_handler.log for details."
            )
            return self.formatResponse(False, text)

        # gather the supported artifact types
        conf_data = self.splunksdk.getConfig(self.service)
        logger.info("Config Data From splunksdk")
        logger.info(conf_data)

        # get the artifact types from Resilient
        artifact_types = self.resilient_client.get_artifact_types()

        # store the current incident definitions from Resilient
        incident_file = self.saveResilientFields("incident", "resilient.json")
        # store the current artifact definitions from Resilient
        artifact_file = self.saveResilientFields("artifact", "resilient_artifact.json")

        # get field definitions from the incident file
        defs = self.resilient_client.get_resilient_field_defs(incident_file)

        # check if the recommended custom field is being used in the Res platform
        # log a warning if it isn"t.
        field_use = None
        if "properties.splunk_notable_event_id" not in defs:
            field_msg = """Warning: splunk_notable_event_id custom field not present in QRadar SOAR field definitions!\n
            Creating the splunk_notable_event_id custom field in QRadar SOAR is strongly encouraged
            in order to strengthen the relationship between QRadar SOAR and Splunk and to avoid duplicate
            case creation."""
            logger.warning(field_msg)
            field_use = False
        else:
            field_use = True

        # put the HTML together for the alert configuration wizard
        html = self.resilient_client.generate_alert_html(
            self.ACTION_NAME, defs, int(setup_data["num_artifacts"]), artifact_types
        )

        # POST the HTML to Splunk
        self.service.post(self.ALERT_URL, app=self.APP_NAME, **{"eai:data": html})

        # To make adhoc invocation of AR action work, ALL the fields must be added to the parameter
        # lists of the AR action.
        # So we extract a list of all the fields of an incident, and then
        # make sure each of them is added to the action parameter list.
        inc_fields = self.resilient_client.get_resilient_field_defs(incident_file)

        # Add param.mapping_" prefix to each field
        params = ["param.mapping_" + field for field in inc_fields]

        # Need fields for artifacts as well, because they appear in the Alert UI as well.
        for i in range(1, int(setup_data["num_artifacts"]) + 1):
            index = str(i)
            type = "param.artifact" + index + "type"
            value = "param.artifact" + index + "value"
            desc = "param.artifact" + index + "description"
            params.append(type)
            params.append(value)
            params.append(desc)

        ara_stanza = self.splunksdk.getAlertParamters(self.service, self.ACTION_NAME)

        self.splunksdk.updateAlertParameters(ara_stanza, params)

        # Success
        logger.info("All fields up-to-date.")
        logger.info("Setup process successfully completed.")

        text = "Successfully connected to QRadar SOAR. Configuration saved."
        if not field_use:
            text += "\n\n" + field_msg
        return self.formatResponse(True, text)

    def testConnection(self, conf, password):
        success = False
        useAPIKeys = conf["api_keys"]

        if useAPIKeys:
            # connect to QRadar SOAR with API keys
            success = self.resilient_client.connect(
                conf, conf["verify"], None, password
            )

        else:
            # connect to QRadar SOAR with username and password
            success = self.resilient_client.connect(conf, conf["verify"], password)

        return success

    def getSplunkClient(self, sessionKey):
        # instantiate a splunk client
        service = client.connect(token=sessionKey, autologin=True, app=self.APP_NAME)
        return service

    def getPassword(self, password_id):
        # get the secret stored for sa_qradar_soar admin
        password = self.splunksdk.getPassword(self.service, password_id)
        return password

    def saveResilientFields(self, field_type, outfile):
        """
        Gathers field data from Resilient and writes it to a file.

        :param field_type: (str) type of field to get from resilient, eg "incident" or "artifact"
        :param outfile: (str) file name to write the data to
        :return: the file containing the data
        """
        # Get the current field definitions from Resilient
        incfields = self.resilient_client.get_fields(field_type)
        # Save this to a file
        # Make sure the /local/data directory is there first as it may not be there on fresh install
        if not os.path.exists(self.STATIC_DATA):
            os.makedirs(self.STATIC_DATA)
        incident_file = os.path.join(self.STATIC_DATA, outfile)
        with open(incident_file, "w") as writefile:
            writefile.write(json.dumps(incfields))
        return incident_file

    @staticmethod
    def parseArtifactTypes(conf_data):
        """
        Takes data from the configuration file and parses the artifact types.
        Returns a list of artifact types to post to the eai HTML.
        """
        artifact_types = []
        for row in csv.reader(
            conf_data["artifact_types"].splitlines(), skipinitialspace=True
        ):
            artifact_types += row
        return artifact_types

    @staticmethod
    def formToDict(form):
        """
        Takes a list of lists (form data from a post request).
        Casts it to a dictionary.
        """
        form_dict = {}

        for item in form:
            key = item[0]
            val = item[1]
            form_dict[key] = val

        return form_dict

    @staticmethod
    def stringToBool(string):
        """
        convert true/false, 1/0 string inputs to a boolean variable
        """
        return True if string.lower() in ("1", "true") else False

    @staticmethod
    def checkForEmpty(dictionary):
        """
        Ensure there are no empty values in a dictionary
        """
        for k, v in dictionary.items():
            if dictionary[k] in (None, ""):
                return True
        return False

    @staticmethod
    def formatResponse(success, text, status=200):
        """
        Build a response to deliver to the UI (setup page)

        :param success: Boolean indicating success
        :param text: string detailing reason for success/failure. Displayed by browser in most cases.
        :param status: always give 200 so the browser continues to execute

        :return: standard payload that the splunk UI expects
        """

        payload = {"success": success, "text": text}

        return {"payload": payload, "status": status}
