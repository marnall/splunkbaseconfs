"""
Query idefense DOMAIN api with provided params.

Usage in Splunk -> |idefenseGetDomain <optional args, kwargs>

Arguments - usage in Splunk ->

Keyword arguments - usage in Splunk ->
"""
import os
import sys
import idefense_splunk

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration

APP_NAME = "TA-idefense"

file_name = os.path.splitext(os.path.basename(__file__))[0]

@Configuration()
class iDefenseGetDomain(GeneratingCommand):
    idefense_search = idefense_splunk.iDefense_search_commands(logfilename=file_name)
    logger = idefense_search.logger

    (earliest, latest, severity_to, severity_from, confidence_from, confidence_to, fields, Output_Threatlist,
     Output_KVstore) = idefense_search.setoptions()

    def generate(self):
        self.idefense_search.queryiDefense(self.service, "domain")
        yield from self.idefense_search.outputSearchResultsGenerator()

    def prepare(self):
        self.idefense_search.format_options(self.earliest, self.latest, self.severity_to, self.severity_from,
                                            self.confidence_from, self.confidence_to, self.fields,
                                            self.Output_Threatlist, self.Output_KVstore)

if __name__ == '__main__':

    sysout = idefense_splunk.syswriter()

    dispatch(iDefenseGetDomain, sys.argv, sys.stdin, sysout, __name__)
