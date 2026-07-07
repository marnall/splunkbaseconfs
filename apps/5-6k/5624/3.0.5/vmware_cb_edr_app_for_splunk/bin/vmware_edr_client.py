import logging as logger
import sys
import os
import json
from Utilities import KennyLoggins, Utilities
from ModularInput import ModularInput
from AlertAction import CreateAlertModularAction
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import version

_APP_NAME = "vmware_cb_edr_app_for_splunk"
sys.path.insert(0, make_splunkhome_path(["etc", "apps", _APP_NAME, "lib"]))
kl = KennyLoggins()
iLog = kl.get_logger(app_name=_APP_NAME, file_name="vmware-instantiation-logger", log_level=logger.INFO)
force_log_creation = kl.get_logger(_APP_NAME, "cbapi", logger.INFO)
force_log_creation.info("action=forcing_logger")

from cbapi import CbEnterpriseResponseAPI


class CBEDRUtilities(Utilities):
    def __init__(self, **kwargs):
        Utilities.__init__(self, **kwargs)

    def get_api_config(self, api_config_guid):
        uri = self._build_endpoint_uri(['configs', 'conf-api_configs', api_config_guid])
        server_response, server_content = self._make_get_request(uri, args={"output_mode": "json"})
        return json.loads(server_content)["entry"][0]["content"]

    def get_proxy(self, proxy_guid):
        proxy_string = None
        verify_ssl = True
        proto = "http"
        if proxy_guid and proxy_guid != "NOPROXYSELECTED":
            self._log.info("action=proxy_found guid={}".format(proxy_guid))
            uri = self._build_endpoint_uri(['configs', 'conf-proxy', proxy_guid])
            server_response, server_content = self._make_get_request(uri, args={"output_mode": "json"})
            proxy = json.loads(server_content)["entry"][0]["content"]
            self._log.debug("action=checking_proxy_user user={}".format("proxy_user" in proxy))
            if "proxy_user" in proxy:
                proxy["proxy_pass"] = self.get_credential(self._app_name,
                                                          "pr-{}".format(proxy_guid))
            proto = "http"
            self._log.debug("action=checking_ssl use_ssl={}".format(proxy.get("use_ssl")))
            if proxy.get("use_ssl") is "true" or "{}".format(proxy.get("use_ssl")) is "1":
                proto = "https"
            proxy_string = "{}://{}".format(proto, proxy["proxy_url"])
            if "proxy_user" in proxy:
                proxy_string = "{}://{}:{}@{}".format(proto,
                                                      proxy["proxy_user"],
                                                      proxy["proxy_pass"],
                                                      proxy["proxy_url"])
            if proxy.get("use_ssl") is "false" or "{}".format(proxy.get("use_ssl")) is "0":
                verify_ssl = False
            self._log.debug("action=proxy_string verify_ssl={} {}".format(verify_ssl,
                                                                         proxy["proxy_url"]))
        return proxy_string, verify_ssl, proto

    def get_command(self, cmd_name):
        self._log.debug("action=getting_command_information name={}".format(cmd_name))
        uri = self._build_endpoint_uri(['configs', 'conf-commands', cmd_name])
        server_response, server_content = self._make_get_request(uri, args={"output_mode": "json"})
        return json.loads(server_content)["entry"][0]["content"]


class VmwareCBEDRModularInput(ModularInput):
    def __init__(self, **kwargs):
        ModularInput.__init__(self, **kwargs)
        self.utils = None
        self.cb = None
        self.cb_log = None
        self.tenant = None
        self.proxy_string = None
        self.verify_ssl = None
        self.credential = None

    def _catch_error(self, e):
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        error_msg = " " \
                    "error_message=\"{}\" " \
                    "error_type=\"{}\" " \
                    "error_arguments=\"{}\" " \
                    "error_filename=\"{}\" " \
                    "error_line_number=\"{}\" " \
                    "input_guid=\"{}\" " \
                    "input_name=\"{}\" " \
            .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno, self.get_config("guid"),
                    self.get_config("input_name"))
        oldst = self.sourcetype()
        self.sourcetype("vmware:cb:edr:error")
        self.print_error("{}".format(error_msg))
        self.print_event("{}".format(error_msg))
        self.sourcetype(oldst)

    def setup_cb(self):
        try:
            self.utils = CBEDRUtilities(app_name=self._app_name, session_key=self.get_config("session_key"))
            self._config["api_key_secret"] = self.utils.get_credential(self._app_name,
                                                                       self.get_config("credential_guid"))
            self._config["tenant"] = self.utils.get_tenant(self.get_config("credential_guid"))
            t = self.get_config("tenant")
            proxy_guid = t.get("proxy_guid", None)
            self.log.debug("action=checking_for_proxy guid={}".format(proxy_guid))
            self.proxy_string, self.verify_ssl = self.utils.get_proxy(t.get("proxy_guid"))
            self.log.info("action=setting_up_base_api")
            # self.cb = CBCloudAPI(integration_name="SplunkApp/{}/{} ModularInput/{}".format(self._app_name,
            #                                                                                version.__version__,
            #                                                                                self.get_config(
            #                                                                                    "name").split(":")[0]),
            #                      url="https://{}".format(t["cb_edr_env"]),
            #                      org_key="{}".format(t["org_key"]),
            #                      token='{0}/{1}'.format(self.get_config("api_key_secret"), t["api_key"]),
            #                      proxy=proxy_string,
            #                      ssl_verify=verify_ssl)
            self.host(t["cb_edr_env"])
            massive_debug = self.get_config("debug_cb_api")
            self.log.info("action=checking_dark_feature debug_cbapi={}".format(massive_debug))
            # This data *should* show up in $SPLUNK_HOME/var/log/splunk/vmware_cb_edr_app_for_splunk/cbapi.log
            if "{}".format(massive_debug) == "enable":
                self.log.warn("ENABLING MASSIVE DEBUG DARK FEATURE debug={}".format(massive_debug))
                self.cb_log = kl.get_logger(self._app_name, "cbapi", logger.DEBUG)
                self.cb_log.warn("action=instantiate_cbapi_debugger")
        except Exception as e:
            self._catch_error(e)
            raise e

    def _validate_arguments(self, val_data):
        """
        :param val_data: The data that requires validation.
        :return:
        RAISE an error if the arguments do not validate correctly. The default is just "True".
        """
        return True


class EDRCommand(object):

    def __init__(self, cmd_name, session_key):
        try:
            mykl = KennyLoggins()
            self._cmd_name = cmd_name
            self._log = mykl.get_logger(app_name=_APP_NAME, file_name=cmd_name, log_level=logger.INFO)
            self._log.info("action=instantiation_start cmd={}".format(cmd_name))
            self.utils = None
            self.session_key = session_key
            self._app_name = _APP_NAME
            self.utils = CBEDRUtilities(app_name=self._app_name, session_key=self.session_key)
            self.proxy_string = None
            self.edr_orgs = {}
            self._configuration = self.utils.get_command(cmd_name)
        except Exception as e:
            self._catch_error(e)

    def get_config(self, item, ret=None):
        return self._configuration.get(item, ret)

    def clients_by_org_key(self):
        return {self.edr_orgs[x]["org_name"]: self.edr_orgs[x]["cb"] for x in self.edr_orgs}

    def clients_as_array(self):
        return [self.edr_orgs[x] for x in self.edr_orgs]

    def setup_client(self, guid):
        try:
            credential = self.utils.get_credential(self._app_name, guid)
            auth_host = self.utils.get_api_config(guid)
            vs = auth_host.get("ssl_verify", "0")
            vss = True
            if vs == '0' or vs == 'false' or vs == 'f':
                vss = False
            client_settings = {"verify": vss, "verbose": True}
            ps = None
            pg = auth_host.get("proxy_guid", None)
            self._log.info("action=proxy guid={} vs={} verify_server_ssl={}".format(pg, vs, vss))
            if pg and pg != "NOPROXYSELECTED" and pg != "undefined":
                self._log.info("action=proxy_found guid={} type={}".format(pg, type(pg)))
                proxy = self.utils.get_proxy(pg)
                proxy_string, verify_ssl, proto = proxy
                ps = {proto: proxy_string}
            if ps is not None:
                client_settings["proxies"] = ps
            return {
                "cb": CbEnterpriseResponseAPI(integration_name="SplunkApp/{}/{} CustomCommand/{}".format(self._app_name,
                                                                                                         version.__version__,
                                                                                                         self._cmd_name),
                                              url="https://{}".format(auth_host["cb_edr_env"]),
                                              token='{}'.format(credential),
                                              proxy=client_settings.get("proxies", {}).get("http"),
                                              ssl_verify=vss),
                "org_name": auth_host["org_name"],
                "url": auth_host["cb_edr_env"]}
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error_msg = " " \
                        "error_message=\"{}\" " \
                        "error_type=\"{}\" " \
                        "error_arguments=\"{}\" " \
                        "error_filename=\"{}\" " \
                        "error_line_number=\"{}\" " \
                        "action_name=\"{}\" " \
                .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno, self._cmd_name)
            self._log.warn("action=setup_client status=failed exception={}".format(error_msg))
            return {"cb": None, "org_name": None, "url": None}


    def setup(self):
        try:
            self._log.debug("action=start_setup")
            apis = self.get_config("api_config", "")
            self.edr_orgs ={k:v for k, v in {x: self.setup_client(x) for x in apis.split(",")}.items() if not v["cb"] is None}
            self._log.info("action=setup edr_orgs={}".format(self.edr_orgs))
        except Exception as e:
            self._catch_error(e, self._cmd_name)
            raise e

    def _catch_error(self, e, cmd_name="undefined_command"):
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        error_msg = " " \
                    "error_message=\"{}\" " \
                    "error_type=\"{}\" " \
                    "error_arguments=\"{}\" " \
                    "error_filename=\"{}\" " \
                    "error_line_number=\"{}\" " \
                    "action_name=\"{}\" " \
            .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno, self._cmd_name)
        self._log.error(error_msg)


class EDRAlertAction(CreateAlertModularAction):
    def __init__(self, settings=None, action_name=None, filename=None, stanza=None):
        try:
            CreateAlertModularAction.__init__(self, settings, action_name=action_name,
                                              app_name=_APP_NAME,
                                              global_configuration={"filename": "alert_actions",
                                                                    "stanza": action_name})
            self.edr_orgs = {}
            # self._log = mykl.get_logger(app_name=_APP_NAME, file_name=action_name, log_level=logger.INFO)
            self._log.info("action=instantiation_start alertaction={}".format(action_name))
            self.utils = None
            self._app_name = _APP_NAME
            self._action_name = action_name
            self._settings = json.loads(settings)
            self.session_key = self._settings.get("session_key", None)
            self.utils = CBEDRUtilities(app_name=self._app_name, session_key=self.session_key)
            self.proxy_string = None
            self._configuration = self._settings.get("configuration", {})
            self.payload = {
                "results_file": self._settings.get("results_file", None),
                "search_name": self._settings.get("search_name", "undefined")
            }
        except Exception as e:
            self._catch_error(e)

    def get_config(self, item, ret=None):
        return self._configuration.get(item, ret)

    def clients_by_org_key(self):
        return {self.edr_orgs[x]["org_name"]: self.edr_orgs[x]["cb"] for x in self.edr_orgs}

    def clients_as_array(self):
        return [self.edr_orgs[x] for x in self.edr_orgs]

    def setup_client(self, guid):
        try:
            credential = self.utils.get_credential(self._app_name, guid)
            auth_host = self.utils.get_api_config(guid)
            vs = auth_host.get("ssl_verify", "0")
            vss = True
            if vs == '0' or vs == 'false' or vs == 'f':
                vss = False
            client_settings = {"verify": vss, "verbose": True}
            ps = None
            verify_proxy_ssl = True
            pg = auth_host.get("proxy_guid", None)
            if pg and pg != "NOPROXYSELECTED" and pg != "undefined":
                self._log.info("action=proxy_found guid={} type={}".format(pg, type(pg)))
                proxy = self.utils.get_proxy(pg)
                proxy_string, verify_ssl, proto = proxy
                ps = {proto: proxy_string}
            if ps is not None:
                client_settings["proxies"] = ps
            return {"cb": CbEnterpriseResponseAPI(
                integration_name="SplunkApp/{}/{} AlertAction/{}".format(self._app_name,
                                                                         version.__version__,
                                                                         self._action_name),
                url="https://{}".format(auth_host["cb_edr_env"]),
                token='{}'.format(credential),
                proxy=client_settings.get("proxies", {}).get("http"),
                ssl_verify=vss),
                    "org_name": auth_host["org_name"],
                    "url": auth_host["cb_edr_env"]}

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error_msg = " " \
                        "error_message=\"{}\" " \
                        "error_type=\"{}\" " \
                        "error_arguments=\"{}\" " \
                        "error_filename=\"{}\" " \
                        "error_line_number=\"{}\" " \
                        "action_name=\"{}\" " \
                .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno, self._action_name)
            self._log.warn("action=setup_client status=failed exception={}".format(error_msg))
            return {"cb": None, "org_name": None, "url": None}

    def setup(self):
        try:
            self._log.debug("action=start_setup")
            apis = self.get_config("api_config", "")
            self.edr_orgs = {k:v for k, v in {x: self.setup_client(x) for x in apis.split(",")}.items() if not v["cb"] is None}
            self._log.info("action=setup edr_orgs={}".format(self.edr_orgs))
        except Exception as e:
            self._catch_error(e, self._action_name)

    def _catch_error(self, e, action_name="undefined_command"):
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
        self._log.error(error_msg)
