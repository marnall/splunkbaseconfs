#!/usr/bin/python
#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""
This is the main entry point for Citrix NetScaler TA
"""
import import_declare_test  # isort: skip # noqa: F401
import os
import os.path as op
import queue
import re
import sys
import time
import traceback

import citrix_netscaler_job_factory as jf
import ta_util2
from citrix_netscaler_config import CitrixNetscalerConfig
from solnlib import file_monitor
from splunklib import modularinput as smi
from ta_util2 import configure as conf
from ta_util2 import data_loader as dl
from ta_util2 import event_writer
from ta_util2 import job_scheduler as sched
from ta_util2 import job_source as js
from ta_util2 import utils

_LOGGER = utils.setup_logging("ta_citrix_netscaler")


def _setup_signal_handler(data_loader):
    """
    Setup signal handlers
    @data_loader: data_loader.DataLoader instance
    """

    def _handle_exit(signum, frame):
        _LOGGER.info("Citrix NetScaler TA is going to exit...")
        data_loader.tear_down()

    utils.handle_tear_down_signals(_handle_exit)


def _get_file_change_handler(data_loader, meta_configs):
    def reload_and_exit(changed_files):
        changed = [f for f in changed_files if not f.endswith(".signal")]
        if changed:
            _LOGGER.info("Reload conf %s", changed)
            conf.reload_confs(
                changed,
                meta_configs["session_key"],
                meta_configs["server_uri"],
            )
        data_loader.tear_down()

    return reload_and_exit


def _setup_logging(loglevel="INFO", refresh=False):
    ta_util2.setup_logging_for_frmk(loglevel, refresh)
    utils.setup_logging("ta_citrix_netscaler", loglevel, refresh)
    utils.setup_logging("ta_app_conf", loglevel, refresh)


def _get_ucs_configs(meta_configs, inputs):
    _setup_logging()
    ucs_config = CitrixNetscalerConfig(meta_configs)
    try:
        ucs_config.encrypt_credentials()
    except Exception as error:
        _LOGGER.info("Caught Error: {}".format(error))
        sys.exit(0)
    if op.isfile(ucs_config.task_file_w_path):
        tasks = ucs_config.get_tasks(inputs)
    else:
        tasks = []

    if tasks:
        loglevel = tasks[0].get("log_level", "INFO")
        if loglevel != "INFO":
            _setup_logging(loglevel, True)
    else:
        _LOGGER.info(
            "No valid NetScaler inputs. This add-on will do nothing and quit now. "
            "Make sure the NetScaler inputs have been correctly configured "
            "with valid appliances and templates. "
            "Refer to ta-app.conf.log for more details."
        )
        return None

    return tasks


def proxy_port_value_validation(value):
    """
    This function returns False if proxy port has unsupported value. Otherwise, it returns true.
    """
    try:
        proxy_port_value = int(value)
        if proxy_port_value <= 0 or proxy_port_value > 65535:
            _LOGGER.error(
                "Field Proxy Port should be within the range of [1 and 65535]"
            )
            return False
    except ValueError:
        _LOGGER.error(
            "Invalid Proxy Port value in splunk_ta_citrix_netscaler_settings.conf file. "
            "To start data collection please provide valid proxy port value."
        )
        return False
    except TypeError:
        _LOGGER.error(
            "No Proxy Port value in splunk_ta_citrix_netscaler_settings.conf file. "
            "To start data collection please provide valid proxy port value."
        )
        return False
    return True


class ModinputJobSource(js.JobSource):
    def __init__(self, tasks):
        self._done = False
        self._job_q = queue.Queue()
        self.put_jobs(tasks)

    def put_jobs(self, jobs):
        for job in jobs:
            self._job_q.put(job)

    def get_jobs(self, timeout=1):
        jobs = []
        try:
            while 1:
                jobs.append(self._job_q.get(timeout=timeout))
        except queue.Empty:
            return jobs


class CitrixNetscaler(smi.Script):
    def __init__(self):
        super(CitrixNetscaler, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme("citrix_netscaler")
        scheme.description = "NetScaler Input"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = True

        scheme.add_argument(
            smi.Argument(
                "name",
                title="Name",
                description="Name",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "description",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "servers",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "templates",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "duration",
                required_on_create=True,
            )
        )

        return scheme

    def validate_input(self, definition):
        return

    def stream_events(self, inputs, ew):

        _LOGGER.info("Start Citrix NetScaler TA")

        _LOGGER.debug("Starting unused files/configuration check in TA")
        SPLUNK_HOME = os.environ["SPLUNK_HOME"]
        dirPath = op.join(
            SPLUNK_HOME,
            op.join(
                "etc",
                op.join("apps", op.join("Splunk_TA_citrix-netscaler", "local")),
            ),
        )

        if op.exists(op.join(dirPath, "citrix_netscaler_tasks.conf")):
            _LOGGER.warn(
                "citrix_netscaler_tasks.conf is not used anymore now, please remove it from this path: %s",
                op.join(dirPath, "citrix_netscaler_tasks.conf"),
            )

        if op.exists(op.join(dirPath, "citrix_netscaler.conf")):
            _LOGGER.warn(
                "citrix_netscaler.conf is not used anymore now, please remove it from this path: %s",
                op.join(dirPath, "citrix_netscaler.conf"),
            )
        _LOGGER.debug("Completed unused files/configuration check in TA")

        try:
            meta_configs = self._input_definition.metadata
            meta_configs["app_name"] = utils.get_appname_from_path(
                op.dirname(op.dirname(op.abspath(__file__)))
            )
            tasks = _get_ucs_configs(meta_configs, inputs.inputs)

        except Exception:
            _LOGGER.error(
                "Failed to setup config for Citrix NetScaler TA: %s",
                traceback.format_exc(),
            )
            raise

        if not tasks:
            _LOGGER.info("Stop Citrix NetScaler TA")
            sys.exit(0)

        for task in tasks:
            # Validate the proxy port value
            proxy_enabled = task.get("proxy_enabled") or "0"
            proxy_port_value = task.get("proxy_port", 0)
            if (
                utils.is_true(proxy_enabled)
                and proxy_port_value
                and not proxy_port_value_validation(proxy_port_value)
            ):
                return

            # Validate http_scheme is valid, i.e. http or https
            http_scheme = task["http_scheme"]
            _LOGGER.debug(
                "Validating http_scheme parameter value from splunk_ta_citrix_netscaler_settings.conf"
            )
            if http_scheme.lower() not in ("http", "https"):
                _LOGGER.error(
                    "Incorrect http_scheme value, %s, in the splunk_ta_citrix_netscaler_settings.conf "
                    "file of the Splunk Add-on for Citrix Netscaler. To resume data collection, "
                    "enter a valid http_scheme value (http or https)",
                    http_scheme,
                )
                return
            _LOGGER.debug(
                "http_scheme parameter value %s, successfully validated",
                http_scheme,
            )

            # Validate host format is valid, i.e. without http_scheme appended
            host = task["url"]
            _LOGGER.debug("Validating format of Citrix Netscaler Host")
            if re.search(":\/\/", host):  # noqa: W605
                _LOGGER.error(
                    "The format of the Citrix Netscaler host %s is invalid. To resume data collection, "
                    "enter the host in the citrix_netscaler_servers.conf file or in configuration page "
                    "of the Splunk Add-on for Citrix Netscaler in one of the following formats: "
                    "mycitrixserver.com OR mycitrixserver.com:8080",
                    host,
                )
                return
            _LOGGER.debug(
                "Format of Citrix Netscaler host %s, successfully validated",
                host,
            )

            # Validate duration field value is valid
            if not (
                isinstance(task.get("duration"), int)
                and 1 <= task.get("duration", 0) <= 31536000
            ):
                _LOGGER.warn(
                    "Got unexpected value {} of 'duration' field for input '{}' while collecting data of "
                    "api endpoint '{}'. Duration should be an integer and within the range of 1 to 31536000. "
                    "Setting the default value. You can either change it in inputs.conf file or "
                    "edit 'Collection interval' on Inputs page.".format(
                        task.get("duration"),
                        task.get("name").replace("citrix_netscaler://", ""),
                        task.get("api_endpoint"),
                    )
                )

                task["duration"] = 3600

        writer = event_writer.EventWriter()
        job_src = ModinputJobSource(tasks)
        job_factory = jf.CitrixNetscalerJobFactory(job_src, writer)
        job_scheduler = sched.JobScheduler(job_factory)
        data_loader = dl.GlobalDataLoader.get_data_loader(tasks, job_scheduler, writer)
        callback = _get_file_change_handler(data_loader, meta_configs)
        files_to_monitor = (
            CitrixNetscalerConfig.server_file_w_path,
            CitrixNetscalerConfig.task_file_w_path,
            CitrixNetscalerConfig.template_file_w_path,
            CitrixNetscalerConfig.ucs_file_w_path,
            CitrixNetscalerConfig.ucs_default_file_w_path,
            CitrixNetscalerConfig.signal_file_w_path,
        )
        conf_monitor = file_monitor.FileChangesChecker(callback, files_to_monitor)
        data_loader.add_timer(conf_monitor.check_changes, time.time(), 60)

        _setup_signal_handler(data_loader)
        data_loader.run()


if __name__ == "__main__":
    exit_code = CitrixNetscaler().run(sys.argv)
    sys.exit(0)
