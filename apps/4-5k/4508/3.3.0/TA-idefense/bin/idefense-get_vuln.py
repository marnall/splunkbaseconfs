"""
Query idefense vulnerability api with provided params.

Usage in Splunk -> |acticollectvuln <optional args, kwargs>

Arguments

Keyword arguments ->

"""
import os
import sys
import idefense_splunk

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration

APP_NAME = "TA-idefense"
file_name = os.path.splitext(os.path.basename(__file__))[0]

@Configuration()
class iDefenseGetVuln(GeneratingCommand):
    idefense_search = idefense_splunk.iDefense_search_commands(logfilename=file_name)
    logger = idefense_search.logger

    (earliest, latest, severity_from, severity_to, cvss2_base_score_from, cvss2_base_score_to, cvss3_base_score_from,
    cvss3_base_score_to, cve_id, Output_KVstore, Output_Threatlist) = idefense_search.setVulnOptions()

    def generate(self):
        self.idefense_search.queryiDefense(self.service, "vuln")
        yield from self.idefense_search.outputSearchResultsGenerator()

    def prepare(self):
        self.idefense_search.format_vuln_options(self.earliest, self.latest, self.severity_from, self.severity_to,
                                            self.cvss2_base_score_from, self.cvss2_base_score_to, self.cvss3_base_score_from, self.cvss3_base_score_to,
                                            self.cve_id, self.Output_KVstore, self.Output_Threatlist)

if __name__ == '__main__':

    sysout = idefense_splunk.syswriter()

    dispatch(iDefenseGetVuln, sys.argv, sys.stdin, sysout, __name__)
