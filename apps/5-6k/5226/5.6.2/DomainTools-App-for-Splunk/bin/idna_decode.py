from __future__ import absolute_import
import os, sys
from settings import APP_ID
import idna

from dt_logger import DTLogger
splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(
    os.path.join(splunkhome, "etc", "apps", APP_ID, "lib")
)
from splunklib.searchcommands import (
    dispatch,
    StreamingCommand,
    Configuration,
    Option,
    validators,
)

@Configuration(local=True)
class DomainExtractCommand(StreamingCommand):
    """This custom search command extracts the domain from a url.

    Inherits from the StreamingCommand custom search type. Override the `stream` method as the entrypoint to this script

    Attributes:
        field_in (str): Field to extract domains from
        field_out (str): Field to output domain in
        feature (str): Where this file was called from in the app

    Example:
        | makeresults | eval url="https://domaintools.com/apidocs" | dtdomainextract field_in=url field_out=domain
    """

    field_in = Option(
        doc="""
            **Syntax:** **field_in=***<in>*
            **Description:** Field to extract domains from""",
        require=True,
    )

    field_out = Option(
        doc="""
                **Syntax:** **field_out=***<out>*
                **Description:** Field to output domain in""",
        require=True,
    )

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

    def stream(self, records):
        """This is the entry point to a StreamingCommand subclass. You must override this method

        :param records: generator iterator of rows from previous command of SPL search
        :return: generator rows to pass on to next command of SPL search after transform
        """
        self.dt_log = DTLogger(
            "none", os.path.basename(__file__), self.get_user(), self.feature
        )
        self.dt_log.debug("starting idna_encode.py")

        for record in records:
            if self.field_in not in record:
                yield record
                continue

            domain = record[self.field_in]
            try:
                record[self.field_out] = idna.decode(domain.strip()).lower()
            except Exception as e:
                self.dt_log.error(e, {"domain": domain})

            yield record

        self.dt_log.debug("completed idna_encode.py")


dispatch(DomainExtractCommand, sys.argv, sys.stdin, sys.stdout, __name__)
