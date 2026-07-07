#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
"""
Create scheduling jobs
"""

import logging
import socket

import citrix_netscaler_data_loader as ndl
from ta_util2 import job_factory as jf

_LOGGER = logging.getLogger("ta_citrix_netscaler")


class CitrixNetscalerCollectionJob(jf.Job):
    def __init__(self, job_id, config, data_collect_func):
        super(CitrixNetscalerCollectionJob, self).__init__(job_id, config)
        if not config.get("host", None):
            config["host"] = socket.gethostname()
        self._config = config
        self._func = data_collect_func

    def __call__(self):
        _LOGGER.debug(
            "Start collecting from %s, %s.",
            self._config["url"],
            self._config["api_endpoint"],
        )
        results = self._func()
        if results:
            events = "".join(("<stream>{}</stream>".format(r) for r in results))
            self._config["event_writer"].write_events(events)
        _LOGGER.debug(
            "End collecting from %s, %s.",
            self._config["url"],
            self._config["api_endpoint"],
        )

    def get(self, key, default=None):
        return self._config.get(key, default)

    def __hash__(self):
        return super(CitrixNetscalerCollectionJob, self).__hash__()

    def __lt__(self, other):
        return self.__hash__() < other.__hash__()

    def __gt__(self, other):
        return self.__hash__() > other.__hash__()

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()


class CitrixNetscalerJobFactory(jf.JobFactory):
    def _create_job(self, job_config):
        job_config["event_writer"] = self._event_writer
        loader = ndl.CitrixNetscaler(job_config)
        job_id = job_config["url"] + "_" + job_config["api_endpoint"]
        return CitrixNetscalerCollectionJob(job_id, job_config, loader.collect_data)
