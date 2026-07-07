#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = ["Guilhem Marchand"]
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Standard library imports
import os
import sys
import time
import json

# Logging imports
import logging
from logging.handlers import RotatingFileHandler

# Third-party library imports
import requests
from requests.structures import CaseInsensitiveDict
import urllib3

# Disable InsecureRequestWarning for urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# set splunkhome
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_splkwlk_getreportsdef_gen.log" % splunkhome,
    mode="a",
    maxBytes=10000000,
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

# impport TrackMe libs
from trackme_libs import trackme_reqinfo


@Configuration(distributed=False)
class SplkWlkGetReportsDef(GeneratingCommand):
    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** value for tenant_id is required.""",
        require=True,
        default=None,
        validate=validators.Match("tenant_id", r"^.*$"),
    )

    object_name = Option(
        doc="""
        **Syntax:** **object_name=****
        **Description:** value for object_name is optional if object_id is provided.""",
        require=False,
        default=None,
        validate=validators.Match("object_name", r"^.*$"),
    )

    object_id = Option(
        doc="""
        **Syntax:** **object_id=****
        **Description:** value for object_id is optional if object_name is provided. This is the _key in KVstore (keyid of the entity).""",
        require=False,
        default=None,
        validate=validators.Match("object_id", r"^.*$"),
    )

    def generate(self, **kwargs):
        if self:
            # Get request info and set logging level
            reqinfo = trackme_reqinfo(
                self._metadata.searchinfo.session_key,
                self._metadata.searchinfo.splunkd_uri,
            )
            log.setLevel(reqinfo["logging_level"])

            # Get the session key
            session_key = self._metadata.searchinfo.session_key

            # Get splunkd_port
            splunkd_uri = self._metadata.searchinfo.splunkd_uri

            """
            Retrieve settings.
            """

            # Ensure splunkd_uri starts with "https://"
            if not splunkd_uri.startswith("https://"):
                splunkd_uri = f"https://{splunkd_uri}"

            # Build header and target URL
            headers = CaseInsensitiveDict()
            headers["Authorization"] = f"Splunk {session_key}"
            headers["Content-Type"] = "application/json"
            target_url = (
                f"{splunkd_uri}/services/trackme/v2/splk_wlk/wlk_entity_metadata"
            )

            # Create a requests session for better performance
            session = requests.Session()
            session.headers.update(headers)

            # Validate that at least one of object_name or object_id is provided
            if not self.object_name and not self.object_id:
                error_message = "Either object_name or object_id must be provided"
                logging.error(error_message)
                raise Exception(error_message)

            # Build the request payload
            payload = {"tenant_id": self.tenant_id}
            if self.object_id:
                payload["object_id"] = self.object_id
            elif self.object_name:
                payload["object"] = self.object_name
            else:
                error_message = "Either object_name or object_id must be provided"
                logging.error(error_message)
                raise Exception(error_message)

            try:
                # Use a context manager to handle the request
                with session.post(
                    target_url,
                    data=json.dumps(payload),
                    verify=False,
                ) as response:
                    if response.ok:
                        logging.debug(f'Success requests, data="{response}"')
                        response_json = response.json()

                        # loop and render
                        for version_id in response_json:
                            response_record = {
                                "_time": response_json[version_id][
                                    "time_inspected_epoch"
                                ],
                                "version_dict": response_json[version_id],
                                "_raw": response_json[version_id],
                            }

                            # loop through available fields in the JSON object
                            for field_key, field_value in response_json[
                                version_id
                            ].items():
                                response_record[field_key] = field_value

                            # yield
                            yield response_record

                    else:
                        error_message = f'Failed to metadata for this object, status_code={response.status_code}, response_text="{response.text}"'
                        logging.debug(error_message)
                        response_record = {
                            "_time": time.time(),
                            "_raw": "There are no versioning metadata available for this object, this may be expected in some use cases such as acceleration searches, or this savedsearch was not inspected yet.",
                        }
                        yield response_record

            except Exception as e:
                error_message = f'Failed to retrieve metadata, exception="{str(e)}"'
                logging.error(error_message)
                raise Exception(error_message)


dispatch(SplkWlkGetReportsDef, sys.argv, sys.stdin, sys.stdout, __name__)
