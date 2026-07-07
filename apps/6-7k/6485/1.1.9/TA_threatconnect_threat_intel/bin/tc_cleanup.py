#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Download ThreatConnect Owner Information Command"""

# standard library
import os
import sys
from inspect import trace

# must be imported before packages in bin/lib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib_1_1_9"))

# standard library
import json
import time

# third-party
import splunklib.results as results
from splunklib.searchcommands import Configuration, dispatch
from splunklib.searchcommands.generating_command import GeneratingCommand
from threatconnect_splunk.utils import Utils


@Configuration()
class CleanupCommand(GeneratingCommand):
    """Command to download owner data from ThreatConnect API.

    Usage:
    | tccleanup
    """

    _search_uuids = None
    results = []

    def finish(self):
        """Implement finish method."""
        search = self.metadata.searchinfo.search.strip("\n")
        self.logger.info(f"""action=completed, command='{search}\'""")
        super().finish()

    def prepare(self):
        """Implement prepare method."""
        super().prepare()
        # splunk dispatch seems to call the command multiple times before service is available
        if self.metadata.action.lower() != "execute":
            return False

        search = self.metadata.searchinfo.search.strip("\n")
        self.logger.info(f"""action=started, command='{search}\'""")
        return True

    @property
    def old_indicator_uuids_spl(self):
        return (
            'search index="tc_indicator_data" | spath "metadata.uuid5" output="uuid5" '
            '| search NOT [search index="tc_indicator_data" '
            '| spath "metadata.uuid5" output="uuid5" | dedup uuid5]'
        )

    @property
    def deleted_indicator_spl(self):
        return (
            'search index = tc_indicator_data | spath "metadata.deleted" output="deleted" '
            "| search deleted=true"
        )

    @property
    def old_search_uuids_spl(self):
        return (
            'search index = tc_indicator_data | spath "metadata.search_uuid5" '
            f"""| search search_uuid != {" AND search_uuid != ".join(self.search_uuids)}"""
        )

    def search(self, search, **kwargs):
        """Execute a Splunk Search."""
        self.service.parse(search, parse_only=True)
        job = self.service.jobs.create(search, **kwargs)
        while True:
            while not job.is_ready():
                pass

            stats = {
                "isDone": job["isDone"],
                "doneProgress": float(job["doneProgress"]) * 100,
                "scanCount": job["scanCount"],
                "eventCount": job["eventCount"],
                "resultCount": job["resultCount"],
            }
            time.sleep(10)
            if stats["isDone"] == "1":
                self.logger.info(f"Search stats: {stats}")
                break

        return job

    def generate(self):
        """Implement generate command for downloading owners."""
        # retrieve owner data from ThreatConnect
        search_response = self.search(f"{self.old_search_uuids_spl} | delete")
        self.results.append({"message": f"SPL: {self.old_search_uuids_spl}"})
        for result in self.result_reader(search_response.results()):
            self.results.append({"message": f"""Deleted: {result.get("deleted")}"""})

        search_response = self.search(f"{self.old_indicator_uuids_spl} | delete")
        self.results.append({"message": f"SPL: {self.old_indicator_uuids_spl}"})
        for result in self.result_reader(search_response.results()):
            self.results.append({"message": f"""Deleted: {result.get("deleted")}"""})

        self.results.append({"message": f"SPL: {self.deleted_indicator_spl}"})
        search_response = self.search(f"{self.deleted_indicator_spl} | delete")
        for result in self.result_reader(search_response.results()):
            self.results.append({"message": f"""Deleted: {result.get("deleted")}"""})

        # display the results
        for r in self.results:
            yield r

    @staticmethod
    def result_reader(search_results):
        """[summary]

        Args:
            search_results ([type]): [description]
        """
        for data in results.ResultsReader(search_results):
            yield data

    @property
    def index_name(self):
        if self._index_name is None:
            searches = self.service.get(
                "data/inputs/tc_download_iocs/", output_mode="json", count=0
            ).body.read()
            self._index_name = ...

        return self._index_name

    @property
    def search_uuids(self):
        """Return an instance of Requests Session configured for the ThreatConnect API."""
        if self._search_uuids is None:
            searches = self.service.get(
                "data/inputs/tc_download_iocs/", output_mode="json", count=0
            ).body.read()
            searches = searches.decode("utf8").replace("'", '"')
            searches = json.loads(searches)
            self._search_uuids = []
            searches = searches.get("entry", [])
            utils = Utils()
            for search in searches:
                name = search.get("name", "")
                content = search.get("content", {})
                fields = [
                    i.strip() for i in content.get("fields", "").split(",") if i.strip()
                ]
                owners = [
                    f"{i.strip()}"
                    for i in content.get("owners", "").split(",")
                    if i.strip()
                ]
                tql = content.get("tql", "")

                self._search_uuids.append(
                    utils.generate_uuid_from_search(name, tql, owners, fields)
                )
        return self._search_uuids


if __name__ == "__main__":
    try:
        dispatch(CleanupCommand, sys.argv, sys.stdin, sys.stdout, __name__)
    except:
        # standard library
        import traceback

        print(traceback.format_exc(), file=sys.stderr)
