#!/usr/bin/env python

import csv
import os
import sys

splunkhome = os.environ.get("SPLUNK_HOME", "/opt/splunk")
APP_NAME = "usecase_explorer"
APP_DIR = os.path.join(splunkhome, "etc", "apps", APP_NAME)
sys.path.append(os.path.join(APP_DIR, "lib"))
# We need to add the apps lib directory to the path before the import (hence the noqa for flake)
from splunklib.searchcommands import (  # noqa: E402
    dispatch,
    validators,
    Option,
    ReportingCommand,
    Configuration,
)


@Configuration()
class UceUpdateTableCommand(ReportingCommand):
    """Updates the internal UCE tables with the supplied results.

    ##Syntax

    uce_update_table append=(true|false)

    ##Description

    Updates the internal UCE tables with the supplied results, either by overwriting (default)
    or appending (with append=true).

    """

    append = Option(require=False, validate=validators.Boolean())

    headers = {"usecase_bookmark": ["use_case", "bookmark", "completed"],
               "usecase_interactions": [
                    "interaction_time",
                    "use_case",
                    "bookmark",
                    "completed",
                    "Data_Match_Discovered",
                    "distinct_UCE_Data_Category",
                    "distinct_Discovered_Sourcetypes",
                    "distinct_use_case_name"]}

    @Configuration()
    def map(self, records):
        """Map portion - not required"""
        # Acconding to docs map does not need to be implemented, but without it there's
        # an error: 'function' object has no attribute 'ConfigurationSettings'
        # Reported in: https://github.com/remg427/misp42splunk/issues/102
        return records

    def reduce(self, events):
        """Overwrite or Append (default) to specific csv's"""
        if not len(self.fieldnames) == 1:
            raise ValueError(
                f"Need one argument, the name of the table. {len(self.fieldnames)} given"
            )
        table = self.fieldnames[0]
        if table not in ("usecase_bookmark", "usecase_interactions"):
            raise ValueError(f"Table {table} not in the authorized list")
        path = os.path.join(APP_DIR, "lookups", table + ".csv")
        try:
            csvfile = open(path, "r")
        except FileNotFoundError:
            header = None
        else:
            with csvfile:
                reader = csv.DictReader(csvfile)
                header = reader.fieldnames
        if self.append:
            open_mode = "a"
        else:
            open_mode = "w"
            header = None
        with open(path, open_mode) as csvfile:
            fieldnames = header
            if header is None:
                fieldnames = self.headers[table]
            writer = csv.DictWriter(
                csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_NONNUMERIC
            )
            if header is None:
                writer.writeheader()
            for event in events:
                event = {field: value for field, value in event.items() if value}
                writer.writerow(event)
                yield event


dispatch(UceUpdateTableCommand, sys.argv, sys.stdin, sys.stdout, __name__)
