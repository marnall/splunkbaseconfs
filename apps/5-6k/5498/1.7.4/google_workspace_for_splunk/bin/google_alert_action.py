from google_constants import app_name as _package_id, global_scopes
from AlertAction import CreateAlertModularAction
import json
import time
from google_utilities import GSuiteUtilities
import httplib2
import os
import sys
import re
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunk.util import normalizeBoolean

sys.path.insert(0, make_splunkhome_path(["etc", "apps", _package_id, "lib"]))
os.environ["PYTHONPATH"] = ",".join(sys.path)

from apiclient.discovery import build

class GWAlertAction(CreateAlertModularAction):
    def __init__(self, settings=None, action_name=None, filename=None, stanza=None):
        try:
            CreateAlertModularAction.__init__(self, settings, action_name=action_name,
                                              app_name=_package_id,
                                              global_configuration={"filename": "alert_actions",
                                                                    "stanza": action_name})
            self._app_name = _package_id
            self._action_name = action_name
            self.utils = None
            self.proxy_string = None
            self.proxy_info = None
            self.http = None
            self.retry = None
            self.build = None
            self.credential = None
            self.bigquery = None
            self.pubsub = None
            self.SchemaField = None
            self._rawcredential = None
            self.non_delegated_credential = None
            self.non_delegated_http = None
            self.service = None
            self.base_st = "google:workspaces"
            self.scopes = global_scopes
            self._settings = json.loads(settings)
            self.session_key = self._settings.get("session_key", None)
            self.utils = GSuiteUtilities(app_name=self._app_name, session_key=self.session_key)
            self.server_info = self.utils.get_server_info()
            self._configuration = self._settings.get("configuration", {})
            self._current_user = self.utils.get_current_user_information()
            self.localized_time_zone = self._current_user.get("tz", "")
            if len(self.localized_time_zone) < 1:
                self.localized_time_zone = time.tzname[time.localtime().tm_isdst]
            self._log.debug("user={} is_dst={} time_zone={} configuration={}".format(
                self._current_user.get("username", "UNKNOWN"),
                time.localtime().tm_isdst,
                self.localized_time_zone,
                self._settings))
            self.payload = {
                "results_file": self._settings.get("results_file", None),
                "search_name": self._settings.get("search_name", "undefined")
            }
            self._config = {}
        except Exception as e:
            self._catch_error(e, action_name=action_name)

    def get_config(self, item, ret=None):
        return self._configuration.get(item, ret)

    def a_build_url(self, endpoint):
        return "{}/servicesNS/-/{}/{}/?output_mode=json".format(
            self._splunk_url, self.app_name, "/".join(endpoint)
        )

    def get_evt_idx(self, evt):
        try:
            url = self.a_build_url(["configs", "conf-eventtypes", evt])
            self._log.debug("function=get_evt_idx evt={} url={} verify={}".format(evt, url, self._verify_splunk))
            r = self._get(url)
            self._log.debug("evtidx_rc=".format(r))
            base_evttype = r.json()["entry"][0]["content"]["search"]
            evt = re.compile(r'index\s* IN \s*\(\s*([a-z\d_\-]+)\s*\)')
            found = evt.match(base_evttype)
            self._log.debug("found=evt_re re={} match={}".format(evt, found.groups()[0]))
            return r.status_code, found.groups()[0]
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            self._log.error("function=get_evtidx exception_line={} file={}  message={}".format(exc_tb.tb_lineno,
                                                                                               fname, e))

    def setup_gw(self, scope):
        try:
            self._config["api_key"] = self.utils.get_credential(self._app_name,
                                                                self.get_config("credential", None))
            if self._config["api_key"] is None:
                raise Exception("API Key not Found")
            t = self.utils.get_workspace_creds(self.get_config("credential", None))
            proxy_guid = t.get("proxy_guid", None)
            self._config["domain"] = t["domain"]
            self._config["impersonation_user"] = t["impersonation_user"]
            self._log.info("action=checking_for_proxy guid={}".format(proxy_guid))
            verify_ssl = True
            proxy_info = None
            if proxy_guid and proxy_guid != "NOPROXYSELECTED":
                self._log.info("action=proxy_found guid={}".format(proxy_guid))
                proxy = self.utils.get_proxy(proxy_guid)
                proto = httplib2.socks.PROXY_TYPE_HTTP
                self._log.debug("action=checking_ssl use_ssl={}".format(proxy.get("use_ssl")))
                use_ssl = normalizeBoolean(proxy.get("use_ssl", False))
                if use_ssl:
                    proto = httplib2.socks.PROXY_TYPE_HTTP
                if not use_ssl:
                    verify_ssl = False
                proxy_host = "{}".format(proxy["proxy_url"].split(":")[0])
                proxy_port = int(proxy["proxy_url"].split(":")[1])
                proxy_info = httplib2.ProxyInfo(
                    proto,
                    proxy_host=proxy_host,
                    proxy_port=proxy_port,
                    proxy_pass=proxy.get("proxy_pass", None),
                    proxy_user=proxy.get("proxy_user", None))
                self._log.info("action=proxy_string verify_ssl={} {}".format(verify_ssl,
                                                                             proxy["proxy_url"]))
                self.proxy_string = "http{}://{}{}:{}".format(
                    "s" if use_ssl else "",
                    "{}:{}@".format(proxy.get("proxy_user", ""), proxy.get("proxy_pass", "")) if proxy.get("proxy_user", False) else "",
                    proxy_host,
                    proxy_port
                )
            # These are not in the header due to complication issues when including before the path is set.
            # import pkg_resources
            # import importlib
            # importlib.reload(pkg_resources)
            if scope == "bigquery":
                #pkg_resources.get_distribution('google-cloud-bigquery')
                from google.cloud import bigquery
                self.bigquery = bigquery
                self.SchemaField = bigquery.SchemaField
            if scope == "pubsub":
                #pkg_resources.get_distribution('google-cloud-pubsub')
                from google.cloud import pubsub_v1
                from google.api_core import retry
                self.retry = retry
                self.pubsub = pubsub_v1
            from google.oauth2 import service_account
            from google.auth.exceptions import RefreshError
            import google_auth_httplib2
            import six
            import urllib
            self.build = build
            credential = urllib.parse.unquote(self._config["api_key"])
            self._rawcredential = credential
            self.non_delegated_credential = service_account.Credentials.from_service_account_info(
                json.loads(credential),
                scopes=self.scopes[scope])
            self.credential = self.non_delegated_credential.with_subject(self._config["impersonation_user"])
            self._log.info("action=setup_http proxy_info={}".format(proxy_info))
            self.proxy_info = proxy_info
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

    def setup_vault(self):
        self.setup_gw("vault")
        self.service = self.build('vault', 'v1', http=self.http)

    def create_matter(self, name, description):
        matter_content = {
            'name': name,
            'description': description,
        }
        matter = self.service.matters().create(body=matter_content).execute()
        return matter

    def close_matter(self, matter_id):
        close_response = self.service.matters().close(matterId=matter_id, body={}).execute()
        return close_response['matter']

    def reopen_matter(self, matter_id):
        reopen_response = self.service.matters().reopen(
            matterId=matter_id, body={}).execute()
        return reopen_response['matter']

    def delete_matter(self, matter_id):
        self.service.matters().delete(matterId=matter_id).execute()
        return self.get_matter(matter_id)

    def get_matter(self, matter_id):
        matter = self.service.matters().get(matterId=matter_id, view='FULL').execute()
        return matter

    def undelete_matter(self, matter_id):
        undeleted_matter = self.service.matters().undelete(
            matterId=matter_id, body={}).execute()
        return undeleted_matter

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
        self._log.error(error_msg)

