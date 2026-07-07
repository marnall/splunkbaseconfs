import logging as logger
import uuid

from s1_utilities import S1Utilities
from Utilities import KennyLoggins
from s1_app_properties import __app_name__ as _splunk_package_name, __version__ as version
import s1_paths
import sys
import os
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path, getProductName

# These imports require _paths import
from management.mgmtsdk_v2_1.mgmt import Management

os.environ["SDK_LOG_PATH"] = make_splunkhome_path(
    ["var", "log", "splunk", _splunk_package_name, "mgmt_sdk.log"]
)
LOG_LEVELS = {10: "debug", 20: "info", 30: "warning", 40: "error"}
kl = KennyLoggins()
iLog = kl.get_logger(
    app_name=_splunk_package_name,
    file_name="s1-instantiation-logger",
    log_level=logger.INFO,
)
format_string = '[MgmtSdk.Client][%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] pid=%(process)d tid=%(threadName)s function="%(funcName)s" version="{}" %(message)s'.format(
    version
)
force_log_creation = kl.get_logger(
    _splunk_package_name, "mgmt_sdk", logger.INFO, format_string=format_string
)
os.environ["SDK_LOG_LEVEL"] = LOG_LEVELS.get(force_log_creation.level, "warning")
force_log_creation.info(
    "action=forcing_line_due_to_windowsness_in_python_3 level={}".format(
        force_log_creation.level
    )
)
iLog.info(
    "action=global_check product={} path_len={}".format(getProductName(), len(sys.path))
)


class S1Command(object):
    def __init__(self, cmd_name, session_key, log=None):
        try:
            if log is None:
                self._log = kl.get_logger(
                    app_name=_splunk_package_name, file_name=cmd_name, log_level=logger.INFO
                )
            else:
                self._log = log
            self._log.info(
                f'action=logging_init name={self._log.name} level={self._log.level} handlers={self._log.handlers}')
            self.tracking_uuid = str(uuid.uuid4())
            self.log_attrs = ["tracking_uuid"]
            self.inform(
                action="instantiation",
                cmd=cmd_name,
                logger_name=self._log.name,
                log_level=self._log.level,
                eff_log_level=self._log.getEffectiveLevel(),
            )
            self.verify_ssl = True
            self.utils = None
            self.session_key = session_key
            self._app_name = _splunk_package_name
            self.utils = S1Utilities(
                app_name=self._app_name, session_key=self.session_key
            )
            self.proxy_string = None
            self.s1_mgmts = {}
            self._configuration = self.utils.get_command(cmd_name)
            self.cmd_name = cmd_name
        except Exception as e:
            self._catch_error(e)

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
            self.error(exception=f"{e}")

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

    def setup_management(self, guid, management=Management):
        credential = self.utils.get_credential(self._app_name, guid)
        auth_host = self.utils.get_api_config(guid)
        vs = auth_host["ssl_verify"]
        vss = True
        if vs == "0" or vs == "false" or vs == "f" or vs == "off":
            vss = False
        client_settings = {"verify": vss, "verbose": True}
        if self.proxy_string is not None:
            client_settings["proxies"] = self.proxy_string
        client_settings["user_agent"] = self.utils.create_user_agent()
        tmp_mgmt = None
        try:
            self.debug(action="setup_management", management=management, url=auth_host["url"], **client_settings, log=self._log.name)
            tmp_mgmt = management(
                auth_host["url"],
                api_token=credential,
                client_settings=client_settings,
                log=self._log,
            )
            self.debug(action="setup_management", log_level=self._log.level)
        except Exception as e:
            self.error(action="exception_bypass", exception=f"{e}")
            raise
        return {"mgmt": tmp_mgmt, "url": auth_host["url"]}

    def setup(self, mgmt_type="management"):
            return self.setup_mgmt(management=Management)

    def setup_mgmt(self, management=Management):
        try:
            self.debug(action="checking_for_proxy", guid=self.get_config("proxy_guid"))
            ps = None
            verify_ssl = True
            pg = self.get_config("proxy_guid")
            if pg and pg != "NOPROXYSELECTED" and pg != "undefined":
                self.inform(action="proxy_found", type=type(pg), guid=pg)
                proxy = self.utils.get_proxy(self.get_config("proxy_guid"))
                proto = "http"
                self.debug(action="checking_ssl", use_ssl=proxy.get("use_ssl"))
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
                self.debug(
                    action="proxy_string",
                    verify_ssl=verify_ssl,
                    proxy_url=proxy["proxy_url"],
                )
                self.verify_ssl = verify_ssl
                ps = {proto: proxy_string}
            self.proxy_string = ps
            self.debug(
                action="prior_to_split", to_split=self.get_config("auth_hosts", None)
            )
            auth_hosts = self.utils.get_auth_hosts(self.cmd_name)
            auth_host_guids = self._get_auth_host_guids(auth_hosts)
            self.s1_mgmts = {
                x: self.setup_management(x, management)
                for x in auth_host_guids if auth_host_guids
            }
            for z in list(self.s1_mgmts):
                if self.s1_mgmts[z]["mgmt"] is None:
                    self.warn(
                        action="client_instantiation",
                        status="failed",
                        host=z,
                        url=self.s1_mgmts[z]["url"],
                        msg="Client failed to instantiate",
                    )
                    del self.s1_mgmts[z]
                else:
                    self.inform(
                        action="client_instantiation",
                        status="success",
                        host=z,
                        url=self.s1_mgmts[z]["url"],
                    )
        except Exception as e:
            self._catch_error(e)
    
    def _get_auth_host_guids(self, auth_hosts):
        self._log.info("Fetching guids from the available auth hosts")
        guids = []
        for auth_host in auth_hosts:
            if auth_host.get("content",{}).get("guid"):
                guids.append(auth_host.get("content",{}).get("guid"))
        self._log.info(f"Fetched guids from the available auth hosts: {str(len(guids))}")
        return guids

    def handle_error(self, e, cmd_name="undefined_alert"):
        return self._catch_error(e, cmd_name)

    def _catch_error(self, e, cmd_name="undefined_alert"):
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
                str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno, cmd_name
            )
        )
        self.error(
            error_msg=str(e),
            error_type=type(e),
            error_arguments=f"{e}",
            error_filename=fname,
            error_line_number=exc_tb.tb_lineno,
            action_name=cmd_name,
        )
        return error_msg
