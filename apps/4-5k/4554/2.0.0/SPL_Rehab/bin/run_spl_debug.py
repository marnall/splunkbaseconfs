'''
File: run_spl_debug.py
Copyright Thomas West (tom.west1987@gmail.com)
This file is supplied in association with SPL Rehab and MUST NOT be
used outside the app without prior written permission
'''

import sys
import re
from devlib import SearchBreakdown


from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option

@Configuration(streaming=False, local=True, type='reporting')
class SearchDebug(GeneratingCommand):
    """Break Down Search."""
    user_search = Option(require=True)
    user_earliest = Option(require=True)
    user_latest = Option(require=True)

    def generate(self):
        self.user_search = re.sub(r'(\\?[\'"])\1',
                                  r'\1``DELETEME``\1',
                                  self.user_search)
        self.user_search = re.sub(r'(\|)(\\?[\'"])',
                                  r'\1``DELETEME``\2',
                                  self.user_search)

        self.user_search = self.user_search.lstrip()

        if self.user_earliest == "1970-01-01T01:00:00.000":
            self.user_earliest = "2000-01-01T01:00:00.000"


        search_lib = SearchBreakdown(self.user_search, prefix_search=True)
        record = {}
        record['genLine'] = []
        record['fullSearch'] = []
        record['commandCount'] = []
        record['commandLine'] = []
        record['commandSearch'] = []
        record['commandCombined'] = []
        record['command'] = []
        record['testing'] = []
        record['debug'] = []
        record['lineSid'] = []
        record['lineDuration'] = []
        record['lineResultCount'] = []

        # Get the collection of jobs
        sid = ""
        jobs = self.service.jobs

        i = 0
        for line in search_lib.search_lines:
            i += 1
            record['commandLine'].append(re.sub("``DELETEME``",
                                                "",
                                                str(line)))

            # Run a blocking search--search everything, return 1st 100 events

            kwargs_blockingsearch = {
                "exec_mode": "blocking",
                "search_mode":"normal",
                "adhoc_search_level":"verbose",
                "earliest_time":self.user_earliest,
                "latest_time":self.user_latest}

            if sid == "":
                searchquery_blocking = re.sub(
                    "``DELETEME``",
                    "",
                    str(line) + " `debugComment('ISINDEBUG')`")
            else:
                searchquery_blocking = (
                    "loadjob " +
                    str(sid) +
                    " `debugComment('ISINDEBUG')`| " +
                    re.sub("``DELETEME``", "", str(line)))

            # A blocking search returns the SID when the search is done
            job = jobs.create(searchquery_blocking, **kwargs_blockingsearch)

            sid = job["sid"]
            record['lineSid'].append(job["sid"])
            record['lineResultCount'].append(job["resultCount"])
            record['lineDuration'].append(job["runDuration"])


        for line in search_lib.search_lines:
            record['commandLine'].append(re.sub(
                "``DELETEME``",
                "",
                str(line)))

        for line in search_lib.generating:
            record['genLine'].append(re.sub(
                "``DELETEME``",
                "",
                str(line)))

        for line in search_lib.full_searches:
            record['fullSearch'].append(re.sub(
                "``DELETEME``",
                "",
                str(line)))

        for line in search_lib.state_count:
            record['commandCount'].append(re.sub(
                "``DELETEME``",
                "",
                str(line)))

        for line in search_lib.search_to_line:
            record['commandSearch'].append(re.sub(
                "``DELETEME``",
                "",
                str(line)))

        i = 0
        for line in search_lib.combined:
            record['commandCombined'].append(
                str(i+1) +
                "``RehabSEP``" +
                re.sub("``DELETEME``", "", str(line)))

            if len(record['lineSid']) > i:
                record['commandCombined'][i] = (
                    record['commandCombined'][i] +
                    "``RehabSEP``" +
                    str(record['lineSid'][i]) +
                    "``RehabSEP``" +
                    record['lineDuration'][i] +
                    "``RehabSEP``" +
                    str(record['lineResultCount'][i]))

                if i > 0:
                    record['commandCombined'][i] = (
                        record['commandCombined'][i] +
                        "``RehabSEP``" +
                        str(record['lineResultCount'][i-1]))
                else:
                    record['commandCombined'][i] = (
                        record['commandCombined'][i] +
                        "``RehabSEP``" +
                        str(record['lineResultCount'][i]))
            else:
                if len(record['lineSid']) == i and i != 0:
                    record['commandCombined'][i] = (
                        record['commandCombined'][i] +
                        "``RehabSEP``ERROR``RehabSEP``0``RehabSEP``ERROR``RehabSEP``" +
                        str(record['lineResultCount'][i-1]))
                else:
                    record['commandCombined'][i] = (
                        record['commandCombined'][i] +
                        "``RehabSEP``ERROR``RehabSEP``0``RehabSEP``0``RehabSEP``0")
            i += 1

        for line in search_lib.command:
            record['command'].append(re.sub("``DELETEME``", "", str(line)))

        for line in search_lib.test:
            record['testing'].append(re.sub("``DELETEME``", "", str(line)))

        for line in search_lib.debug:
            record['debug'].append(re.sub("``DELETEME``", "", str(line)))

        yield record


dispatch(SearchDebug, sys.argv, sys.stdin, sys.stdout, __name__)
