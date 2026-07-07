#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import import_declare_test
import sys
import os.path as op
import queue
import time
import re

import ta_util2.utils as utils
import ta_util2.log_files as log_files
import was_consts as c

all_logs = log_files.get_all_logs()
all_logs.append(c.was_log)

_LOGGER = utils.setup_logging(c.was_log)

import ta_util2.job_scheduler as sched
import ta_util2.job_source as js
import ta_util2.data_loader as dl
import ta_util2.event_writer as event_writer
import ta_util2.configure as conf
import ta_util2.state_store as ss
import was_hpel_job_factory as jf
import was_config as wc
import was_consts as c


def _setup_signal_handler(data_loader):
    """
    Setup signal handlers
    @data_loader: data_loader.DataLoader instance
    """

    def _handle_exit(signum, frame):
        _LOGGER.info("WAS TA is going to exit...")
        data_loader.tear_down()

    utils.handle_tear_down_signals(_handle_exit)


def _get_file_change_handler(data_loader, meta_configs):
    def reload_and_exit(changed_files):
        _LOGGER.info("Reload conf %s", changed_files)
        conf.reload_confs(
            changed_files, meta_configs[c.session_key], meta_configs[c.server_uri]
        )
        data_loader.tear_down()

    return reload_and_exit


def _setup_logging(loglevel="INFO", refresh=False):
    for logfile in all_logs:
        utils.setup_logging(logfile, loglevel, refresh)


class ModinputJobSource(js.JobSource):
    def __init__(self, stanza_configs):
        self._done = False
        self._job_q = queue.Queue()
        self.put_jobs(stanza_configs)

    def put_jobs(self, jobs):
        for job in jobs:
            self._job_q.put(job)

    def get_jobs(self, timeout=0):
        jobs = []
        try:
            while 1:
                jobs.append(self._job_q.get(timeout=timeout))
        except queue.Empty:
            return jobs


def collect_hpel_log(was_config):
    tasks = wc.get_hpel_tasks(was_config)
    if not tasks:
        return

    writer = event_writer.EventWriter()
    job_src = ModinputJobSource(tasks)
    job_factory = jf.HpelJobFactory(job_src, writer)
    job_scheduler = sched.JobScheduler(job_factory)
    data_loader = dl.GlobalDataLoader.get_data_loader(tasks, job_scheduler, writer)
    callback = _get_file_change_handler(data_loader, was_config[c.meta])
    conf_monitor = wc.WasConfMonitor(callback)
    data_loader.add_timer(conf_monitor.check_changes, time.time(), 60)

    _setup_signal_handler(data_loader)
    data_loader.run()


def validate_configs(was_configs):
    """ """

    if was_configs.get(c.was_global_settings):
        was_global_settings = was_configs[c.was_global_settings]

        # validate index
        if not was_global_settings.get(c.index):
            _LOGGER.error(
                "Index not set for the data  collection. Please set an index."
            )
        elif len(was_global_settings[c.index]) > 80:
            _LOGGER.error(
                "Length of index name should be less than or equal to 80 characters"
            )

        # validate log_level
        if not was_global_settings.get(c.log_level):
            _LOGGER.info(
                "Log level for the add-on's logs not set. Using default log level."
            )
        elif was_global_settings[c.log_level].upper() not in ("DEBUG", "INFO", "ERROR"):
            _LOGGER.error(
                'Invalid log level specified for add-on\'s logs. Use "DEBUG", "INFO" or "ERROR".'
            )

        # validate was_install_dir
        if not was_global_settings.get(c.was_install_dir):
            _LOGGER.error(
                "WAS installation directory path not set for the data collection. Please set it to start collecting HPEL logs."
            )
        else:
            if len(was_global_settings.get(c.was_install_dir, "")) > 4096:
                _LOGGER.error(
                    "WAS installation directory path length should be less than or equal to 4096 characters"
                )

    else:
        # global settings have not been configured
        _LOGGER.error("Global settings not configured for the add-on.")

    if was_configs.get(c.was_hpel_settings):
        was_hpel_settings = was_configs[c.was_hpel_settings]

        # validate excluded_profiles
        if was_hpel_settings.get(c.excluded_profiles):
            if len(was_hpel_settings[c.excluded_profiles]) > 4096:
                _LOGGER.error(
                    "length of Excluded Profiles field should be less than or equal to 4096 characters"
                )

        # validate excluded_servers
        if was_hpel_settings.get(c.excluded_servers):
            if len(was_hpel_settings[c.excluded_servers]) > 4096:
                _LOGGER.error(
                    "length of Excluded Servers field should be less than or equal to 4096 characters"
                )
            if not re.match(
                "^([^,:\s]+:[^,:\s]+)(,[^,:\s]+:[^,:\s]+)*$",
                was_hpel_settings[c.excluded_servers],
            ):
                _LOGGER.error(
                    'Invalid format for Excluded Servers. It should be in "ProfileA:Server3,ProfileB:Server2" format.'
                )

        # validate duration
        if not was_hpel_settings.get(c.duration):
            _LOGGER.debug(
                "Duration for the HPEL log collection not set. Using default value as 60."
            )
        else:
            if not re.match("^\d+$", was_hpel_settings[c.duration]):
                _LOGGER.error(
                    "Duration field for HPEL data collection should be an integer."
                    ' Invalid value "{}" found.'.format(was_hpel_settings[c.duration])
                )

    else:
        _LOGGER.error("HPEL settings not configured for the add-on.")


def run():
    was_config, stanzas = wc.get_was_configs()
    log_level = was_config[c.was_global_settings].get(c.log_level, "INFO")
    _setup_logging(log_level, True)

    if not stanzas:
        return

    if was_config.get(c.was_hpel_settings):
        if was_config[c.was_hpel_settings].get(c.hpel_collection_enabled):
            _LOGGER.warn(
                'The deprecated "hpel_collection_enabled" parameter is being used.'
                'Please remove this parameter and use the "disabled" property under'
                "ibm_was://was_data_input stanza to toggle data collection."
            )
            if not utils.is_true(
                was_config[c.was_hpel_settings][c.hpel_collection_enabled]
            ):
                return

    validate_configs(was_config)
    collect_hpel_log(was_config)


def do_scheme():
    """
    Feed splunkd the TA's scheme
    """

    print(
        """
    <scheme>
    <title>Splunk Add-on for IBM WebSphere Application Server</title>
    <description>Collects IBM WebSphere Application Server logs</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <use_single_instance>true</use_single_instance>
    <endpoint>
      <args>
        <arg name="name">
          <title>IBM WAS TA Configuration</title>
        </arg>
        <arg name="was_data_input">
          <title>WAS Data Input</title>
        </arg>
      </args>
    </endpoint>
    </scheme>
    """
    )


def usage():
    """
    Print usage of this binary
    """

    hlp = "%s --scheme|--validate-arguments|-h"
    print(hlp % sys.argv[0], file=sys.stderr)
    sys.exit(1)


def main():
    """
    Main entry point
    """

    args = sys.argv
    if len(args) > 1:
        if args[1] == "--scheme":
            do_scheme()
        elif args[1] == "--validate-arguments":
            sys.exit(0)
        elif args[1] in ("-h", "--h", "--help"):
            usage()
        else:
            usage()
    else:
        _LOGGER.info("Start WAS TA")
        run()
        _LOGGER.info("Stop WAS TA")
    sys.exit(0)


if __name__ == "__main__":
    main()
