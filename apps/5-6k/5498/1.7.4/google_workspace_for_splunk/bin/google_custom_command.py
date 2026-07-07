from Utilities import KennyLoggins
from google_constants import global_scopes, app_name as _APP_NAME
import logging as logger
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from google_utilities import GSuiteUtilities
import sys
import os
import httplib2
import json

sys.path.insert(0, make_splunkhome_path(["etc", "apps", _APP_NAME, "lib"]))
os.environ["PYTHONPATH"] = ",".join(sys.path)
from apiclient.discovery import build
from google.oauth2 import service_account
import google_auth_httplib2
import urllib

class GWCommand(object):
    def __init__(self, cmd_name, session_key):
        try:
            mykl = KennyLoggins()
            self._log = mykl.get_logger(
                app_name=_APP_NAME, file_name=cmd_name, log_level=logger.INFO)
            self._log.info(
                "action=instantiation_start cmd={}".format(cmd_name))
            self._app_name = _APP_NAME
            self._cmd_name = cmd_name
            self._settings = None
            self.session_key = session_key
            self._configuration = None
            self.utils = None
            self.access_key = None
            self.proxy = None
            self.verify_proxy_ssl = None
            self.build = None
            self.credential = None
            self._rawcredential = None
            self.non_delegated_credential = None
            self.non_delegated_http = None
            self.http = None
            self.service = None
            self.base_st = "google:workspaces"
            self.scopes = global_scopes
            self.utils = GSuiteUtilities(
                app_name=self._app_name, session_key=self.session_key)
            self._configuration = self.utils.get_command(cmd_name)
            self._log.info("action=instantiation_complete")
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
            self._catch_error(e, cmd_name=cmd_name)

    def init(self, settings={}):
        self._settings = settings
        self.access_key = self.utils.get_credential(self._app_name,
                                                    self._configuration.get(["guid"]))
        self.proxy, self.verify_proxy_ssl = self.setup_proxy(
            self._configuration.get("proxy_guid", None))

    def _catch_error(self, e, cmd_name="undefined_alert"):
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        error_msg = " " \
                    "error_message=\"{}\" " \
                    "error_type=\"{}\" " \
                    "error_arguments=\"{}\" " \
                    "error_filename=\"{}\" " \
                    "error_line_number=\"{}\" " \
                    "action_name=\"{}\" " \
            .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno, cmd_name)
        self._log.error(error_msg)

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
                if proxy.get("use_ssl") == "true" or "{}".format(proxy.get("use_ssl")) == "1":
                    proto = "https"
                proxy_string = "{}://{}".format(proto, proxy["proxy_url"])
                if "proxy_user" in proxy:
                    proxy_string = "{}://{}:{}@{}".format(proto,
                                                          proxy["proxy_user"],
                                                          proxy["proxy_pass"],
                                                          proxy["proxy_url"])
                if proxy.get("use_ssl") == "false" or "{}".format(proxy.get("use_ssl")) == "0":
                    verify_ssl = False
                self._log.debug("action=proxy_string verify_ssl={} {}".format(verify_ssl,
                                                                              proxy["proxy_url"]))
            return proxy_string, verify_ssl
        except Exception as e:
            self._catch_error(e)
            raise e

    def get_config(self, key, default=None):
        return self._configuration.get(key, default)

    def setup_gw(self, scope):
        try:
            self._configuration["api_key"] = self.utils.get_credential(self._app_name,
                                                                       self.get_config("credential", None))
            t = self.utils.get_workspace_creds(self.get_config("credential", None))
            proxy_guid = t.get("proxy_guid", None)
            self._configuration["domain"] = t["domain"]
            self._configuration["impersonation_user"] = t["impersonation_user"]
            self._log.info("action=checking_for_proxy guid={}".format(proxy_guid))
            verify_ssl = True
            proxy_info = None
            if proxy_guid and proxy_guid != "NOPROXYSELECTED":
                self._log.info("action=proxy_found guid={}".format(proxy_guid))
                proxy = self.utils.get_proxy(proxy_guid)
                proto = httplib2.socks.PROXY_TYPE_HTTP
                self._log.debug("action=checking_ssl use_ssl={}".format(proxy.get("use_ssl")))
                if proxy.get("use_ssl") == "true" or "{}".format(proxy.get("use_ssl")) == "1":
                    proto = httplib2.socks.PROXY_TYPE_HTTP
                if proxy.get("use_ssl") == "false" or "{}".format(proxy.get("use_ssl")) == "0":
                    verify_ssl = False
                proxy_info = httplib2.ProxyInfo(
                    proto,
                    proxy_host="{}".format(proxy["proxy_url"].split(":")[0]),
                    proxy_port=int(proxy["proxy_url"].split(":")[1]),
                    proxy_pass=proxy.get("proxy_pass", None),
                    proxy_user=proxy.get("proxy_user", None))
                self._log.info("action=proxy_string verify_ssl={} {}".format(verify_ssl,
                                                                             proxy["proxy_url"]))
            # These are not in the header due to complication issues when including before the path is set.
            # import pkg_resources
            # import importlib
            # importlib.reload(pkg_resources)
            self.build = build
            credential = urllib.parse.unquote(self.get_config("api_key"))
            self._rawcredential = credential
            self.non_delegated_credential = service_account.Credentials.from_service_account_info(
                json.loads(credential),
                scopes=self.scopes[scope])
            self.credential = self.non_delegated_credential.with_subject(self.get_config("impersonation_user"))
            self._log.info("action=setup_http proxy_info={}".format(proxy_info))
            self.http = google_auth_httplib2.AuthorizedHttp(
                self.credential,
                http=httplib2.Http(proxy_info=proxy_info))
            self.non_delegated_http = google_auth_httplib2.AuthorizedHttp(
                self.non_delegated_credential,
                http=httplib2.Http(proxy_info=proxy_info))
            # # Reference for credential handling
            # https://developers.google.com/identity/protocols/oauth2/service-account#expiration
        except Exception as e:
            self._catch_error(e)
            raise e
