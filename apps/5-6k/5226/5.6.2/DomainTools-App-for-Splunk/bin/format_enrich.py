from __future__ import absolute_import
import os
import sys
import json
import time
from settings import APP_ID

splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(
    os.path.join(splunkhome, "etc", "apps", APP_ID, "lib")
)
from splunklib.searchcommands import (
    dispatch,
    EventingCommand,
    Configuration,
    Option,
    validators,
)
from dt_logger import DTLogger
import dt_exception_messages
from shared_enrich_formatters import update_row


@Configuration()
class FormatEnrichCommand(EventingCommand):
    """This custom search command formats iris-enrich or iris-investigate response

        Inherits from the EventingCommand custom search type. Override the `transform` method as the entrypoint to this script


        Example:
            | dtirisinvestigate domain=domaintools.com | dtformatenrich
    """

    feature = Option(
        doc="""
                **Syntax:** **feature=***<feature>*
                **Description:** Feature in the app where this was called""",
        default="adhoc",
        require=False,
    )

    def get_user(self):
        """get current logged in user"""
        return self.metadata.searchinfo.username

    def format_row(self, result):
        """format Iris Enrich response to Splunk row"""
        output = []

        try:
            row = {
                "dt_queued": False,
                "dt_retrieved": time.time(),
                "dt_observed": False,
                "dt_event_seen": False,
                "dt_unknown": False,
                "_raw": json.dumps(result),
            }

            update_row(row, result)

            output.append(row)
        except Exception as e:
            self.dt_log.error(
                "error mapping domain. exception type: {0}, exception message {1}, domain: {2}".format(
                    type(e).__name__, e, json.dumps(result)
                )
            )

        return output

    def transform(self, records):
        """This is the entry point to an EventingCommand subclass. You must override this method

            :param records: generator iterator of rows from previous command of SPL search
            :return: generator rows to pass on to next command of SPL search after transform
        """
        self.dt_log = DTLogger(
            "none", os.path.basename(__file__), self.get_user(), self.feature
        )
        self.dt_log.debug("starting format_enrich.py")

        for record in records:
            try:
                record = json.loads(record["_raw"])

                output = self.format_row(record)
                for row in output:
                    yield row
            except Exception as e:
                self.dt_log.error(
                    "error formatting domain: {0}, exception type: {1}, exception message: {2}".format(
                        json.dumps(record), type(e).__name__, e
                    )
                )
                raise Exception(dt_exception_messages.generic.format(e))

        self.dt_log.info("completed format_enrich.py")


dispatch(FormatEnrichCommand, sys.argv, sys.stdin, sys.stdout, __name__)
