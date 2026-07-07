from __future__ import absolute_import
import os, sys
from settings import APP_ID

splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(
    os.path.join(splunkhome, "etc", "apps", APP_ID, "lib")
)
sys.path.append(
    os.path.join(splunkhome, "etc", "slave-apps", APP_ID, "lib")
)

from dt_logger import DTLogger
from splunklib.searchcommands import (
    dispatch,
    StreamingCommand,
    Configuration,
    Option,
    validators,
)
import dt_exception_messages
import re

@Configuration(local=True)
class DomainRefangCommand(StreamingCommand):
    """This custom search command refangs a url.

        Inherits from the StreamingCommand custom search type. Override the `stream` method as the entrypoint to this script

        Attributes:
            field_in (str): Field to get urls from
            field_out (str): Field to output refanged url
            feature (str): Where this file was called from in the app

        Example:
            | makeresults | eval url="hXXps://domaintools[.]com/apidocs" | dtdomainrefang field_in=url field_out=refanged_url
    """

    field_in = Option(
        doc="""
            **Syntax:** **field_in=***<in>*
            **Description:** Field to get urls from""",
        require=True,
    )

    field_out = Option(
        doc="""
                **Syntax:** **field_out=***<out>*
                **Description:** Field to output refanged url""",
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

    def refang(self, line):
        """Refangs a line of text. See: https://bitbucket.org/johannestaas/defang

        :param str line: the line of text to reverse the defanging of.
        :return: the "dirty" line with actual URIs
        """
        dirty_line = re.sub(r'\((\.|dot)\)', '.',
                            line, flags=re.IGNORECASE)
        dirty_line = re.sub(r'\[(\.|dot)\]', '.',
                            dirty_line, flags=re.IGNORECASE)
        dirty_line = re.sub(r'(\s*)h([x]{1,2})p([s]?)\[?:\]?//', r'\1http\3://',
                            dirty_line, flags=re.IGNORECASE)
        dirty_line = re.sub(r'(\s*)(s?)fxp(s?)\[?:\]?//', r'\1\2ftp\3://',
                            dirty_line, flags=re.IGNORECASE)
        dirty_line = re.sub(r'(\s*)\(([-.+a-zA-Z0-9]{1,12})\)\[?:\]?//', r'\1\2://',
                            dirty_line, flags=re.IGNORECASE)
        return dirty_line

    def stream(self, records):
        """This is the entry point to a StreamingCommand subclass. You must override this method

            :param records: generator iterator of rows from previous command of SPL search
            :return: generator rows to pass on to next command of SPL search after transform
        """
        self.dt_log = DTLogger(
            "none", os.path.basename(__file__), self.get_user(), self.feature
        )
        self.dt_log.debug("starting domain_refang.py")

        for record in records:
            if self.field_in not in record:
                yield record
                continue

            line = record[self.field_in]
            try:
                if isinstance(line, list):
                    record[self.field_out] = [self.refang(l) for l in line]
                else:
                    record[self.field_out] = self.refang(line)
                yield record
            except Exception as e:
                self.dt_log.error(
                    "error refanging domain: {0}, exception type: {1}, exception message: {2} feature: {3}".format(
                        line, type(e).__name__, e, self.feature
                    )
                )

        self.dt_log.debug("completed domain_refang.py")


dispatch(DomainRefangCommand, sys.argv, sys.stdin, sys.stdout, __name__)
