#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Standard library
import os
import sys
import time
import json

# Networking imports
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
import logging
from logging.handlers import RotatingFileHandler

splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    os.path.join(splunkhome, "var", "log", "splunk", "trackme_trackmesplkpriority.log"),
    mode="a",
    maxBytes=10_000_000,
    backupCount=1,
)
formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(filename)s %(funcName)s %(lineno)d %(message)s"
)
logging.Formatter.converter = time.gmtime
filehandler.setFormatter(formatter)
log = logging.getLogger()  # root logger - Good to get it only once.
for hdlr in log.handlers[:]:  # remove the existing file handlers
    if isinstance(hdlr, logging.FileHandler):
        log.removeHandler(hdlr)
log.addHandler(filehandler)  # set the new handler
# set the log level to INFO, DEBUG as the default is ERROR
log.setLevel(logging.INFO)

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# import Splunk libs
from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)

# Import trackme libs
from trackme_libs import (
    trackme_reqinfo,
    trackme_vtenant_component_info,
    trackme_register_tenant_object_summary,
)

# import TrackMe get data libs
from trackme_libs_get_data import (
    search_kv_collection,
)


@Configuration(distributed=False)
class TrackMeHandlePriority(GeneratingCommand):
    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** Specify the TrackMe target tenant_id.""",
        require=True,
        default="None",
        validate=validators.Match("tenant_id", r"^.*$"),
    )

    component = Option(
        doc="""
        **Syntax:** **component=****
        **Description:** Specify the TrackMe target component.""",
        require=True,
        default="None",
        validate=validators.Match("component", r"^.*$"),
    )

    def generate(self, **kwargs):

        # start
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # log start
        logging.info(f'tenant_id="{self.tenant_id}", component="{self.component}", Starting tracker')

        # target
        target_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/splk_priority_policies/write/priority_policies_apply"

        # data
        post_data = {
            "tenant_id": self.tenant_id,
            "component": self.component,
        }

        # Splunk header
        header = f"Splunk {self._metadata.searchinfo.session_key}"

        # priority policies KV collection
        priority_policies_collection_name = (
            f"kv_trackme_{self.component}_priority_policies_tenant_{self.tenant_id}"
        )

        # get records
        # Get kvcollection mode from configuration with error handling
        try:
            kvcollection_mode = reqinfo["trackme_conf"]["trackme_general"].get(
                "central_kvcollection_mode", "search_mode"
            )
        except Exception as e:
            logging.debug(
                f'failed to retrieve kvcollection_mode, defaulting to search_mode, exception="{str(e)}"'
            )
            kvcollection_mode = "search_mode"
        # Build provenance string for logging
        provenance = f"trackmesplkpriority:{self.component}:tenant_{self.tenant_id}"
        (
            priority_policies_records,
            priority_collection_keys,
            priority_collection_dict,
            last_page,
        ) = search_kv_collection(
            self.service, priority_policies_collection_name, page=1, page_count=0, kvcollection_mode=kvcollection_mode, provenance=provenance, logger=logging
        )

        # get vtenant component info
        vtenant_component_info = trackme_vtenant_component_info(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
            self.tenant_id,
        )
        logging.debug(
            f'vtenant_component_info="{json.dumps(vtenant_component_info, indent=2)}"'
        )

        # check schema version migration state
        try:
            schema_version = int(vtenant_component_info["schema_version"])
            schema_version_upgrade_in_progress = bool(
                int(vtenant_component_info["schema_version_upgrade_in_progress"])
            )
            logging.debug(
                f'schema_version_upgrade_in_progress="{schema_version_upgrade_in_progress}"'
            )
        except Exception as e:
            schema_version = 0
            schema_version_upgrade_in_progress = False
            logging.error(
                f'failed to retrieve schema_version_upgrade_in_progress=, exception="{str(e)}"'
            )

        # Do not proceed if the schema version upgrade is in progress
        if schema_version_upgrade_in_progress:
            yield_json = {
                "_time": time.time(),
                "tenant_id": self.tenant_id,
                "component": self.component,
                "response": f'tenant_id="{self.tenant_id}", schema upgrade is currently in progress, we will wait until the process is completed before proceeding, the schema upgrade is handled by the health_tracker of the tenant and is completed once the schema_version field of the Virtual Tenants KVstore (trackme_virtual_tenants) matches TrackMe\'s version, schema_version="{schema_version}", schema_version_upgrade_in_progress="{schema_version_upgrade_in_progress}"',
                "schema_version": schema_version,
                "schema_version_upgrade_in_progress": schema_version_upgrade_in_progress,
            }
            logging.info(json.dumps(yield_json, indent=2))
            yield {
                "_time": yield_json["_time"],
                "_raw": yield_json,
            }

        # proceed boolean
        proceed = False

        # only proceed if we have records in priority_policies_records
        if len(priority_policies_records) > 0:
            proceed = True

        if not proceed or schema_version_upgrade_in_progress:

            if not schema_version_upgrade_in_progress:

                run_time = round(time.time() - start, 3)
                response = {
                    "action": "success",
                    "result": "There are no policies to apply, nothing to do.",
                    "run_time": run_time,
                }

                trackme_register_tenant_object_summary(
                    self._metadata.searchinfo.session_key,
                    self._metadata.searchinfo.splunkd_uri,
                    self.tenant_id,
                    f"splk-{self.component}",
                    f"trackme_{self.component}_priority_tracker_tenant_{self.tenant_id}",
                    "success",
                    time.time(),
                    str(time.time() - start),
                    "The report was executed successfully",
                    "-5m",
                    "now",
                )

                yield {
                    "_time": time.time(),
                    "response": response,
                    "_raw": response,
                    "run_time": run_time,
                }

        else:

            try:
                response = requests.post(
                    target_url,
                    headers={
                        "Authorization": header,
                        "Content-Type": "application/json",
                    },
                    data=json.dumps(post_data),
                    verify=False,
                    timeout=600,
                )

                # Parse the upstream response defensively. The upstream endpoint can return
                # a non-JSON body (e.g. a 5xx with a plain-text payload coming from the base
                # RESTHandler's unhandled-exception path) — without this guard the bare
                # JSONDecodeError ("Expecting value: line 1 column 1 (char 0)") leaks up as
                # the tracker's last_result and hides the real upstream failure.
                response_text = response.text or ""
                if response.status_code >= 400:
                    body_preview = response_text[:500] if response_text else "<empty>"
                    msg = (
                        f'upstream returned an HTTP error, '
                        f'http_status="{response.status_code}", body_preview="{body_preview}"'
                    )
                    logging.error(msg)
                    raise Exception(msg)

                try:
                    response_json = response.json()
                except ValueError as parse_error:
                    body_preview = response_text[:500] if response_text else "<empty>"
                    msg = (
                        f'upstream returned a non-JSON response, '
                        f'http_status="{response.status_code}", body_preview="{body_preview}", '
                        f'parse_error="{str(parse_error)}"'
                    )
                    logging.error(msg)
                    raise Exception(msg)

                # get action value
                action = response_json.get("action", "failure")

                if action == "success":

                    trackme_register_tenant_object_summary(
                        self._metadata.searchinfo.session_key,
                        self._metadata.searchinfo.splunkd_uri,
                        self.tenant_id,
                        f"splk-{self.component}",
                        f"trackme_{self.component}_priority_tracker_tenant_{self.tenant_id}",
                        "success",
                        time.time(),
                        str(time.time() - start),
                        "The report was executed successfully",
                        "-5m",
                        "now",
                    )

                else:

                    # try to get entities_exceptions_list from the response
                    error_messages = response_json.get("error_messages", [])
                    error_msg = f"The report was executed with errors: {json.dumps(error_messages, indent=0)}"

                    trackme_register_tenant_object_summary(
                        self._metadata.searchinfo.session_key,
                        self._metadata.searchinfo.splunkd_uri,
                        self.tenant_id,
                        f"splk-{self.component}",
                        f"trackme_{self.component}_priority_tracker_tenant_{self.tenant_id}",
                        "failure",
                        time.time(),
                        str(time.time() - start),
                        error_msg,
                        "-5m",
                        "now",
                    )

                run_time = round(time.time() - start, 3)
                yield {
                    "_time": time.time(),
                    "response": response_json,
                    "_raw": response_json,
                    "run_time": run_time,
                }

                # log end
                logging.info(f'tenant_id="{self.tenant_id}", component="{self.component}", The tracker has terminated successfully, run_time="{run_time}", response="{json.dumps(response_json, indent=2)}"')

            except Exception as e:
                # Call the component register
                trackme_register_tenant_object_summary(
                    self._metadata.searchinfo.session_key,
                    self._metadata.searchinfo.splunkd_uri,
                    self.tenant_id,
                    f"splk-{self.component}",
                    f"trackme_{self.component}_priority_tracker_tenant_{self.tenant_id}",
                    "failure",
                    time.time(),
                    str(time.time() - start),
                    str(e),
                    "-5m",
                    "now",
                )
                msg = f'context="check_trackers", tenant_id="{self.tenant_id}", main search failed with exception="{str(e)}"'
                logging.error(msg)
                raise Exception(msg)


dispatch(TrackMeHandlePriority, sys.argv, sys.stdin, sys.stdout, __name__)
