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

# Logging
import logging
from logging.handlers import RotatingFileHandler

# Third-party modules
import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_get_kos.log" % splunkhome,
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

# Import Splunk libs
from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)

# Import trackme libs
from trackme_libs import trackme_reqinfo


@Configuration(distributed=False)
class TrackMeGetKos(GeneratingCommand):

    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** The tenant identifier.""",
        require=True,
        default=None,
        validate=validators.Match("tenant_id", r".*"),
    )

    """
    This function ensures that records have the same list of fields to allow Splunk to automatically extract these fields
    If a given result does not have a given field, it will be added to the record as an empty value    
    """

    def generate_fields(self, records):
        all_keys = set()
        for record in records:
            all_keys.update(record.keys())

        for record in records:
            for key in all_keys:
                if key not in record:
                    record[key] = ""
            yield record

    def generate(self, **kwargs):
        # Start performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # Define an header for requests authenticated communications with splunkd
        header = {
            "Authorization": "Splunk %s" % self._metadata.searchinfo.session_key,
            "Content-Type": "application/json",
        }

        # url
        url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/configuration/get_tenant_knowledge_objects"

        # final yield record
        yield_record = []

        try:
            response = requests.post(
                url,
                headers=header,
                data=json.dumps({"tenant_id": self.tenant_id}),
                verify=False,
                timeout=600,
            )

            response.raise_for_status()
            response_json = response.json()

        except Exception as e:
            error_msg = f'failed to retrieve the list of TrackMe Knowledge Objects to be handled with exception="{str(e)}"'
            raise Exception(error_msg)

        #
        # Render
        #

        for yield_record in self.generate_fields(response_json):
            # logging
            logging.debug(f'yield_record="{json.dumps(yield_record, indent=2)}"')

            # yield record
            yield {
                "_time": time.time(),
                "_raw": json.dumps(yield_record),
                "tenant_id": self.tenant_id,
                "title": yield_record.get("title"),
                "type": yield_record.get("type"),
                "properties": yield_record.get("properties"),
                "component": yield_record.get("component"),
                "description": yield_record.get("description"),
                "collection": yield_record.get("collection"),
                "fields_list": yield_record.get("fields_list"),
            }

        # performance counter
        logging.debug(f'trackmegetkos has terminated, run_time="{time.time() - start}"')


dispatch(TrackMeGetKos, sys.argv, sys.stdin, sys.stdout, __name__)
