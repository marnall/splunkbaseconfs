from __future__ import absolute_import
import os
import sys
import json
import requests
import time
import datetime
from settings import APP_ID


splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(
    os.path.join(splunkhome, "etc", "apps", APP_ID, "lib")
)
from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)
from splunklib import client, results
from dt_api_wrapper import DtApiWrapper
from dt_logger import DTLogger
from domaintools.exceptions import (
    ServiceException,
    NotAuthorizedException,
    ServiceUnavailableException,
)
import dt_exception_messages


@Configuration()
class SyncWatchlistCommand(GeneratingCommand):
    """This custom search command syncs dt_iris_detect_results with the state "watched" with the dt_monitoring_list.

        Inherits from the GeneratingCommand custom search type. Override the `generate` method as the entrypoint to this script

        Example:
            | dtsyncirisdetectwatchlist feature="Saved Search"
    """

    feature = Option(
        doc="""
                **Syntax:** **feature=***<feature>*
                **Description:** Feature in the app where this was called""",
        default="adhoc",
        require=False,
    )

    def get_token(self):
        """get session key used to decrypt api credentials"""
        return self.metadata.searchinfo.session_key

    def get_user(self):
        """get current logged in user"""
        return self.metadata.searchinfo.username

    def generate(self):
        """This is the entry point to a GeneratingCommand subclass. You must override this method

            :return: generator rows to pass on to next command of SPL search after transform
        """
        self.dt_log = DTLogger(
            "iris_detect", os.path.basename(__file__), self.get_user(), self.feature
        )
        self.dt_log.info("starting sync_watchlist.py")

        try:
            iris_detect_results_kvstore = self.service.kvstore["dt_iris_detect_results"]
            dt_monitoring_list_kvstore = self.service.kvstore["dt_monitoring_list"]
            new_monitor_list = []
            for result_data in iris_detect_results_kvstore.data.query(query=json.dumps({"dt_state": "watched"})):
                new_record = {
                    "_key": result_data["dt_domain"],
                    "en_attribute_type": "domain",
                    "_dt_updated": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "_dt_updated_by": self.get_user(),
                    "_dt_source": "Iris Detect",
                    "_dt_created": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "_dt_created_by": self.get_user(),
                }
                check_duplicate = dt_monitoring_list_kvstore.data.query(query=json.dumps({"_key": result_data["dt_domain"]}))
                if check_duplicate:
                    new_record["_dt_created"] = check_duplicate[0]["_dt_created"]
                    new_record["_dt_created_by"] = check_duplicate[0]["_dt_created_by"]
                new_monitor_list.append(new_record)

            save_result = dt_monitoring_list_kvstore.data.batch_save(*new_monitor_list)

            yield ({"status": save_result})
        except Exception as e:
            self.dt_log.error(e, {"status": "sync watchlist down"})
            raise Exception(dt_exception_messages.generic.format(e)) from e

        self.dt_log.info("Completed sync_watchlist.py")


dispatch(SyncWatchlistCommand, sys.argv, sys.stdin, sys.stdout, __name__)
