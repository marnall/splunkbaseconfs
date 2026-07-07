"""
s1_client.py ;; 2023-05-1
Written by ksmith for Aplura, LLC
Copyright (C) 2016-2024 Aplura, LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import logging as logger
import sys
import os
import json
import time
import uuid
from inspect import getframeinfo, stack

from Utilities import KennyLoggins
from s1_utilities import S1Utilities
from ModularInput import ModularInput
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path, getProductName
from splunk.util import normalizeBoolean
from datetime import datetime
import multiprocessing.dummy as mp
from s1_app_properties import __app_name__
import s1_paths
from management.mgmtsdk_v2_1.mgmt import Management as S1Management
from management.mgmtsdk_v2_1_apl.mgmt import Management as AplManagement

os.environ["SDK_LOG_PATH"] = make_splunkhome_path(
    ["var", "log", "splunk", __app_name__, "mgmt_sdk.log"]
)
LOG_LEVELS = {10: "debug", 20: "info", 30: "warning", 40: "error"}
kl = KennyLoggins()
iLog = kl.get_logger(
    app_name=__app_name__, file_name="s1-instantiation-logger", log_level=logger.INFO
)
force_log_creation = kl.get_logger(__app_name__, "mgmt_sdk", logger.INFO)
os.environ["SDK_LOG_LEVEL"] = LOG_LEVELS.get(force_log_creation.level, "warning")
force_log_creation.info(
    "action=forcing_line_due_to_windowsness_in_python_3 level={}".format(
        force_log_creation.level
    )
)
iLog.info(
    "action=global_check product={} path_len={}".format(getProductName(), len(sys.path))
)


# https://usea1-partners.sentinelone.net/api-doc/api-details?category=activities&api=get-activities


class S1ModularInput(ModularInput):
    def __init__(self, **kwargs):
        ModularInput.__init__(self, **kwargs)
        self.utils = None
        self.proxy_string = None
        self.s1_mgmt = None
        self.flatten_sep = "."
        self.enabled_features = {}
        self.tracking_uuid = kwargs["tracking_uuid"] if "tracking_uuid" in kwargs else str(uuid.uuid4())
        self.log_attrs = ["tracking_uuid"]
        self.inform(
            action="instantiation", cmd=kwargs.get("name", "sentinelone-generic-input"), logger_name=self.log.name
        )

    def set_uuid(self, str_uuid):
        self.tracking_uuid = str_uuid

    def _add_logging_additional(self):
        ret = {}
        for r in self.log_attrs:
            ret[r] = getattr(self, r)
        ret["input_name"] = self.get_config("input_name", "NOT FOUND")
        ret["input_guid"] = self.get_config("guid", "NOT FOUND")
        ret["channel"] = self.get_config("channel", "NOT FOUND")
        return ret

    def _build_message(self, **args):
        try:
            ret_msg = []
            add = self._add_logging_additional()
            for k in args:
                ret_msg.append(f'{k}="{args[k]}"')
            for k in add:
                ret_msg.append(f'{k}="{add[k]}"')
            return " ".join(ret_msg)
        except Exception as e:
            self.error(exception=f"{e}")

    def inform(self, **kwargs):
        caller = getframeinfo(stack()[1][0])
        self.log.info(
            self._build_message(
                calling_line_number=caller.lineno,
                calling_function=caller.function,
                calling_file_name=os.path.basename(caller.filename),
                **kwargs,
            )
        )

    def fatal(self, **kwargs):
        caller = getframeinfo(stack()[1][0])
        self.log.fatal(
            self._build_message(
                calling_line_number=caller.lineno,
                calling_function=caller.function,
                calling_file_name=os.path.basename(caller.filename),
                **kwargs,
            )
        )

    def warn(self, **kwargs):
        caller = getframeinfo(stack()[1][0])
        self.log.warning(
            self._build_message(
                calling_line_number=caller.lineno,
                calling_function=caller.function,
                calling_file_name=os.path.basename(caller.filename),
                **kwargs,
            )
        )

    def dbg(self, **kwargs):
        caller = getframeinfo(stack()[1][0])
        self.log.debug(
            self._build_message(
                calling_line_number=caller.lineno,
                calling_function=caller.function,
                calling_file_name=os.path.basename(caller.filename),
                **kwargs,
            )
        )

    def error(self, **kwargs):
        caller = getframeinfo(stack()[1][0])
        self.log.error(
            self._build_message(
                calling_line_number=caller.lineno,
                calling_function=caller.function,
                calling_file_name=os.path.basename(caller.filename),
                **kwargs,
            )
        )

    def setup(self, apl=False):
        try:
            self.utils = S1Utilities(
                app_name=self._app_name, session_key=self.get_config("session_key")
            )
            self._config["api_token"] = self.utils.get_credential(
                self._app_name, self.get_config("api_config")
            )
            self._config["api_config"] = self.utils.get_api_config(
                self.get_config("api_config")
            )
            self.log.debug(
                "action=checking_for_proxy guid={}".format(
                    self.get_config("proxy_guid")
                )
            )
            self.log.warning("action=logger_name name={}".format(self.log.name))
            ps = None
            verify_ssl = True
            self.log.debug("proxy_guid: {}".format(self.get_config("proxy_guid")))
            if (
                self.get_config("proxy_guid")
                and self.get_config("proxy_guid") != "NOPROXYSELECTED"
            ):
                self.log.info(
                    "action=proxy_found guid={}".format(self.get_config("proxy_guid"))
                )
                proxy = self.utils.get_proxy(self.get_config("proxy_guid"))
                self.log.debug("proxy: {}".format(proxy))
                proto = "http"
                self.log.debug(
                    "action=checking_ssl use_ssl={}".format(proxy.get("use_ssl"))
                )
                if (
                    proxy.get("use_ssl") == "true"
                    or "{}".format(proxy.get("use_ssl")) == "1"
                ):
                    proto = "https"
                proxy_string = "{}://{}".format(proto, proxy["proxy_url"])
                if "proxy_user" in proxy:
                    proxy_string = "{}://{}:{}@{}".format(
                        proto,
                        proxy["proxy_user"],
                        proxy["proxy_pass"],
                        proxy["proxy_url"],
                    )
                if (
                    proxy.get("use_ssl") == "false"
                    or "{}".format(proxy.get("use_ssl")) == "0"
                ):
                    verify_ssl = False
                self.log.debug(
                    "action=proxy_string verify_ssl={} {}".format(
                        verify_ssl, proxy["proxy_url"]
                    )
                )
                ps = {"http": proxy_string, "https": proxy_string}
            self.proxy_string = ps
            self.log.debug("proxy_string (ps): {}".format(ps))
            vs = self.get_config("api_config")["ssl_verify"]
            vss = True
            if vs == "0" or vs == "true" or vs == "t" or vs == "off":
                vss = False
            self.log.debug("ssl_verify: {}, vss: {}".format(vs, vss))

            # TODO: Add "source" channel or input or action to Useragent
            client_settings = {
                "verify": vss,
                "verbose": True,
                "user_agent": f"{self.utils.create_user_agent()}",
            }
            if self.proxy_string is not None:
                client_settings["proxies"] = self.proxy_string
            self.log.debug(
                "action=set_client_settings client_settings={}".format(client_settings)
            )
            self.host(self.get_config("api_config")["url"])
            if apl:
                self.log.debug(f"action=set_management_sdk sdk={AplManagement}")
                self.s1_mgmt = AplManagement(
                    self.get_config("api_config")["url"],
                    api_token=self.get_config("api_token"),
                    client_settings=client_settings,
                )
            else:
                self.log.debug(f"action=set_management_sdk sdk={S1Management}")
                self.s1_mgmt = S1Management(
                    self.get_config("api_config")["url"],
                    api_token=self.get_config("api_token"),
                    client_settings=client_settings,
                )
            if self.s1_mgmt is None:
                self.log.fatal(
                    "action=client_instantiation status=failure msg='Client failed to instantiate'"
                )
                exit(2)
            else:
                self.log.info(
                    "action=client_instantiation status=success url={}".format(
                        self.get_config("api_config")["url"]
                    )
                )
            resp = self.s1_mgmt.system.enabled_features().json
            enabled_features = " "
            for k in list(resp["data"].keys()):
                nv = normalizeBoolean(resp["data"][k])
                enabled_features += f'{k}="{nv}" '
                self.enabled_features[k] = nv
            apl_mgmt_features = ["starAlerts", "appManagement"]
            acceptable_features = [
                self.enabled_features.get(x, False) for x in apl_mgmt_features
            ]
            self.log.debug(
                f"action=check_features apl_mgmt={apl_mgmt_features} "
                f"results={acceptable_features} "
                f"{enabled_features}"
            )
            if any(acceptable_features):
                self.log.debug(f"action=set_management_sdk sdk={AplManagement}")
                self.s1_mgmt = AplManagement(
                    self.get_config("api_config")["url"],
                    api_token=self.get_config("api_token"),
                    client_settings=client_settings,
                )
            self.log.debug(
                "action=s1_mgmt_type s1_mgmt={} type={}".format(
                    self.s1_mgmt, type(self.s1_mgmt)
                )
            )
            self.warn(action="completed_setup")
        except Exception as e:
            self._catch_error(e)

    def _catch_error(self, e, **kwargs):
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        error_msg = (
            " "
            'error_message="{}" '
            'error_type="{}" '
            'error_arguments="{}" '
            'error_filename="{}" '
            'error_line_number="{}" '
            'input_guid="{}" '
            'input_name="{}" '.format(
                str(e),
                type(e),
                "{}".format(e),
                fname,
                exc_tb.tb_lineno,
                self.get_config("guid"),
                self.get_config("input_name"),
            )
        )
        oldst = self.sourcetype()
        self.sourcetype(f"{self._app_name}:error")
        self.print_error("{}".format(error_msg))
        self.print_event("{}".format(error_msg))
        self.sourcetype(oldst)

    api_limits = {"groups": 200, "threats": 1000, "uam_alerts": 1000}
    snapshot_bulk_limit_channels = {"applications", "agents", "groups"}
    default_bulk_import_limit = 1000000

    def _get_effective_bulk_import_limit(self, channel=None):
        if channel is None:
            channel = "{}".format(self.get_config("channel", "")).lower()
        configured_bulk_import_limit = self.get_config(
            "bulk_import_limit", self.default_bulk_import_limit
        )
        try:
            configured_bulk_import_limit = int(configured_bulk_import_limit)
        except Exception:
            self.log.warning(
                "action=invalid_bulk_import_limit channel={} value={} fallback={}".format(
                    channel,
                    configured_bulk_import_limit,
                    self.default_bulk_import_limit,
                )
            )
            configured_bulk_import_limit = self.default_bulk_import_limit
        if configured_bulk_import_limit < 1:
            self.log.warning(
                "action=invalid_bulk_import_limit channel={} value={} fallback={}".format(
                    channel,
                    configured_bulk_import_limit,
                    self.default_bulk_import_limit,
                )
            )
            configured_bulk_import_limit = self.default_bulk_import_limit
        if channel not in self.snapshot_bulk_limit_channels:
            if configured_bulk_import_limit != self.default_bulk_import_limit:
                self.log.info(
                    "action=ignoring_bulk_import_limit channel={} configured_bulk_import_limit={} effective_bulk_import_limit={}".format(
                        channel,
                        configured_bulk_import_limit,
                        self.default_bulk_import_limit,
                    )
                )
            return self.default_bulk_import_limit
        if configured_bulk_import_limit < self.default_bulk_import_limit:
            self.log.warning(
                "action=bulk_import_limit_below_min channel={} configured_bulk_import_limit={} minimum={}".format(
                    channel,
                    configured_bulk_import_limit,
                    self.default_bulk_import_limit,
                )
            )
            return self.default_bulk_import_limit
        return configured_bulk_import_limit

    def _paginate(
        self,
        func,
        next_page=None,
        time_field="timestamp",
        max_threads=10,
        call_sleep=None,
        skipCount=True,
        **fil,
    ):
        try:
            channel = self.get_config("channel")
            # try:
            #     resp = self.s1_mgmt.star_alerts.get(
            #         sourceProcessStoryline__contains="1627532589216254644",
            #         logger=self.log,
            #     )
            #     self.log.debug(
            #         f"action=calling_complete threat_id=1627532589216254644 resp={resp.json}"
            #     )
            # except Exception as e:
            #     self.log.debug(
            #         f"action=calling_complete threat_id=1627532589216254644 e={e}"
            #     )
            self.log.debug(
                "action=starting_paginate func={} next_page={} time_field={} max_threads={} channel={} call_sleep={} {}".format(
                    func,
                    next_page,
                    time_field,
                    max_threads,
                    channel,
                    call_sleep,
                    " ".join([f'{k}="{fil[k]}"' for k in fil]),
                )
            )
            total_items = 0
            if next_page is not None and next_page != "None":
                fil["cursor"] = next_page
            fil["skipCount"] = skipCount
            fil["limit"] = fil.get("limit", 1000)
            if fil["limit"] > 1000:
                fil["limit"] = 1000
            if channel in self.api_limits.keys():
                fil["limit"] = self.api_limits[channel]
            self.log.debug(
                "action=set_limit limit={} channel={} api_limits={}".format(
                    fil["limit"], channel, self.api_limits
                )
            )
            self.log.warning(f"action=forced_warning next='resp=func' filters={fil}")
            resp = func(**fil)
            results = resp.json
            self.log.debug(
                "action=paginate channel={} status_code={}".format(
                    channel, resp.status_code
                )
            )
            next_cursor = None
            bulk_import_limit = self._get_effective_bulk_import_limit(channel)
            while total_items < bulk_import_limit:
                self.log.info(
                    "action=paginate channel={} total_items={} "
                    "bulk_import_limit={} api_total_items={} continue_while={}".format(
                        channel,
                        total_items,
                        bulk_import_limit,
                        results["pagination"].get("total_items", 0),
                        total_items < bulk_import_limit,
                    )
                )
                try:
                    next_cursor = results["pagination"].get("nextCursor", None)
                except Exception as e:
                    self.log.debug(f'action=exception_bypass exception="{e}"')
                self.log.debug(
                    "action=paginate cursor={} channel={} fil={} pagination={}".format(
                        next_cursor, channel, fil, results["pagination"]
                    )
                )
                if len(results["data"]) > 0:
                    if channel == "uam_alerts" and len(results["data"]) > 1000:
                        chunk_size = 1000
                        total_records = len(results["data"])
                        for chunk_start in range(0, total_records, chunk_size):
                            chunk_end = min(chunk_start + chunk_size, total_records)
                            chunk_data = results["data"][chunk_start:chunk_end]
                            p = mp.Pool(max_threads)
                            matrix = [
                                (num, result, time_field)
                                for num, result in enumerate(chunk_data)
                            ]
                            p.starmap(self._process_data_threaded, matrix)
                            p.close()
                            p.join()
                            self.log.info(
                                "action=paginate channel={} chunk_processed={}-{} total_records={} chunk_size={}".format(
                                    channel, chunk_start, chunk_end, total_records, len(chunk_data)
                                )
                            )
                    else:
                        p = mp.Pool(max_threads)
                        matrix = [
                            (num, result, time_field)
                            for num, result in enumerate(results["data"])
                        ]
                        p.starmap(self._process_data_threaded, matrix)
                        p.close()
                        p.join()
                else:
                    self.log.debug(
                        "action=no_data channel={} matrix_length=0".format(channel)
                    )
                total_items += len(results["data"])
                self.log.debug(
                    "action=paginate total_items={} channel={} next_cursor={}".format(
                        total_items, channel, next_cursor
                    )
                )
                if next_cursor is None:
                    break
                fil["cursor"] = next_cursor
                self.log.debug("action=paginate fil={}".format(fil))
                self.log.warning(f"action=forced_warning next='resp=func' filters={fil}")
                if call_sleep:
                    self.log.warning(
                        f"action=forced_wait_between_calls channel={channel} call_sleep={call_sleep}"
                    )
                    time.sleep(call_sleep)
                resp = func(**fil)
                results = resp.json
                self.log.debug(
                    "action=paginate channel={} status_code={}".format(
                        channel, resp.status_code
                    )
                )
            return total_items, next_cursor
        except Exception as e:
            self._catch_error(e)
            # Avoid the error: cannot unpack non-iterable NoneType object.
            # DESK-1292
            return 0, None

    def _process_data_threaded(self, num, x, time_field="timestamp"):
        self.warn(action="not_implemented")

    def _get_lockfile(self):
        guid = self.get_config("guid")
        return os.path.join(self._config["checkpoint_dir"], f"{guid}.lock")

    def _set_lock(self, run_id=""):
        lockfile = self._get_lockfile()
        self.inform(action="setting_lockfile", lockfile=lockfile)
        if os.path.exists(lockfile):
            with open(lockfile, "r") as lf:
                ls = lf.read()
            self.warn(action="lockfile_exists", lockfile=lockfile, contents=ls)
            return False
        else:
            meme = f"{str(time.time())};;{run_id}"
            self.inform(action="no_lockfile", lockfile=lockfile, contents=meme)
            with open(lockfile, "w") as lf:
                lf.write(meme)
            return True

    def _remove_lock(self):
        lockfile = self._get_lockfile()
        self.inform(action="removing_lockfile", lockfile=lockfile)
        if os.path.exists(lockfile):
            try:
                os.remove(lockfile)
            except Exception as e:
                self.warn(action="failed_to_remove_lockfile", lockfile=lockfile, exception=e)
            self.inform(action="removed_lockfile", lockfile=lockfile)
            return True
        else:
            self.inform(action="lockfile_not_found", lockfile=lockfile)
            return False

    def _set_checkpoint(self, chkpnt_name=None, next_page=None, checkpoint_time=None):
        try:
            # So to avoid "long runs" and "time lapse" in checkpointing,
            # if no time is passed, use the time the checkpoint was loaded.
            # if "now" is passed, use "now". Can I haz tautology?
            # First identified in ASA-3
            # THIS MIGHT FAIL ON SHC VICTORIA DUE TO USE OF HOST
            # TRY TO LOAD THE NEW, if that fails, load the old. Then, only write out the new.
            chkpointfile = os.path.join(
                self._config["checkpoint_dir"], "{}_{}".format(self.host(), chkpnt_name)
            )
            chk_time = checkpoint_time
            if chk_time is None:
                chk_time = self._loaded_checkpoints[chkpnt_name]
            if chk_time == "now":
                chk_time = (
                    datetime.utcnow() - datetime.utcfromtimestamp(0)
                ).total_seconds()
            self._write_file(
                chkpointfile,
                json.dumps(
                    {"next_page": "", "last_execution": "{}".format(checkpoint_time)}
                ),
            )
            return True
        except Exception as e:
            self._catch_error(e)
            return False

    def _validate_arguments(self, val_data):
        """
        :param val_data: The data that requires validation.
        :return:
        RAISE an error if the arguments do not validate correctly. The default is just "True".
        """
        return True
