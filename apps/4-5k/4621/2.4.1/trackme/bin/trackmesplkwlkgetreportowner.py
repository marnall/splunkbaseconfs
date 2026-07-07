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

# Standard library
import os
import sys
import time

# External libraries
import urllib3

# Disable urllib3 warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
import logging
from logging.handlers import RotatingFileHandler

# set splunkhome
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_splkwlk_getreportowner_stream.log" % splunkhome,
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

# import trackme libs (after lib appended)
from trackme_libs import trackme_reqinfo, run_splunk_search
from trackme_libs_utils import decode_unicode

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces


@Configuration(distributed=False)
class SplkWlkGetReportsDef(StreamingCommand):
    account = Option(
        doc="""
        **Syntax:** **account=****
        **Description:** The account name, local means the local Splunk API.""",
        require=False,
        default="local",
    )

    # default record
    def yield_default_record(
        self,
        record,
        message,
    ):
        record["owner_check_result"] = message

        return record

    # process savedsearch
    def process_savedsearch(
        self,
        record,
        savedsearches,
    ):
        record_savedsearch_name = decode_unicode(record.get("savedsearch_name"))
        record_user = record.get("user", None)

        # if record_user is defined, check then len and set to None if empty
        if record_user:
            if len(record_user) == 0:
                record_user = None

        # Not application for accelerated searches
        if record_savedsearch_name.startswith("_ACCELERATE"):
            return self.yield_default_record(
                record,
                "Not applicable for datamodel acceleration searches",
            )

        # Not application if the user is defined already
        elif record_user and not (record_user == "system" or record_user == "nobody"):
            return self.yield_default_record(
                record,
                "saved search user owner is identified already",
            )

        else:
            savedsearch = savedsearches.get(record_savedsearch_name, None)

            if not savedsearch:
                return self.yield_default_record(
                    record,
                    "saved search was not found",
                )

            else:
                # init
                savedsearch_owner = None
                savedsearch_owner = savedsearch.get("user")

                # return the final record
                record["user"] = savedsearch_owner
                record["owner_check_result"] = (
                    "saved search metadata were retrieved successfully"
                )
                return record

    def generate_fields(self, records):
        # this function ensures that records have the same list of fields to allow Splunk to automatically extract these fields
        # if a given result does not have a given field, it will be added to the record as an empty value
        all_keys = set()
        for record in records:
            all_keys.update(record.keys())

        for record in records:
            for key in all_keys:
                if key not in record:
                    record[key] = ""
            yield record

    # main
    def stream(self, records):
        if self:
            # start perf duration counter
            start = time.time()

            # Get request info and set logging level
            reqinfo = trackme_reqinfo(
                self._metadata.searchinfo.session_key,
                self._metadata.searchinfo.splunkd_uri,
            )
            log.setLevel(reqinfo["logging_level"])

            #
            # Run a search to get the list of saved searches, either locally or remotely using splunkremotesearch
            #

            # kwargs
            kwargs_oneshot = {
                "earliest_time": "-5m",
                "latest_time": "now",
                "output_mode": "json",
                "count": 0,
            }

            savedsearches = {}

            if self.account == "local":
                search_str = f"""\
                    | rest timeout=1800 splunk_server=local /servicesNS/-/-/saved/searches add_orphan_field=no count=0 
                    | rename title as savedsearch_name, eai:acl.owner AS user, eai:acl.app AS app
                    | fields savedsearch_name, user, app
                    | eval user=if(user=="nobody" OR user=="splunk-system-user", "system", user)
                    | table savedsearch_name, app, user
                """
            else:
                search_str = f"""\
                    | splunkremotesearch account="{self.account}" search="| rest timeout=1800 splunk_server=local /servicesNS/-/-/saved/searches add_orphan_field=no count=0 
                    | rename title as savedsearch_name, eai:acl.owner AS user, eai:acl.app AS app
                    | fields savedsearch_name, user, app
                    | eval user=if(user==\\\"nobody\\\" OR user==\\\"splunk-system-user\\\", \\\"system\\\", user)
                    | table savedsearch_name, app, user"
                    | table savedsearch_name, app, user
                """

            # run the main report, every result is a Splunk search to be executed on its own thread

            # run search
            try:
                reader = run_splunk_search(
                    self.service,
                    remove_leading_spaces(search_str),
                    kwargs_oneshot,
                    24,
                    5,
                )

                for item in reader:
                    if isinstance(item, dict):
                        savedsearches[item.get("savedsearch_name")] = {
                            "app": item.get("app"),
                            "user": item.get("user"),
                        }

                # break while
                logging.info(
                    f'get savedsearches succeeded, account={self.account}, {len(savedsearches)} uniq searches were retrieved, search_str="{remove_leading_spaces(search_str)}"'
                )

            except Exception as e:
                msg = f'main search failed with exception="{str(e)}"'
                logging.error(msg)
                raise Exception(msg)

            # end of get configuration

            #
            # loop through upstream records
            #

            yield_records = []

            # Loop in the results
            for record in records:
                # Process the saved search and yield the result
                yield_records.append(
                    self.process_savedsearch(
                        record,
                        savedsearches,
                    )
                )

            for yield_record in self.generate_fields(yield_records):
                yield yield_record

            run_time = round(time.time() - start, 3)
            logging.info(
                f'trackmesplkwlkgetreportowner has terminated, run_time="{run_time}"'
            )


dispatch(SplkWlkGetReportsDef, sys.argv, sys.stdin, sys.stdout, __name__)
