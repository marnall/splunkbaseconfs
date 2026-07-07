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
    "%s/var/log/splunk/trackme_check_backups.log" % splunkhome,
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
class TrackMeCheckBackups(GeneratingCommand):

    archives_list = Option(
        doc="""
        **Syntax:** **archives_list=****
        **Description:** Optionally filter on a given list of backup files. (comma separated list of files)""",
        require=False,
        default="*",
        validate=validators.Match("archives_list", r".*"),
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
        url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/backup_and_restore/restore"

        # Set backup root dir
        backuproot = os.path.join(splunkhome, "etc", "apps", "trackme", "backup")

        # final yield record
        yield_record = []

        # List of available archives files
        archives_available_list = []

        # Iterate over the backup root dir, add to the list each backup file starting with "trackme-backup-" and with .tgz or .tar.zst extension
        for root, dirs, files in os.walk(backuproot):
            logging.info(f"Scanning directory: {root}, Found files: {files}")
            for file in files:
                if file.startswith("trackme-backup-") and (file.endswith(".tgz") or file.endswith(".tar.zst")):
                    archives_available_list.append(file)

        # Debug log for available archives
        logging.info(f"Available archives: {archives_available_list}")

        # Optional: requested archives list
        requested_archives_list = self.archives_list

        if requested_archives_list != "*":
            # Turn into a list from the comma-separated string
            requested_archives_list = [
                x.strip() for x in requested_archives_list.split(",")
            ]
            logging.info(f"Requested archives list: {requested_archives_list}")

            # Update archives_available_list to keep only files in the requested_archives_list
            archives_available_list = list(
                set(archives_available_list).intersection(requested_archives_list)
            )

        # Final debug log for archives
        logging.info(f"Filtered archives: {archives_available_list}")

        # List of responses
        responses_list = []

        if not archives_available_list:
            yield {
                "_time": time.time(),
                "_raw": json.dumps(
                    {
                        "message": "No backup archives available",
                        "archives_available_list": archives_available_list,
                        "backupdir": backuproot,
                    }
                ),
            }

        else:

            for archive_name in archives_available_list:

                data = {
                    "backup_archive": os.path.join(backuproot, archive_name),
                    "dry_run": True,
                }

                try:
                    response = requests.post(
                        url,
                        headers=header,
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )

                    response.raise_for_status()
                    response_json = response.json()
                    # add the archive name to the response
                    response_json["archive_name"] = archive_name
                    responses_list.append(response_json)

                    logging.info(
                        f'response_json="{json.dumps(response_json, indent=2)}"'
                    )

                except Exception as e:
                    error_msg = f'failed to call TrackMe endpoint, exception="{str(e)}"'
                    raise Exception(error_msg)

            #
            # Render
            #

            for yield_record in self.generate_fields(responses_list):
                # logging
                logging.debug(f'yield_record="{json.dumps(yield_record, indent=2)}"')

                # yield record
                yield {
                    "_time": time.time(),
                    "_raw": json.dumps(yield_record),
                    "archive_name": yield_record.get("archive_name"),
                    "response": yield_record.get("response"),
                    "knowledge_objects_summary": yield_record.get(
                        "knowledge_objects_summary"
                    ),
                    "kvstore_collections_details": yield_record.get(
                        "kvstore_collections_details"
                    ),
                    "kvstore_collections_json_files": yield_record.get(
                        "kvstore_collections_json_files"
                    ),
                }

        # performance counter
        logging.debug(
            f'TrackMeCheckBackups has terminated, run_time="{time.time() - start}"'
        )


dispatch(TrackMeCheckBackups, sys.argv, sys.stdin, sys.stdout, __name__)
