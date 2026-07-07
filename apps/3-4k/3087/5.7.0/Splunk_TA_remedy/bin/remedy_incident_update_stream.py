#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import remedy_incident_update_base as riub
import splunk.Intersplunk as sI


class RemedyIncidentUpdateStream(riub.RemedyIncidentUpdateBase):
    def __init__(self, results, dummyresults, settings):
        self.results = results
        self.dummyresults = dummyresults
        self.settings = settings
        super(RemedyIncidentUpdateStream, self).__init__()

    def _get_session_key(self):
        return self.settings["sessionKey"]

    def _get_events(self):
        return self.results


def main():
    results, dummyresults, settings = sI.getOrganizedResults()
    handler = RemedyIncidentUpdateStream(results, dummyresults, settings)
    handler.handle()


if __name__ == "__main__":
    main()
