#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Generating Module"""

# standard library
import io
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib_1_1_9"))

# third-party
from base_generating_command import BaseGeneratingCommand
from splunklib import results
from threatconnect_splunk import TCS


class BaseSearchCommand(BaseGeneratingCommand):
    """Base Generating Class."""

    # properties
    filename = os.path.basename(__file__)
    results = []
    _tcs = None

    @property
    def tcs(self):
        """Instance of ThreatConnect Splunk Module."""
        if self._tcs is None:
            self._tcs = TCS(logger=self.logger, service=self.service)
        return self._tcs

    def iterate(self, job, count=50_000):
        offset = 0
        result_count = int(job["resultCount"])
        while offset < result_count:
            start_time = time.time()
            self.tcs.logger.debug(
                f"[search] processing results: offset={offset}, result_count={result_count:,}"
            )
            kwargs_paginate = {"count": count, "offset": offset}
            for result in results.JSONResultsReader(
                io.BufferedReader(job.results(**kwargs_paginate, output_mode="json"))
            ):
                if isinstance(result, results.Message):
                    # handle error
                    self.tcs.logger.error(f"message={result}")
                    continue
                yield result
            offset += count
            self.log_execution_time("iterate-pagination", start_time)
