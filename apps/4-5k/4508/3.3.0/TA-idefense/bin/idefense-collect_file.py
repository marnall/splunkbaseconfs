"""
Collects file hashes from indicators that are already downloaded (domain, ip and URL)

Usage in Splunk (no args required currently) -> |acticollectfile
"""

import os
import sys
import idefense_splunk

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
APP_NAME = "TA-idefense"

TIMEFORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
file_name = os.path.splitext(os.path.basename(__file__))[0]

@Configuration()
class iDefenseCollectFile(GeneratingCommand):
    idefense_files = idefense_splunk.iDefense_search_commands(logfilename=file_name)
    logger = idefense_files.logger

    (earliest, latest, severity_to, severity_from, confidence_from, confidence_to, fields, Output_Threatlist,
     Output_KVstore) = idefense_files.setoptions()

    def generate(self):
        for KVSTORES in (self.idefense_files.IP_KVSTORE,
                         self.idefense_files.URL_KVSTORE,
                         self.idefense_files.DOMAIN_KVSTORE):
            self.idefense_files.collectfileintel(self.service, KVSTORES)
            yield from self.idefense_files.outputSearchResultsGenerator()

    def prepare(self):
        self.idefense_files.format_options_file(self.earliest, self.latest, self.Output_Threatlist, self.Output_KVstore)

if __name__ == '__main__':

    sysout = idefense_splunk.syswriter()

    dispatch(iDefenseCollectFile, sys.argv, sys.stdin, sysout, __name__)
