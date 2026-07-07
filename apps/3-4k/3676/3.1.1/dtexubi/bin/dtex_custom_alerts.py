#!/usr/bin/python
# -*- coding: utf-8 -*-

# Python imports
from __future__ import print_function

import csv
import gzip
import json
import logging
import logging.handlers
import sys
import traceback
import time
import os
from datetime import datetime
import codecs


# Core splunk imports

import splunk.search as search
from splunk.clilib import cli_common as cli

try:
    from splunk.clilib.bundle_paths import make_splunkhome_path
except ImportError:
    from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

# Get app name

myapp = __file__.split(os.sep)[-3]

# Append path to app's lib to use modules within it

sys.path.append(make_splunkhome_path(["etc", "apps", myapp, "lib"]))

# Local imports

from cim_actions import ModularAction  # noqa: E402

# Setup logger

logger = ModularAction.setup_logger("dtexubi_custom_modalert")

# Prepare path to lookups directory of the app
LOOKUP_FILE = make_splunkhome_path(["etc", "apps", myapp, "lookups", "category_mapping.csv"])

try:

    # Open lookup file

    csv_file = open(LOOKUP_FILE)

    # Read rows from csv file using csv reader

    search_info_rows = csv.reader(csv_file)

    # Skip header

    next(search_info_rows)
    category_mapping = [
        {"category_id": row[0], "category_value": row[1]} for row in search_info_rows
    ]
except Exception:
    category_mapping = None

# Get index name from macros.conf file

configuration_dict = cli.getConfStanza("macros", "dtexubi_index")
index = configuration_dict["definition"].split("=")[1]


class DtexCustomAlertAction(ModularAction):
    """Class for Custom Alert Action."""

    def __init__(
        self, settings, logger, action_name=None,
    ):
        """Init method."""
        super(DtexCustomAlertAction, self).__init__(settings, logger, action_name)

        # Obtain action parameters set by the user

        self.category = self.configuration["category"]
        self.risk_score = self.configuration["risk_score"]
        self.severity = self.configuration["severity"]
        self.created_at = int(float(self.configuration["triggertime"]))
        self.created_at = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(self.created_at))

    def dowork(
        self, user_name_list, session_key, occurred_at,
    ):
        """Override dowork method of ModularAction class.

        This method searches for the user_risk_score for all the
        users, adds the risk_score configured to the obtained user_risk_score and prepares the event dictionary
        that needs to be indexed as splunk event.
        :param user_name_list: list of user names to run search for
        :param session_key: session key of Splunk
        :param occurred_at: time at which event was first noticed
        """
        # Prepare event dictionary
        event_dict = dict()

        # Get current day start and end in epoch

        current_day_start = int(time.mktime(datetime.now().date().timetuple()))
        current_day_end = current_day_start + 86399

        # Run search for each user and add an event for each user in splunk with the updated

        for user in user_name_list:
            user_modified = user.replace("\\", "\\\\")

            # Search that provides the user_score for a particular user

            get_user_risk_score = (
                '| tstats sum(alerts.risk_score) as user_score from datamodel=dtex_alerts where alerts.user_name="'
                + user_modified
                + '"'
            )

            # Run search on splunk

            user_risk_score_results = search.searchAll(
                get_user_risk_score,
                earliest_time=current_day_start,
                latest_time=current_day_end,
                sessionKey=session_key,
                namespace="dtexubi",
            )

            user_cumulative_risk_score = 0

            # Iterate over results obtained and get the existing user_risk_score

            for (i, user_risk_score_result) in enumerate(user_risk_score_results):
                user_cumulative_risk_score = str(user_risk_score_result.get("user_score", 0))

            # Update user_risk_score by adding the score obtained from search and the score configured by user

            event_dict["user_risk_score"] = float(user_cumulative_risk_score) + float(
                self.risk_score
            )

            get_user_category_risk_score = (
                '| tstats sum(alerts.risk_score) as user_score from datamodel=dtex_alerts where alerts.user_name="'
                + user_modified
                + '"'
                + 'AND alerts.category="'
                + self.category
                + '"'
            )

            # Run search on splunk

            user_category_risk_score_results = search.searchAll(
                get_user_category_risk_score,
                earliest_time=current_day_start,
                latest_time=current_day_end,
                sessionKey=session_key,
                namespace="dtexubi",
            )

            user_category_risk_score = 0

            # Iterate over results obtained and get the existing user_category_risk_score

            for (i, user_category_risk_score_result) in enumerate(user_category_risk_score_results):
                user_category_risk_score = str(user_category_risk_score_result.get("user_score", 0))

            event_dict["user_category_risk_score"] = float(user_category_risk_score) + float(
                self.risk_score
            )
            event_dict["category"] = self.category

            # Get category_id from category name provided by user

            category_id = None
            if category_mapping:
                for category in category_mapping:
                    if self.category == category["category_value"]:
                        category_id = category["category_id"]
                        break

            # Add other required fields in event dictionary

            event_dict["category_id"] = category_id if category_id else ""
            event_dict["user_name"] = user
            event_dict["risk_score"] = self.risk_score
            event_dict["severity"] = self.severity
            event_dict["occurred_at"] = occurred_at
            event_dict["created_at"] = self.created_at
            event_dict["sid"] = self.sid

            # Add event_dict formed and assign it a sourcetype

            self.addevent(json.dumps(event_dict), "dtex_custom_alerts")

        # Write events in splunk in the specified index and source

        if modaction.writeevents(index=index, source="dtex_custom_alerts"):
            modaction.message("Successfully created splunk event", status="success", rids=self.rids)
        else:
            modaction.message(
                "Failed to create splunk event",
                status="failure",
                rids=self.rids,
                level=logging.ERROR,
            )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] != "--execute":
        print("FATAL Unsupported execution mode (expected --execute flag)", file=sys.stderr)
        sys.exit(1)
    try:

        # Initialize object of "DtexCustomAlertAction" class
        modaction = DtexCustomAlertAction(sys.stdin.read(), logger, "dtex_custom_alerts")
        modaction.addinfo()
        # Obtain session key

        session_key = modaction.session_key
        user_name_field = modaction.configuration.get("username")
        time_field = modaction.configuration.get("time")
        time_field_list = list()
        user_name_list = list()

        if not user_name_field:
            logger.critical(modaction.message('"User Name" field not configured', "failure"))
            sys.exit(0)

        # Read user name and time from the results obtained and add it to the user_name_list
        #  and time_field_list respectively

        with gzip.open(modaction.results_file, "rb") as fh:

            fh = codecs.getreader("utf-8")(fh)

            for (num, result) in enumerate(csv.DictReader(fh)):
                result.setdefault("rid", str(num))
                modaction.update(result)
                modaction.invoke()

                if result.get(user_name_field):
                    user_name_list.append(result.get(user_name_field))

                if result.get(time_field):
                    time_of_event = result.get(time_field).split(".")
                    try:
                        epoch_time = datetime.strptime(time_of_event[0], "%Y-%m-%dT%H:%M:%S")
                        epoch_time_in_secs = time.mktime(epoch_time.timetuple())
                    except Exception:
                        try:
                            epoch_time_in_secs = int(time_of_event[0])
                        except Exception:
                            logger.error(
                                "Invalid time format: set time format to epoch or %Y-%m-%dT%H:%M:%S"
                            )
                            sys.exit(1)

                    time_field_list.append(int(epoch_time_in_secs))

        # Assign least value in time_field_list to occurred_at if time_field_list is not empty else take current time

        if time_field_list:
            time_field_list = sorted(set(time_field_list))
            occurred_at = time_field_list[0]
        else:
            occurred_at = int(time.time())

        # Convert timestamp to human readable format

        occurred_at = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(occurred_at))

        # Invoke dowork method

        user_name_list = list(set(user_name_list)) if user_name_list else list()
        modaction.dowork(user_name_list, session_key, occurred_at)

    except Exception as e:
        # Handle any exception occurred
        try:
            logger.critical(modaction.message(e, "failure"))
        except Exception:
            logger.critical(e)
            traceback.print_exc(file=sys.stderr)
        print("ERROR Unexpected error: %s" % e, file=sys.stderr)
        sys.exit(3)
