#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test  # isort: skip # noqa: F401
import sys

from splunklib.searchcommands import dispatch, Configuration, ReportingCommand

import snowrecordstream_helper as srh


@Configuration(requires_preop=True, run_in_preview=False)
class SnowrecordstreamCommand(ReportingCommand):
    """
    Reporting command to create or update record in ServiceNow table
    """

    @Configuration()
    def map(self, records):
        """
        Processes input events and computes partial results.

        param records: Generator yielding OrderedDicts (Splunk search events)
        :yield: dict - response result
        """
        for record in records:
            yield record

    def reduce(self, records):
        """
        This method receives the intermediate results produced during the map phase
        and yields them directly as the final output to be displayed in format.

        :param records: Generator of intermediate result dictionaries
        :yield: dict - Final results to be shown in the output table
        """
        results = srh.SnowRecordStreamHelper(self, records).handle()
        for record in results:
            yield record


dispatch(SnowrecordstreamCommand, sys.argv, sys.stdin, sys.stdout, __name__)
