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

# Built-in libraries
import json
import logging
import os
import sys
import time
from ast import literal_eval

# Third-party libraries
import requests
import urllib3

# Logging handlers
from logging.handlers import RotatingFileHandler

# Disable insecure request warnings for urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_splk_soar_trackmesplksoarlookup.log" % splunkhome,
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

# import Splunk libs (after lib appended)
from splunklib.searchcommands import (
    dispatch,
    StreamingCommand,
    Configuration,
    Option,
    validators,
)

# Import trackme libs
from trackme_libs import trackme_reqinfo


@Configuration(distributed=False)
class TrackmeSoarRestLookup(StreamingCommand):
    soar_server = Option(
        doc="""
        **Syntax:** **The soar_server=****
        **Description:** Mandatory, SOAR server account as configured in the Splunk App for SOAR""",
        require=False,
        default="*",
        validate=validators.Match("url", r"^.*"),
    )

    endpoint_target = Option(
        doc="""
        **Syntax:** **The type of object for the lookup call=****
        **Description:** The type of objects to be looked up""",
        require=True,
        default=None,
        validate=validators.Match("endpoint_target", r"^.*"),
    )

    source_field = Option(
        doc="""
        **Syntax:** **source_field=****
        **Description:** The source_field.""",
        require=True,
        default=None,
        validate=validators.Match("source_field", r"^.*$"),
    )

    dest_field_name = Option(
        doc="""
        **Syntax:** **dest_field_name=****
        **Description:** The dest_field_name.""",
        require=True,
        default=None,
        validate=validators.Match("dest_field_name", r"^.*$"),
    )

    dest_field_definition = Option(
        doc="""
        **Syntax:** **dest_field_definition=****
        **Description:** The dest_field_definition.""",
        require=True,
        default=None,
        validate=validators.Match("dest_field_definition", r"^.*$"),
    )

    definition_filter_fields = Option(
        doc="""
        **Syntax:** **definition_filter_fields=****
        **Description:** A comma separated list of fields that will be used to restrict the content of the definition, if None, the full content is retrieved.""",
        require=False,
        default="*",
        validate=validators.Match("definition_filter_fields", r"^.*$"),
    )

    def stream(self, records):
        # Start performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # Get the session key
        session_key = self._metadata.searchinfo.session_key

        # Build header and target
        header = f"Splunk {session_key}"
        root_url = f"{reqinfo['server_rest_uri']}/services/trackme/v2/splk_soar"

        # Set HTTP headers
        headers = {"Authorization": header}
        headers["Content-Type"] = "application/json"

        # Set the target URL
        target_url = f"{root_url}/soar_get_endpoint"

        # Set session and proceed
        with requests.Session() as session:

            # Process records
            for record in records:

                # Get the source field
                source_field_name = self.source_field
                source_field_value = record.get(source_field_name)

                if source_field_value:

                    try:

                        response = session.post(
                            target_url,
                            headers=headers,
                            verify=False,
                            data=json.dumps(
                                {
                                    "soar_server": self.soar_server,
                                    "endpoint": f"{self.endpoint_target}/{source_field_value}",
                                }
                            ),
                        )

                        response_json = response.json()
                        response.raise_for_status()
                        response_soar = response_json.get(
                            "response"
                        )  # get response inside response

                        logging.debug(
                            f'response_soar="{json.dumps(response_soar)}"'
                        )  # debug

                        if response_soar:

                            # get name from the response
                            soar_response_name = response_soar.get("name")

                            # set the dest field name
                            record[self.dest_field_name] = soar_response_name

                            # get object from the response
                            if self.definition_filter_fields == "*":
                                record[self.dest_field_definition] = response_soar
                            else:
                                # only preserve the fields in the definition_filter_fields (comma separated), if it exists and is not null
                                definition_filter_fields = (
                                    self.definition_filter_fields.split(",")
                                )
                                response_soar_filtered = {}
                                for field in definition_filter_fields:
                                    if field in response_soar:
                                        response_soar_filtered[field] = (
                                            response_soar.get(field)
                                        )
                                record[self.dest_field_definition] = (
                                    response_soar_filtered
                                )

                    # if an exception occurs, we would only log it in debug mode
                    except Exception as e:
                        logging.debug(
                            f"Failed to get the SOAR response for source_field_value={source_field_value}, exception={e}"
                        )
                        pass

                    # yield
                    yield record

        # Log the run time
        logging.info(
            f"trackmesplksoarlookup has terminated, run_time={round(time.time() - start, 3)}"
        )


dispatch(TrackmeSoarRestLookup, sys.argv, sys.stdin, sys.stdout, __name__)
