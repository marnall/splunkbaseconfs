#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import socket

import import_declare_test  # noqa F401 # isort: skip
import os.path as op
import sys
import traceback
from datetime import datetime, timedelta  # noqa F401

import box_helper
import log_files
import requests
from box_client import BoxClient
from box_config import BoxConfig, BoxConfMonitor  # noqa
from solnlib import conf_manager
from solnlib.utils import handle_teardown_signals, is_true, remove_http_proxy_env_vars
from splunk import rest
from splunklib import modularinput as smi
import box_data_loader as bdl
import box_utility
from solnlib import log
import thread_pool

requests.urllib3.disable_warnings()  # type: ignore

remove_http_proxy_env_vars()
all_logs = log_files.get_all_logs()
all_logs.append("ta_box")

_LOGGER = log.Logs().get_logger(log_files.ta_box)


APP_NAME = "Splunk_TA_box"
SESSION_KEY = "session_key"
SERVER_URI = "server_uri"


def _setup_signal_handler(box):
    """
    Setup signal handlers
    @box: box_data_loader.BoxBase instance
    """

    def _handle_exit(signum, frame):
        _LOGGER.info("Execution about to get stopped due to SIGTERM.")
        box.revert_checkpoint()
        thread_pool.stop_thread_pool(box.config.get("rest_endpoint"))
        sys.exit(0)

    handle_teardown_signals(_handle_exit)


def _setup_logging(loglevel="INFO", refresh=False):
    for logfile in all_logs:
        logger = log.Logs().get_logger(logfile)
        logger.setLevel(loglevel)


def _check_interval(interval, input_name):
    if not interval:
        _LOGGER.error("Field 'interval' is required for input '{}'".format(input_name))
        return False

    try:
        if 0 < int(interval) < 31536001:
            return True
        else:
            _LOGGER.error(
                "Got unexpected value {} of 'interval' field for input '{}'. "
                "Interval should be in between 1 and 31536000 seconds. "
                "You can either change it in inputs.conf file or edit "
                "'Collection interval' on Inputs page.".format(interval, input_name)
            )
            return False
    except ValueError:
        _LOGGER.error(
            "Got unexpected value {} of 'interval' field for input '{}'. Interval should be an integer. "
            "You can either change it in inputs.conf file or edit 'Collection interval' on Inputs page.".format(
                interval, input_name
            )
        )
        return False


def get_account_id(session_key, account_info, proxy_config, box_config, account_name):
    """This function is used to get the account id using the Box SDK."""
    params = {}
    params["session_key"] = session_key
    params["appname"] = APP_NAME
    params.update(proxy_config)
    params.update(box_config)
    params.update(account_info)
    params["account"] = account_name

    if "disable_ssl_certificate_validation" in params:
        params["disable_ssl_certificate_validation"] = is_true(
            params["disable_ssl_certificate_validation"]
        )

    client = BoxClient(params, logger=_LOGGER)
    try:
        account_id = box_helper.fetch_data(
            client, box_helper.fetch_account_id_uri(params), _LOGGER
        ).get("id")
    except Exception as err:
        account_id = None
        _LOGGER.error("Failed to fetch account_id, " "reason={}".format(err))

    return account_id


class BoxService(smi.Script):
    def __init__(self):
        super(BoxService, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme("Splunk Add-on for Box")
        scheme.description = "Enable Box RESTful inputs"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                "input_name", title="Name", description="Name", required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                "name", title="Name", description="Name", required_on_create=True
            )
        )

        scheme.add_argument(
            smi.Argument(
                "account",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "rest_endpoint",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "collect_folder",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "collect_collaboration",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "collect_file",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "collect_task",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "created_after",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "duration",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "folder_fields",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "file_fields",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "task_fields",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "comment_fields",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "user_fields",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "event_delay",
                required_on_create=False,
            )
        )

        return scheme

    def validate_input(self, definition):
        return

    def stream_events(self, inputs, ew):
        meta_configs = self._input_definition.metadata

        for input_name, input_item in inputs.inputs.items():  # py2/3
            if "account" not in input_item:
                rest.simpleRequest(
                    "messages",
                    meta_configs[SESSION_KEY],
                    postargs={
                        "severity": "error",
                        "name": "Box error message",
                        "value": "Some configurations are missing in Splunk Add-on for Box. "
                        "Please fix the configurations to resume data collection.",
                    },
                    method="POST",
                )
        try:
            settings_cfm = conf_manager.ConfManager(
                meta_configs[SESSION_KEY],
                APP_NAME,
                realm="__REST_CREDENTIAL__#{}#configs/conf-splunk_ta_box_settings".format(
                    APP_NAME
                ),
            )

            splunk_ta_box_settings_conf = settings_cfm.get_conf(
                "splunk_ta_box_settings"
            ).get_all()

            loglevel = splunk_ta_box_settings_conf["logging"].get("loglevel", "INFO")
            _setup_logging(loglevel)
            if not bool(inputs.inputs):
                _LOGGER.info(
                    "No configured Historical Querying inputs found. To collect data from Box, "
                    "configure new input(s) or "
                    "update existing input(s) either from Inputs page of the Add-on or manually from inputs.conf."
                )
                return 0

            try:
                if not op.isfile(
                    op.join(
                        op.dirname(op.realpath(op.dirname(__file__))),
                        "local",
                        "splunk_ta_box_account.conf",
                    )
                ):
                    raise Exception("Box account conf file not found")
                account_cfm = conf_manager.ConfManager(
                    meta_configs[SESSION_KEY],
                    APP_NAME,
                    realm="__REST_CREDENTIAL__#{}#configs/conf-splunk_ta_box_account".format(
                        APP_NAME
                    ),
                )

                splunk_ta_box_account_conf_obj = account_cfm.get_conf(
                    "splunk_ta_box_account"
                )
                splunk_ta_box_account_conf = splunk_ta_box_account_conf_obj.get_all()
            except:  # noqa E722
                _LOGGER.error(
                    "Either account configuration does not exist or there was an error while fetching the account configuration"  # noqa
                )
                return

            box_conf = account_cfm.get_conf("box").get_all()

            account_info = {}
            stanza_configs = []
            for k, v in splunk_ta_box_account_conf.items():  # py2/3
                account_info[k] = v

            account_id_dict = {}
            for input_name, input_item in inputs.inputs.items():  # py2/3
                input_item["name"] = input_name
                input_item["created_after"] = BoxConfig._get_datetime(
                    input_item.get("created_after")
                )
                account_id = None
                account_id_present = False
                try:
                    account_config = account_info[input_item["account"]]
                    box_config = box_helper.get_box_config(meta_configs[SESSION_KEY])
                    proxy_config, _ = box_helper.get_proxy_logging_config(
                        meta_configs[SESSION_KEY]
                    )  # noqa: E501

                    if input_item["account"] in account_id_dict:
                        account_id = account_id_dict[input_item["account"]]
                        account_id_present = True
                    else:
                        account_id = get_account_id(
                            meta_configs[SESSION_KEY],
                            account_config,
                            proxy_config,
                            box_config,
                            input_item["account"],
                        )
                        account_id_dict[input_item["account"]] = account_id

                    if account_id is None:
                        _LOGGER.info(
                            "Box account ID not found for account {}".format(
                                input_item["account"]
                            )
                        )
                        pass
                except Exception as e:
                    _LOGGER.error(
                        "Error occured while getting the account Id: {}".format(e)
                    )

                if account_id_present:
                    for k, v in account_info[input_item["account"]].items():  # py2/3
                        input_item[k] = v
                else:
                    updated_info = {}
                    try:
                        updated_account_info = splunk_ta_box_account_conf_obj.get_all()
                        for k, v in updated_account_info.items():  # py2/3
                            updated_info[k] = v
                        for k, v in updated_info[
                            input_item["account"]
                        ].items():  # py2/3
                            input_item[k] = v
                    except Exception as e:
                        _LOGGER.error(
                            "Error occured while fetching the updated values of account: {}".format(
                                e
                            )
                        )
                        continue

                for k, v in box_conf["box_default"].items():  # py2/3:
                    if k not in input_item:
                        input_item[k] = v

                if "disable_ssl_certificate_validation" in input_item:
                    input_item["disable_ssl_certificate_validation"] = is_true(
                        input_item["disable_ssl_certificate_validation"]
                    )

                input_item["account_id"] = account_id

                for k, v in meta_configs.items():  # py2/3
                    input_item[k] = v
                if splunk_ta_box_settings_conf is not None:
                    for k, v in splunk_ta_box_settings_conf["proxy"].items():  # py2/3:
                        input_item[k] = v
                    for x, y in splunk_ta_box_settings_conf["logging"].items():  # py2/3
                        input_item[x] = y

                # Perform migration of duration field to interval field for multi instance mode
                if (
                    input_item.get("duration")
                    != "Deprecated - Please use the interval field instead"
                ):
                    box_utility.migrate_duration_to_interval(
                        input_name, input_item, meta_configs, _LOGGER, APP_NAME
                    )

                # Validate interval
                if "interval" not in input_item:
                    # Keeping the default value in case interval is not specified
                    input_item["interval"] = int(input_item["collection_interval"])
                elif _check_interval(input_item["interval"], input_item["name"]):
                    input_item["interval"] = int(input_item["interval"])
                else:
                    default_interval = {
                        "events": 120,
                        "users": 604800,
                        "folders": 604800,
                        "groups": 604800,
                    }
                    input_item["interval"] = default_interval[
                        input_item["rest_endpoint"]
                    ]

                # default value of event_delay will be '0'; type:: str
                e_delay = (
                    int(input_item.get("event_delay"))
                    if input_item.get("event_delay")
                    else 0
                )
                e_interval = input_item["interval"]
                if e_delay and (e_delay > e_interval):
                    e_delay = max((e_interval - 10), (e_delay % e_interval))
                    _LOGGER.warn(
                        "Entered Delay ({} sec) is greater than Interval ({} sec) provided. "
                        " Using the delay: {} seconds.".format(
                            input_item["event_delay"], e_interval, e_delay
                        )
                    )

                input_item["event_delay"] = e_delay
                input_item["appname"] = APP_NAME
                stanza_configs.append(input_item)
                input_item["host"] = socket.gethostname()
                thread_pool.start_thread_pool(input_item["rest_endpoint"])

                rest_to_cls = {
                    "events": bdl.BoxEvent,
                    "folders": bdl.BoxFolder,
                    "users": bdl.BoxUser,
                    "groups": bdl.BoxGroup,
                }
                cls = rest_to_cls[input_item["rest_endpoint"]]
                client = BoxClient(input_item, logger=_LOGGER)
                box = cls(input_item, client)
                _setup_signal_handler(box)
                box.run()

                thread_pool.stop_thread_pool(input_item["rest_endpoint"])
        except Exception:
            _LOGGER.error("Error %s", traceback.format_exc())


if __name__ == "__main__":
    exit_code = BoxService().run(sys.argv)
    sys.exit(exit_code)
