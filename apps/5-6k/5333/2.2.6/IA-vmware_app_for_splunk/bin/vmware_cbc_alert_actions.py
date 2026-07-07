# VMWARE CBC Alert Actions Base Class
import sys
import json
import logging as logger
import version
import os
import time
import uuid
from VMWAlertAction import CreateAlertModularAction
from VMWUtilities import KennyLoggins
from vmware_cbc_utilities import CBCUtilities
import vmware_paths
from cbc_sdk import CBCloudAPI

__app_name__ = vmware_paths.__app_name__
kl = KennyLoggins()
iLog = kl.get_logger(app_name=__app_name__, file_name="vmware-instantiation-logger", log_level=logger.INFO)


class VmwareCBCAlertAction(CreateAlertModularAction):
    def __init__(self, settings=None, action_name=None, filename=None, stanza=None):
        try:
            CreateAlertModularAction.__init__(self, settings, action_name=action_name,
                                              app_name=__app_name__,
                                              global_configuration={"filename": "alert_actions",
                                                                    "stanza": action_name})
            self.cb = None
            self.cb_log = None
            self.multi_tenant_apis = {}
            self._app_name = __app_name__
            self._action_name = action_name
            self._settings = json.loads(settings)
            self.session_key = self._settings.get("session_key", None)
            self._configuration = self._settings.get("configuration", {})
            self._log.debug("_settings={}".format(self._settings))
            self.utils = CBCUtilities(
                app_name=self._app_name, session_key=self.session_key)
            self._tenants = None
            if "," in self._configuration.get("tenant", ""):
                self._tenants = self._configuration.get("tenant").split(",")
                self._use_multi_tenant = True
            else:
                self._tenants = [self._configuration.get("tenant")]
                self._use_multi_tenant = False
            # Set the default tenant to the first one.
            self.tenant = self.utils.get_tenant(self._tenants[0])
            self._log.debug(
                "action=setup_default_tenant tenant={}".format(self.tenant))
            self.verify_ssl = self._configuration.get("verify_ssl", True)
            if self.utils.is_cloud():
                self.verify_ssl = True
            self._log.debug(
                "action=checking_ssl_verify verify={}".format(self.verify_ssl))
            self.api_key_secret = self.utils.get_credential(self._app_name,
                                                            self.tenant["guid"])
            self.proxy, self.verify_proxy_ssl = self.setup_proxy(
                self._configuration.get("proxy_guid", None))
            self.payload = {
                "results_file": self._settings.get("results_file", None),
                "search_name": self._settings.get("search_name", "undefined")
            }
            # This data *should* show up in $SPLUNK_HOME/var/log/splunk/vmware_app_for_splunk/cbc_sdk.log
            massive_debug = self._configuration.get("debug_cbc_sdk", None)
            self._log.info(
                "action=checking_dark_feature debug_cbc_sdk={}".format(massive_debug))
            if "{}".format(massive_debug) == "enable":
                self._log.warn(
                    "ENABLING MASSIVE DEBUG DARK FEATURE debug={}".format(massive_debug))
                self.cb_log = kl.get_logger(
                    self._app_name, "cbc_sdk", logger.DEBUG)
                self.cb_log.warn("action=instantiate_cbc_sdk_debugger")
            self._log.info("action=setting_up_client")
            integration_name = "SplunkApp/{}/{} AlertAction/{}".format(self._app_name,
                                                                       version.__version__,
                                                                       action_name)
            url = "https://{}".format(self.tenant["cbc_env"])
            org_key = "{}".format(self.tenant["org_key"])
            token = '{0}/{1}'.format(self.api_key_secret,
                                     self.tenant["api_key"])
            self._log.debug("tenant: {}".format(self.tenant))
            self.cb = CBCloudAPI(integration_name=integration_name,
                                 url=url,
                                 org_key=org_key,
                                 token=token,
                                 proxy=self.proxy,
                                 ssl_verify=self.verify_ssl)

            if self._use_multi_tenant:
                self.setup_multi_tenant_apis()

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error_msg = " " \
                        "error_message=\"{}\" " \
                        "error_type=\"{}\" " \
                        "error_arguments=\"{}\" " \
                        "error_filename=\"{}\" " \
                        "error_line_number=\"{}\" " \
                .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno)
            self._log.error(error_msg)
            self._catch_error(e, action_name=action_name)

    def setup_multi_tenant_apis(self):
        try:
            self._log.info("action=setting_up_multi_tenant_apis")
            integration_name = "SplunkApp/{}/{} AlertAction/{}".format(self._app_name,
                                                                       version.__version__,
                                                                       self._action_name)
            for ti in self._tenants:
                self._log.debug(
                    "action=setting_up_multi_tenant_api guid={}".format(ti))
                tenant = self.utils.get_tenant(ti)
                self._log.debug(
                    "action=setting_up_tenant tenant={}".format(tenant))
                url = "https://{}".format(tenant["cbc_env"])
                org_key = "{}".format(tenant["org_key"])
                if org_key not in self.multi_tenant_apis:
                    self.multi_tenant_apis[org_key] = {}
                self._log.debug(
                    "action=setting_up_tenant org_key={}".format(org_key))
                api_key_secret = self.utils.get_credential(self._app_name,
                                                           tenant["guid"])
                token = '{0}/{1}'.format(api_key_secret, tenant["api_key"])
                self._log.debug("tenant: {}".format(tenant["guid"]))
                self.multi_tenant_apis[org_key]["cb"] = CBCloudAPI(integration_name=integration_name,
                                                                   url=url,
                                                                   org_key=org_key,
                                                                   token=token,
                                                                   proxy=self.proxy,
                                                                   ssl_verify=self.verify_ssl)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error_msg = " " \
                        "error_message=\"{}\" " \
                        "error_type=\"{}\" " \
                        "error_arguments=\"{}\" " \
                        "error_filename=\"{}\" " \
                        "error_line_number=\"{}\" " \
                .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno)
            self._log.error(error_msg)

    def _catch_error(self, e, action_name="undefined_alert"):
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        error_msg = " " \
                    "error_message=\"{}\" " \
                    "error_type=\"{}\" " \
                    "error_arguments=\"{}\" " \
                    "error_filename=\"{}\" " \
                    "error_line_number=\"{}\" " \
                    "action_name=\"{}\" " \
            .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno, action_name)
        iLog.error(error_msg)

    def setup_proxy(self, proxy_guid):
        try:
            self._log.debug(
                "action=checking_for_proxy guid={}".format(proxy_guid))
            verify_ssl = True
            proxy_string = None
            if proxy_guid and proxy_guid != "NOPROXYSELECTED":
                self._log.info("action=proxy_found guid={}".format(proxy_guid))
                proxy = self.utils.get_proxy(proxy_guid)
                proto = "http"
                self._log.debug(
                    "action=checking_ssl use_ssl={}".format(proxy.get("use_ssl")))
                if proxy.get("use_ssl") == "true" or str(proxy.get("use_ssl")) == "1":
                    proto = "https"
                proxy_string = "{}://{}".format(proto, proxy["proxy_url"])
                if "proxy_user" in proxy:
                    proxy_string = "{}://{}:{}@{}".format(proto,
                                                          proxy["proxy_user"],
                                                          proxy["proxy_pass"],
                                                          proxy["proxy_url"])
                if proxy.get("use_ssl") == "false" or str(proxy.get("use_ssl")) == "0":
                    verify_ssl = False
                self._log.debug("action=proxy_string verify_ssl={} {}".format(verify_ssl,
                                                                              proxy["proxy_url"]))
            return proxy_string, verify_ssl
        except Exception as e:
            self._catch_error(e)
            raise e

    def _create_watchlist(self, local_cb_api, cls, watchlist_name):
        uu = uuid.uuid4()
        descr = "AutoGenerated from Splunk Search: '{}'"
        now_now = int(time.time())
        wobj = {
            "create_timestamp": now_now,
            "last_update_timestamp": now_now,
            "name": watchlist_name,
            "description": descr.format(self._settings.get("search_name", "unknown")),
            "id": "splunk-ar-{}".format(uu)}
        self._log.debug(
            "action=no_watchlist resolution=create_new wobj={}".format(wobj))
        local_cb_api \
            .create(cls, wobj) \
            .save()
