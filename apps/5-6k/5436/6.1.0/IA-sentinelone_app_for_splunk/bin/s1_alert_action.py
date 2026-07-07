"""
Written by Kyle Smith for Aplura, LLC
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
import uuid

from AlertAction import CreateAlertModularAction
from s1_utilities import S1Utilities
from Utilities import KennyLoggins
from s1_app_properties import __app_name__, __version__ as version
import json
import logging as logger
import sys
import os
import s1_paths
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path, getProductName
# These imports require _paths import
from management.mgmtsdk_v2_1.mgmt import Management

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


class S1AlertAction(CreateAlertModularAction):
    def __init__(self, settings=None, action_name=None, management=Management):
        try:
            CreateAlertModularAction.__init__(
                self,
                settings,
                action_name=action_name,
                app_name=__app_name__,
                global_configuration={
                    "filename": "alert_actions",
                    "stanza": action_name,
                },
            )
            self.s1_log = None
            self.proxy_string = None
            self.s1_mgmts = {}
            self.s1_mgmt_client = {}
            self.tracking_uuid = str(uuid.uuid4())
            self.__app_name__ = __app_name__
            self._action_name = action_name
            self._settings = json.loads(settings)
            self.management = management
            self.session_key = self._settings.get("session_key", None)
            self.utils = S1Utilities(
                app_name=self.__app_name__, session_key=self.session_key
            )
            self.server_info = self.utils.get_splunk_info()
            self._configuration = self._settings.get("configuration", {})
            self._log.debug("configuration={}".format(self._settings))
            self.payload = {
                "results_file": self._settings.get("results_file", None),
                "search_name": self._settings.get("search_name", "undefined"),
            }
            self.log_attrs = ["tracking_uuid"]
            self._log.warning("action=logger_name name={}".format(self._log.name))

        except Exception as e:
            self._catch_error(e, action_name=action_name)

    def _add_logging_additional(self):
        ret = {}
        for r in self.log_attrs:
            ret[r] = getattr(self, r)
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
            self._log.error(f"Exception: {e}")

    def inform(self, **kwargs):
        self._log.info(self._build_message(**kwargs))

    def warn(self, **kwargs):
        self._log.warning(self._build_message(**kwargs))

    def debug(self, **kwargs):
        self._log.debug(self._build_message(**kwargs))

    def error(self, **kwargs):
        self._log.error(self._build_message(**kwargs))

    def get_config(self, item, ret=None):
        return self._configuration.get(item, ret)

    def clients_by_url(self):
        return {
            self.s1_mgmts[x]["url"]: self.s1_mgmts[x]["mgmt"] for x in self.s1_mgmts
        }

    def setup_management(self, guid):
        credential = self.utils.get_credential(self.__app_name__, guid)
        auth_host = self.utils.get_api_config(guid)
        vs = auth_host["ssl_verify"]
        vss = True
        if vs == "0" or vs == "true" or vs == "t":
            vss = False
        client_settings = {"verify": vss, "verbose": True}
        if self.proxy_string is not None:
            client_settings["proxies"] = self.proxy_string
        client_settings["user_agent"] = self.utils.create_user_agent()
        try:
            tmp_mgmt = self.management(
                auth_host["url"], api_token=credential, client_settings=client_settings
            )
        except Exception as e:
            self._log.debug(f'action=exception_bypass exception="{e}')
            tmp_mgmt = None
        return {"mgmt": tmp_mgmt, "url": auth_host["url"]}

    def setup_s1_client(self):
        try:
            self._log.debug(
                "action=checking_for_proxy guid={}".format(
                    self.get_config("proxy_guid")
                )
            )
            ps = None
            verify_ssl = True
            pg = self.get_config("proxy_guid")
            if pg and pg != "NOPROXYSELECTED" and pg != "undefined":
                self._log.info(
                    "action=proxy_found guid={} type={}".format(pg, type(pg))
                )
                proxy = self.utils.get_proxy(self.get_config("proxy_guid"))
                proto = "http"
                self._log.debug(
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
                self._log.debug(
                    "action=proxy_string verify_ssl={} {}".format(
                        verify_ssl, proxy["proxy_url"]
                    )
                )
                ps = {proto: proxy_string}
            self.proxy_string = ps
            self.s1_mgmts = {
                x: self.setup_management(x)
                for x in self.get_config("auth_hosts", "").split(",")
            }
            for z in list(self.s1_mgmts):
                if self.s1_mgmts[z]["mgmt"] is None:
                    self._log.warning(
                        "action=client_instantiation status=failure "
                        "msg='Client failed to instantiate for host={} url={}".format(
                            z, self.s1_mgmts[z]["url"]
                        )
                    )
                    del self.s1_mgmts[z]
                else:
                    self._log.info(
                        "action=client_instantiation status=success msg='Client instantiated for host={}".format(
                            z
                        )
                    )

        except Exception as e:
            self._catch_error(e, action_name=self._action_name)

    def setup_proxy(self, proxy_guid):
        try:
            self._log.debug("action=checking_for_proxy guid={}".format(proxy_guid))
            verify_ssl = True
            proxy_string = None
            if proxy_guid and proxy_guid != "NOPROXYSELECTED":
                self._log.info("action=proxy_found guid={}".format(proxy_guid))
                proxy = self.utils.get_proxy(proxy_guid)
                proto = "http"
                self._log.debug(
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
                self._log.debug(
                    "action=proxy_string verify_ssl={} {}".format(
                        verify_ssl, proxy["proxy_url"]
                    )
                )
            return proxy_string, verify_ssl
        except Exception as e:
            self._catch_error(e)
            raise e

    def _catch_error(self, e, action_name="undefined_alert"):
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        error_msg = (
            " "
            'error_message="{}" '
            'error_type="{}" '
            'error_arguments="{}" '
            'error_filename="{}" '
            'error_line_number="{}" '
            'action_name="{}" '.format(
                str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno, action_name
            )
        )
        iLog.error(error_msg)
        return error_msg
