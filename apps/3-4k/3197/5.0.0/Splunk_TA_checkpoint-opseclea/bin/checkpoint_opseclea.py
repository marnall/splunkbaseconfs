#!/usr/bin/python

"""
This is the main entry point for My TA
"""
from __future__ import print_function
import ta_opseclea_import_declare
import os.path as op
import sys
import time
import traceback
import splunktalib.modinput as modinput
import splunktalib.common.util as utils
import splunktaucclib.common.log as stulog
import ta_opseclea_config as tc
from splunktaucclib.data_collection import ta_consts as c
from splunktaucclib.data_collection import ta_data_loader as dl
import splunktalib.orphan_process_monitor as opm
import splunktalib.file_monitor as fm
import ta_opseclea_data_collector as collector

utils.remove_http_proxy_env_vars()
stulog.reset_logger("modinput")
MAX_ONLINE_COUNT = 120


def do_scheme():
    """
    Feed splunkd the TA's scheme

    """

    print("""<scheme>
    <title>Splunk Add-on for {ta_short_name}</title>
    <description>Enable data inputs for {ta_name}</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <use_single_instance>true</use_single_instance>
    <endpoint>
      <args>
        <arg name="name">
          <title>{ta_name} Data Input Name</title>
        </arg>
        <arg name="description">
          <title>{ta_name}</title>
          <required_on_create>0</required_on_create>
          <required_on_edit>0</required_on_edit>
        </arg>
      </args>
    </endpoint>
    </scheme>
    """.format(ta_short_name="Check Point OPSEC LEA",
               ta_name="Check Point OPSEC LEA"))

def _setup_signal_handler(data_loader):
    """
    Setup signal handlers
    :data_loader: data_loader.DataLoader instance
    """

    def _handle_exit(signum, frame):
        stulog.logger.info("%s receives exit signal", c.ta_name)

        if data_loader is not None:
            data_loader.tear_down()
        stulog.logger.info("%s finishes handling exit signal", c.ta_name)

    utils.handle_tear_down_signals(_handle_exit)

def _handle_file_changes(data_loader):
    """
    :reload conf files and exit
    """

    def _handle_refresh(changed_files):
        stulog.logger.info("Detect %s changed, reboot itself", changed_files)
        data_loader.tear_down()
        stulog.logger.info("%s finishes rebooting itself", c.ta_name)

    return _handle_refresh

def _get_conf_files():
    cur_dir = op.dirname(op.dirname(op.abspath(__file__)))
    files = []
    for f in (c.ta_connection_conf, c.ta_opseclea_input_conf, c.ta_global_setting_conf):
        files.append(op.join(cur_dir, "local", c.client_prefix + f + ".conf"))
    return files

def run():
    """
    Main loop. Run this TA forever
    """
    # This is for stdout flush
    utils.disable_stdout_buffer()

    # http://bugs.python.org/issue7980
    time.strptime('2016-01-01', '%Y-%m-%d')
    tconfig = tc.create_ta_opseclea_config()
    stulog.set_log_level(tconfig.get_log_level())
    task_configs = tconfig.get_task_configs()
    online_count = sum(1 for task in task_configs if task[c.mode] == c.online)
    if online_count > MAX_ONLINE_COUNT:
        stulog.logger.error("There is too many online mode inputs. The count "
                            "is {} which should be less than {}".format(
            online_count, MAX_ONLINE_COUNT))
        return
    if not task_configs:
        stulog.logger.debug("No task and exiting...")
        return

    meta_configs = tconfig.get_meta_configs()
    if tconfig.is_shc_but_not_captain():
        # In SHC env, only captain is able to collect data
        stulog.logger.debug("This search header is not captain, will exit.")
        return

    loader = dl.create_data_loader(meta_configs)

    for config in task_configs:
        config[c.data_loader] = loader

    jobs = [collector.create_opseclea_data_collector(meta_configs, config)
            for config in task_configs]
    _setup_signal_handler(loader)

    monitor = fm.FileMonitor(_handle_file_changes(loader),
                             _get_conf_files())

    loader.add_timer(monitor.check_changes, time.time(), 10)

    # Add orphan process handling, which will check each 1 second
    orphan_checker = opm.OrphanProcessChecker(loader.tear_down)
    loader.add_timer(orphan_checker.check_orphan, time.time(), 1)

    loader.run(jobs)



def validate_config():
    """
    Validate inputs.conf
    """

    _, configs = modinput.get_modinput_configs_from_stdin()
    return 0


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
            sys.exit(validate_config())
        elif args[1] in ("-h", "--h", "--help"):
            usage()
        else:
            usage()
    else:
        stulog.logger.debug("Start %s task", c.ta_name)
        try:
            run()
        except Exception:
            stulog.logger.error("Encounter exception=%s",
                                traceback.format_exc())
        stulog.logger.debug("End %s task", c.ta_name)
    sys.exit(0)


if __name__ == "__main__":
    main()

