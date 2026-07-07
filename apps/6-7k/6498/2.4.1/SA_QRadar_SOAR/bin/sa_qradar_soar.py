# -*- coding: utf-8 -*-
# pragma pylint: disable=unused-argument, no-self-use

# (c) Copyright IBM Corp. 2024. All Rights Reserved.

# Allow Python3 style printing in Python2
from __future__ import print_function

import csv
import gzip
import logging
import os
import sys
import time
import traceback

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
from app_constants import SA_APP_NAME

logger = ModularAction.setup_logger("qradar_soar_modalert")

# name of the custom field in QRadar SOAR to correlate back to the splunk event
CUSTOM_FIELD_NAME = "splunk_notable_event_id"


class EscalateEvent(ModularAction):
    """EscalateEvent"""

    artifacts = None
    resilient_client = None
    APP_NAME = SA_APP_NAME
    splunksdk = SplunkSdkUtils(appName=APP_NAME, logger=logger)
    PASSWORD_ID = None
    USE_API_KEYS = None
    STATIC_DATA = os.path.join(
        os.environ["SPLUNK_HOME"], "etc", "apps", APP_NAME, "local/data"
    )
    resilient_conf = None
    allGood = True
    customFieldConfigured = None
    artifactLimit = None

    def __init__(self, settings, logger, action_name=None):
        super(EscalateEvent, self).__init__(settings, logger, action_name)
        logger.info("Settings:" + str(settings))

        try:
            # instantiate a splunk client
            service = client.connect(token=self.session_key)
            self.resilient_conf = self.splunksdk.getConfig(service)

            # Boolean values come in from the Setup UI as 1 or 0
            # Cast them to True or False
            self.resilient_conf["duplicates"] = self.resilient_conf["duplicates"] == "1"
            self.resilient_conf["api_keys"] = self.resilient_conf["api_keys"] == "1"

            # verify can be True (boolean) or the path to the certificate (string) -> Can't allow False (insecure connection)
            self.resilient_conf["verify"] = (
                True
                if self.resilient_conf["verify"] in ("1", "", None, "True", "true")
                else self.resilient_conf["verify"]
            )

            # get the max number of artifacts allowed
            self.artifactLimit = int(self.resilient_conf["num_artifacts"])

            # determine whether to connect with API keys or not
            self.USE_API_KEYS = self.resilient_conf["api_keys"]
            # concatenate standard StoragePassword naming convention from the .conf
            self.PASSWORD_ID = "{0}_{1}:{2}:".format(
                self.APP_NAME, self.resilient_conf["host"], self.resilient_conf["user"]
            )

            if sys.version_info.major > 2:
                logger.info("QRadar SOAR conf: " + str(self.resilient_conf))
            else:
                logger.info(
                    "QRadar SOAR conf: {"
                    + "".join(
                        "u'%s': u'%s', " % (k, v)
                        for k, v in self.resilient_conf.iteritems()
                    )
                    + "}"
                )
        except Exception as e:
            logger.error(e)
            raise Exception(
                "Failed to get the QRadar SOAR configuration.\n"
                + traceback.format_exc()
            )

        try:
            # set limit for number of events this action can handle each time it is triggered
            self.limit = int(self.resilient_conf["num_events"])
            if self.limit < 1 or self.limit > 30:
                self.limit = 30
        except Exception as e:
            self.limit = 30

    def validate(self, result):
        #
        # Nothing to validate at this point. We will put in default values if required informaiton is missing
        #
        # if len(self.rids)<=1:
        #    if not self.configuration.get("url"):
        #        raise Exception("Invalid URL requested")
        return

    def setArtifact(self, artifacts):
        self.artifacts = artifacts

    def checkStatus(self):
        return self.allGood

    def queryFieldMatch(self, resilient_client, field_name, field_value):
        query_uri = "/incidents/query?return_level=normal&field_handle={}".format(
            field_name
        )
        query = {
            "filters": [
                {
                    "conditions": [
                        {
                            "field_name": "properties.{}".format(field_name),
                            "method": "equals",
                            "value": field_value,
                        },
                        # below restricts the query to only return open incidents
                        {"field_name": "plan_status", "method": "equals", "value": "A"},
                    ]
                }
            ],
            "sorts": [{"field_name": "create_date", "type": "desc"}],
        }
        # In our case, the ResilientClient class contains a resilient_client
        # as an attribute, rather than extending the class.
        # Therefore we call resilient_client.resilient_client.example_method()
        res = resilient_client.resilient_client.post(query_uri, query)
        return res

    def dowork(self, result):
        """This is the main function create an incident for an event"""
        if sys.version_info.major > 2:
            logger.info("Configuration is: " + str(self.configuration))
        else:
            logger.info(
                "Configuration is: {"
                + "".join(
                    "u'%s': u'%s', " % (k, v) for k, v in self.configuration.iteritems()
                )
                + "}"
            )

        # instantiate a splunk client
        service = client.connect(token=self.session_key)

        # instantiate a resilient_client
        if self.resilient_client is None:
            self.resilient_client = ResilientClient(logger=logger)

        # get the password from StoragePasswords
        password = self.splunksdk.getPassword(service, self.PASSWORD_ID)

        # connect to Resilient using the desired method
        if self.USE_API_KEYS:
            # connect with api keys
            self.resilient_client.connect(
                self.resilient_conf, self.resilient_conf["verify"], None, password
            )
        else:
            # conn with user and password
            self.resilient_client.connect(
                self.resilient_conf, self.resilient_conf["verify"], password
            )

        try:
            configuration = self.configuration
            # Since we cannot delete fields from the mapping configuration endpoint,
            # a better indicator of whether the splunk_notable_event_id is used in the pairing
            # is to query for it directly in Resilient.
            # We check for this field every time in order to best know how to handle duplicates
            self.customFieldConfigured = self.resilient_client.is_field_present(
                "incident", CUSTOM_FIELD_NAME
            )
            if not self.customFieldConfigured:
                msg = """splunk_notable_event_id custom field not present in QRadar SOAR field definitions!
                    Creating the splunk_notable_event_id custom field in QRadar SOAR is strongly encouraged
                    in order to strengthen the relationship between QRadar SOAR and Splunk and to avoid duplicate
                    incident creation."""
                logger.warning(msg)
            #
            #   Note, Splunk does the token substitution for us only for the first event
            #   Do substitution ourselves if rid > 0.
            #
            if self.rid != "0":
                logger.debug("Token substitution")
                configuration = self.splunksdk.map_result(
                    sessionKey=self.session_key,
                    actionName=self.action_name,
                    modular_action=self,
                    result=result,
                    service=service,
                )

            # get rid of mapping_
            mapping_config = {
                fieldname.replace("mapping_", ""): configuration[fieldname]
                for fieldname in configuration.keys()
                if fieldname.startswith("mapping_")
            }

            artifacts = ResilientClient.get_artifacts(configuration, self.artifactLimit)

            if sys.version_info.major > 2:
                logger.info("APP CONFIGURATION: " + str(configuration))
                logger.info("CASE FIELD MAPPINGS: " + str(mapping_config))
                logger.info("ARTIFACTS: " + str(artifacts))
            else:
                # python2 REPL can not correctly interpret unicode inside a data container
                logger.info(
                    "APP CONFIGURATION: {"
                    + "".join(
                        "u'%s': u'%s', " % (k, v) for k, v in configuration.iteritems()
                    )
                    + "}"
                )
                logger.info(
                    "CASE FIELD MAPPINGS: {"
                    + "".join(
                        "u'%s': u'%s', " % (k, v) for k, v in mapping_config.iteritems()
                    )
                    + "}"
                )
                # slightly different case here. artifacts are in dict within list containing 1 element.
                artifacts and logger.info(
                    "ARTIFACTS: {"
                    + "".join(
                        "u'%s': u'%s', " % (k, v) for k, v in artifacts[0].iteritems()
                    )
                    + "}"
                )
                # if there are no aritfacts, the above log statement will throw an IndexError.
                # log that we have no artifacts
                not artifacts and logger.info("ARTIFACTS: []")

            incident_file = os.path.join(self.STATIC_DATA, "resilient.json")

            if (
                not self.resilient_conf["duplicates"]
                and self.customFieldConfigured
                and "event_id" in result
            ):
                # If we are disallowing duplicates, we need to have an event_id to reference and field must exist in resilient
                # If there is no event_id, the object escalated from Splunk was not a notable
                # query will return a list of incidents if there is a match
                # otherwise it returns an empty list
                logger.info("Checking for matching existing case in QRadar SOAR")
                event_id = result["event_id"]
                existing_incidents = self.queryFieldMatch(
                    self.resilient_client, CUSTOM_FIELD_NAME, event_id
                )
                if existing_incidents:
                    # in case there is more than once incident, we take the most recently created
                    # update the existing incident
                    existing_incident = existing_incidents[0]
                    logger.info(
                        "Existing case detected in QRadar SOAR. Case ID: {}".format(
                            existing_incident["id"]
                        )
                    )
                    logger.info(existing_incident)
                    logger.info("Updating case values")
                    inc = self.resilient_client.create_incident(
                        mapping_config,
                        artifacts,
                        incident_file,
                        update=True,
                        existing_incident=existing_incident,
                    )
                    case_url = self.resilient_client.build_case_url(
                        self.resilient_conf, inc["id"]
                    )
                    comment = "Updated case {0} in QRadar SOAR\n{1}".format(
                        inc["id"], case_url
                    )
                    self.splunksdk.update_notable_comment(
                        self.session_key, event_id, comment
                    )
                else:
                    # if nothing matches, go ahead and escalate
                    logger.info(
                        "No existing event found in QRadar SOAR matching {}".format(
                            event_id
                        )
                    )
                    inc = self.resilient_client.create_incident(
                        mapping_config, artifacts, incident_file
                    )
            else:
                # otherwise we escalate regardless
                logger.info(
                    "Settings not configured or not enough information to check for existing event. Escalating a new case"
                )
                inc = self.resilient_client.create_incident(
                    mapping_config, artifacts, incident_file
                )

            logger.info("Posted case.  ID is [%s]", inc["id"])
            logger.debug(inc)

            # if the result contains "event_id", then we write the incident_id back to the notable event
            # corresponding to that event_id
            if "event_id" in result:
                event_id = result["event_id"]
                logger.info(
                    "Adding case ID: "
                    + str(inc["id"])
                    + " to notable event "
                    + event_id
                )
                case_url = self.resilient_client.build_case_url(
                    self.resilient_conf, inc["id"]
                )
                new_comment = "QRadar SOAR Case ID: {0}\n{1}".format(
                    inc["id"], case_url
                )
                # TODO convert to splunklib
                self.splunksdk.update_notable_comment(
                    self.session_key, event_id, new_comment
                )

        except Exception as e:
            self.allGood = False
            logger.error(str(e))
            self.message(
                "Adaptive Response Action failed to create QRadar SOAR Case! See qradar_soar_modalert.log "
                "for details",
                status="failure",
            )


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        print(
            "FATAL Unsupported execution mode (expected --execute flag)",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        modaction = EscalateEvent(sys.stdin.read(), logger, "resilient")

        with gzip.open(modaction.results_file, "rt") as fh:
            for num, result in enumerate(csv.DictReader(fh)):
                if num >= modaction.limit:
                    break

                result.setdefault("rid", str(num))
                logger.info("Handling result: " + str(result) + ". rid is " + str(num))
                modaction.update(result)
                modaction.invoke()
                modaction.validate(result)
                modaction.dowork(result)
                if modaction.checkStatus():
                    logger.info("Escalated case successfully.")
                    modaction.message("Successfully created case.", status="success")
                time.sleep(1.6)

        modaction.writeevents(index="resilient", source="resilient")

    except Exception as e:
        try:
            modaction.message(e, status="failure", level=logging.CRITICAL)
        except:
            logger.critical(e)
        print("ERROR: {}".format(e), file=sys.stderr)
        sys.exit(3)
