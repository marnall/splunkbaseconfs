"""
Written by Aplura, LLC
Copyright (C) 2022 Aplura, ,LLC

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

This is a generic Critical Start Client class. This allows for multiple alert actions to use the same authentication schemes and faster bug updates as needed.
"""

import json
import logging as logger
import os
import sys
import warnings
from contextlib import contextmanager

import requests
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

from AlertAction import CreateAlertModularAction
from Utilities import KennyLoggins, Utilities

# Sets up path to the lib if needed, and updates the loggers to output correctly.
_APP_NAME = "ztap_app"
sys.path.insert(0, make_splunkhome_path(["etc", "apps", _APP_NAME, "lib"]))
LOG_LEVELS = {10: "debug", 20: "info", 30: "warning", 40: "error"}

kl = KennyLoggins()
iLog = kl.get_logger(
    app_name=_APP_NAME,
    file_name="criticalstart-instantiation-logger",
    log_level=logger.INFO,
)


# CS Specific Utilities, based on an SDK Utilities Class
class CSUtilities(Utilities):
    def __init__(self, **kwargs):
        Utilities.__init__(self, **kwargs)

    def get_ztap_host(self, tenant_guid):
        #
        # Get ztap host configuration from ztap_hosts.conf based on guid associated with token in alert action
        #
        uri = self._build_endpoint_uri(["configs", "conf-ztap_hosts", tenant_guid])
        self._log.debug("action=build_endpoint_uri uri={}".format(uri))
        server_response, server_content = self._make_get_request(
            uri, args={"output_mode": "json"}
        )
        return json.loads(server_content)["entry"][0]["content"]

    def get_ztap_search_job(self, sid):
        #
        # Retrieve job information from Splunk search based on sid associated with Splunk search job
        #
        uri = self._build_endpoint_uri(["search", "jobs", "{}".format(sid)])
        self._log.debug("action=build_endpoint_uri uri={}".format(uri))
        server_response, server_content = self._make_get_request(
            uri, args={"output_mode": "json"}
        )
        return json.loads(server_content)["entry"][0]["content"]

    def get_proxy(self, proxy_guid):
        #
        # Get proxy configuration from proxy.conf based on proxy guid associated with proxy configured in app configuration
        #
        uri = self._build_endpoint_uri(["configs", "conf-proxy", proxy_guid])
        self._log.debug("action=build_endpoint_uri uri={}".format(uri))
        server_response, server_content = self._make_get_request(
            uri, args={"output_mode": "json"}
        )
        proxy = json.loads(server_content)["entry"][0]["content"]
        self._log.debug(
            "action=checking_proxy_user user={}".format("proxy_user" in proxy)
        )
        if "proxy_user" in proxy:
            proxy["proxy_pass"] = self.get_credential(
                self._app_name, "pr-{}".format(proxy_guid)
            )
        return proxy


# Creates a standard Alert Action for CS. This can be inherited elsewhere for faster dev / more responsive / reusable code
class CSAlertAction(CreateAlertModularAction):
    def __init__(self, settings=None, action_name=None, filename=None, stanza=None):
        try:
            CreateAlertModularAction.__init__(
                self,
                settings,
                action_name=action_name,
                app_name=_APP_NAME,
                global_configuration={
                    "filename": "alert_actions",
                    "stanza": action_name,
                },
            )
            self.cs_log = None
            self.multi_tenant_apis = {}
            self._app_name = _APP_NAME
            self._action_name = action_name
            self._settings = json.loads(settings)
            self.session_key = self._settings.get("session_key", None)
            self.ztap_token = None
            self.utils = CSUtilities(
                app_name=self._app_name, session_key=self.session_key
            )
            self._configuration = self._settings.get("configuration", {})
            self._log.debug(
                'action={} message="{}"'.format(
                    "received_init_configuration", self._configuration
                )
            )
            self.sid = self._settings.get("sid", "")
            self._log.debug('action={} message="{}"'.format("set_search_sid", self.sid))
            self.session_key = self._settings.get("session_key", "")
            self.search_name = self._settings.get("search_name", "")
            self.server_host = self._settings.get("server_host", "")
            self.server_uri = self._settings.get("server_uri", "")
            self.owner = self._settings.get("owner", "")
            self.search_app = self._settings.get("app", "")
            self.results_file = self._settings.get("results_file", "")
            self.results_link = self._settings.get("results_link", "")
            self.search_uri = self._settings.get("search_uri", "")
            self._log.debug(
                'action={} message="{}" guid={}'.format(
                    "get_ztap_authentication_configuration",
                    "Get the ZTAP Authentication settings via guid reference in configuration files.",
                    self._configuration.get("ztap_host_guid"),
                )
            )
            self.ztap_host = self.utils.get_ztap_host(
                self._configuration.get("ztap_host_guid")
            )
            self._log.debug(
                "action=setup_default_ztap_host ztap_host={}".format(self.ztap_host)
            )
            # sid is usually expected, unless the is a Test Event
            sid = self._settings.get("sid")
            if sid:
                self.ztap_search_job = self.utils.get_ztap_search_job(sid)
                self._log.debug(
                    "action=get_search_job_information, job={}".format(
                        self.ztap_search_job
                    )
                )
            self.ztap_token = self.utils.get_credential(
                self._app_name, self.ztap_host["guid"]
            )
            self.proxy = self.setup_proxy(self._configuration.get("proxy_guid", None))
            self.payload = {
                "results_file": self._settings.get("results_file", None),
                "search_name": self._settings.get("search_name", "undefined"),
            }

            #
            # Build url that will be used as ztap appliance url
            #
            self.url = "https://{}".format(self.ztap_host["ztap_env"])
            self.org_key = "{}".format(self.ztap_host["org_key"])
            self.token = "{}".format(self.ztap_token)
            self._log.warning("action=logger_name name={}".format(self._log.name))

        except Exception as e:
            self._catch_error(e, action_name=action_name)

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

    def setup_proxy(self, proxy_guid):
        try:
            self._log.debug("action=checking_for_proxy guid={}".format(proxy_guid))
            ps = None
            if (
                proxy_guid
                and proxy_guid != "NOPROXYSELECTED"
                and proxy_guid != "undefined"
            ):
                self._log.info("action=proxy_found guid={}".format(proxy_guid))
                proxy = self.utils.get_proxy(proxy_guid)
                ps = Utilities.build_proxy_string(proxy)
            self._log.debug("action=set_proxy_string string='{}'".format(ps))
            proxy_string = ps
            return proxy_string
        except Exception as e:
            self._catch_error(e)
            raise e

    def get_config(self, item, ret=None):
        return self._configuration.get(item, ret)
