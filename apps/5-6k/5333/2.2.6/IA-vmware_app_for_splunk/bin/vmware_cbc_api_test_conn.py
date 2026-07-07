import json
import sys
import splunk.appserver.mrsparkle.lib.util as util
from VMWUtilities import KennyLoggins
from vmware_cbc_utilities import CBCUtilities
from urllib.parse import parse_qs
import logging
import os
import splunk
from splunk import version
import multiprocessing.dummy as mp

import vmware_paths

try:
    from cbc_sdk import CBCloudAPI, __version__ as __cbc_version__
    from cbc_sdk.platform import Device, Alert, AssetGroup, Device, Vulnerability
    from cbc_sdk.enterprise_edr.auth_events import AuthEvent
    from cbc_sdk.audit_remediation import RunHistory
    from cbc_sdk.endpoint_standard import USBDevice
except Exception as ex:
    import traceback
    __cbc_version__ = "unknown"
    CBCloudAPI = None
    _cbc_import_tb = traceback.format_exc()
    logging.getLogger("splunk.rest").fatal(
        "Unable to import cbc_sdk: %s: %s\npython=%s\n%s",
        type(ex).__name__, ex, sys.version, _cbc_import_tb
    )

__app_name__ = vmware_paths.__app_name__
__version__ = vmware_paths.__app_version__
os.environ["PYTHONPATH"] = ",".join(sys.path)
#
# loader = importlib.machinery.SourceFileLoader('six', make_splunkhome_path(["etc", "apps", __app_name__, "lib", "six.py"]))
# spec = importlib.util.spec_from_loader('six', loader)
# six = importlib.util.module_from_spec(spec)
# loader.exec_module(six)
# sys.modules['six'] = six
#
# if sys.platform == "win32":
#     import msvcrt
#
#     # Binary mode is required for persistent mode on Windows.
#     msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
#     msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
#     msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

kl = KennyLoggins()
__action__ = "vmware_cbc_endpt_test_conn"
logger = kl.get_logger(
    app_name=__app_name__,
    file_name=__action__,
    log_level=logging.INFO,
)
cbc_override = kl.get_logger(
    app_name=__app_name__, file_name="cbc_sdk.connection", log_level=logging.INFO
)
_LOCALDIR = os.path.join(util.get_apps_dir(), __app_name__, "local")
if not os.path.exists(_LOCALDIR):
    os.makedirs(_LOCALDIR)


class Test(splunk.rest.BaseRestHandler):
    def __init__(self, method, requestInfo, responseInfo, sessionKey):
        splunk.rest.BaseRestHandler.__init__(
            self, method, requestInfo, responseInfo, sessionKey
        )
        self.utils = CBCUtilities(app_name=__app_name__, session_key=sessionKey)
        self.log = logger
        self.cb = None
        self.org = None

    @staticmethod
    def _catch_error(e):
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        return "log_level=ERROR exception='{}' exception_type='{}' filename='{}' exception_line='{}' args='{}'".format(
            str(e), type(e), fname, exc_tb.tb_lineno, "{}".format(e)
        ), "{}".format(
            str(e)
        )

    def setup_cb(
        self,
        conn_type="heartbeat",
        api_key_secret=None,
        guid=None,
        proxy_guid=None,
        credential_guid=None,
        **kwargs,
    ):
        if CBCloudAPI is None:
            raise ImportError(
                "CBC SDK failed to load. Check splunkd logs for "
                "'FATAL_ERROR: action=HARD_TO_FIND' to see the root cause."
            )
        try:
            if credential_guid is not None and conn_type != "heartbeat":
                api_key_secret = self.utils.get_credential(
                    __app_name__, credential_guid
                )
                t = self.utils.get_tenant(credential_guid)
            elif guid is not None and conn_type == "heartbeat":
                api_key_secret = self.utils.get_credential(__app_name__, guid)
                t = self.utils.get_tenant(guid)
            else:
                t = {
                    "org_key": kwargs.get("org_key"),
                    "cbc_env": kwargs.get("cbc_env"),
                    "comment": kwargs.get("comment"),
                    "tenant": kwargs.get("tenant"),
                    "api_key": kwargs.get("api_key"),
                }
            self.org = t["org_key"]
            verify_ssl = True
            proxy_string = None
            if proxy_guid and proxy_guid != "NOPROXYSELECTED" and len(proxy_guid) > 0:
                self.log.info("action=proxy_found sub_action=proxy guid={}".format(proxy_guid))
                proxy = self.utils.get_proxy(proxy_guid)
                proto = "http"
                self.log.debug(
                    "action=checking_ssl sub_action=proxy use_ssl={}".format(proxy.get("use_ssl"))
                )
                if proxy.get("use_ssl") == "on":
                    proto = "https"
                proxy_string = "{}://{}".format(proto, proxy["proxy_url"])
                if "proxy_user" in proxy:
                    self.log.debug(f"action=proxy_user sub_action=proxy user={proxy['proxy_user']}")
                    proxy_string = "{}://{}:{}@{}".format(
                        proto,
                        proxy["proxy_user"],
                        proxy["proxy_pass"],
                        proxy["proxy_url"],
                    )
                if proxy.get("verify_ssl") == "off":
                    verify_ssl = False
                self.log.debug(
                    "action=proxy_string sub_action=proxy verify_ssl={} {}".format(
                        verify_ssl, proxy_string.replace(proxy.get("proxy_pass", "<<<READACTED>>>"), "<<<READACTED>>>")
                    )
                )
            user_agent = " ".join(
                [
                    f"Splunk/{self.getProductType()}/{version.__version__}",
                    f"SplunkApp/{__app_name__}/{__version__}",
                    f"ConnectionTest/{__action__}/{conn_type}",
                    f"CBC_SDK/{__cbc_version__}",
                    f"Python/{'.'.join([f'{x}' for x in sys.version_info[:2]])}",
                ]
            )
            self.log.info(
                'action=setting_up_base_api user_agent="{}"'.format(user_agent)
            )
            cb = CBCloudAPI(
                timeout=10.0,
                integration_name=user_agent,
                url=f'https://{t["cbc_env"]}',
                org_key=f'{t["org_key"]}',
                token=f'{api_key_secret}/{t["api_key"]}',
                proxy=proxy_string,
                ssl_verify=verify_ssl,
            )
            return cb
        except Exception as e:
            self._catch_error(e)
            raise e

    # Inputs: Alert, Audit Log (search, not pull), Live Query, Vulnerability, Auth Event, Assets (USB included)
    # Alert: org.alerts (Read)

    # def _test_live_query_results: livequery.manage (Read)
    # def _test_vulnerabilities: vulnerabilityAssessment.data (Read)
    # def _test_audit_logs_class: org.audits (Read)
    # def _test_asset_input_class: UNKNOWN

    def _test_live_query_results(self, **kwargs):
        #
        # Alert
        class_name = f"Live Query Results"

        ret = {
            "status": "success",
            "code": 0,
            "message": "Success",
            "permission_required": "livequery.manage (Read)",
        }
        try:
            logger.debug(f' conn_type={kwargs["conn_type"]}')
            query = kwargs["result_query"] if "result_query" in kwargs else "*"
            dvc = self.cb.select(RunHistory).where(query).sort_by("CREATE_TIME", "DESC").first()
            logger.debug(f' action="test_{class_name}" result={dvc}')
        except IndexError as e:
            logger.warning(' '.join([f'action="test_{class_name}"',
                                     "result=no_results_returned",
                                     "status=success",
                                     f"exception={e}",
                                     f"exception_type='{type(e)}'",]))
        except Exception as e:
            ret["code"] = 1
            ret["status"] = "failure"
            error_msg, clean = self._catch_error(e)
            logger.error(f' {error_msg} type={type(e)}')
            ret["message"] = clean.split(":")[0]
            ret["full_message"] = error_msg
            ret["e"] = f"{e}"
        return class_name, ret
    
    def _test_vulnerabilities_class(self, **kwargs):
        #
        # Alert
        class_name = f"Vulnerabilities"
        ret = {
            "status": "success",
            "code": 0,
            "message": "Success",
            "permission_required": "vulnerabilityAssessment.data (Read)",
        }
        try:
            logger.debug(f' conn_type={kwargs["conn_type"]}')
            dvc = self.cb.select(Vulnerability.OrgSummary).submit()
            logger.debug(f' action="test_{class_name}" result={dvc}')
        except IndexError as e:
            logger.warning(' '.join([f'action="test_{class_name}"',
                                     "result=no_results_returned",
                                     "status=success",
                                     f"exception={e}",
                                     f"exception_type='{type(e)}'",]))
        except Exception as e:
            ret["code"] = 1
            ret["status"] = "failure"
            error_msg, clean = self._catch_error(e)
            logger.error(f' {error_msg}')
            ret["message"] = clean.split(":")[0]
            ret["full_message"] = error_msg
            ret["e"] = f"{e}"
        return class_name, ret

    def _test_audit_logs_class(self, **kwargs):
        class_name = f"Audit Logs"
        ret = {
            "status": "success",
            "code": 0,
            "message": "Success",
            "permission_required": "org.audits (Read)",
        }
        try:
            logger.debug(f' conn_type={kwargs["conn_type"]}')
            url_object = f"/audit_log/v1/orgs/{self.org}/logs/_search"
            dvc = self.cb.post_object(url_object, {"rows": 1})
            logger.debug(f' action="test_{class_name}" result={dvc}')
        except IndexError as e:
            logger.warning(' '.join([f'action="test_{class_name}"',
                                     "result=no_results_returned",
                                     "status=success",
                                     f"exception={e}",
                                     f"exception_type='{type(e)}'",]))
        except Exception as e:
            ret["code"] = 1
            ret["status"] = "failure"
            error_msg, clean = self._catch_error(e)
            logger.error(f' {error_msg}')
            ret["message"] = clean.split(":")[0]
            ret["full_message"] = error_msg
            ret["e"] = f"{e}"
        return class_name, ret

    def _test_asset_usb_input_class(self, **kwargs):
        #
        # Alert
        class_name = f"Assets (USB)"
        ret = {
            "status": "success",
            "code": 0,
            "message": "Success",
            "permission_required": "external-device.manage (READ)",
        }
        try:
            logger.debug(f' conn_type={kwargs["conn_type"]}')
            dvc = self.cb.select(USBDevice).set_max_rows(1).first()
            logger.debug(f' action="test_{class_name}" result={dvc}')
        except IndexError as e:
            logger.warning(' '.join([f'action="test_{class_name}"',
                                     "result=no_results_returned",
                                     "status=success",
                                     f"exception={e}",
                                     f"exception_type='{type(e)}'",]))
        except Exception as e:
            ret["code"] = 1
            ret["status"] = "failure"
            error_msg, clean = self._catch_error(e)
            logger.error(f' {error_msg}')
            ret["message"] = clean.split(":")[0]
            ret["full_message"] = error_msg
            ret["e"] = f"{e}"
        return class_name, ret

    def _test_asset_group_input_class(self, **kwargs):
        #
        # Alert
        class_name = f"Assets (Groups)"
        ret = {
            "status": "success",
            "code": 0,
            "message": "Success",
            "permission_required": "group-management (READ)",
        }
        try:
            logger.debug(f' conn_type={kwargs["conn_type"]}')
            dvc = AssetGroup.get_all_groups(self.cb)
            logger.debug(f' action="test_{class_name}" result={dvc}')
        except IndexError as e:
            logger.warning(' '.join([f'action="test_{class_name}"',
                                     "result=no_results_returned",
                                     "status=success",
                                     f"exception={e}",
                                     f"exception_type='{type(e)}'",]))
        except Exception as e:
            ret["code"] = 1
            ret["status"] = "failure"
            error_msg, clean = self._catch_error(e)
            logger.error(f' {error_msg}')
            ret["message"] = clean.split(":")[0]
            ret["full_message"] = error_msg
            ret["e"] = f"{e}"
        return class_name, ret

    def _test_auth_events_class(self, **kwargs):
        #
        # Alert
        class_name = f"Auth Events"
        ret = {
            "status": "success",
            "code": 0,
            "message": "Success",
            "permission_required": "org.search.events (Read, Create)",
        }
        try:
            logger.debug(f' conn_type={kwargs["conn_type"]}')
            dvc = self.cb.select(AuthEvent).where("auth_username:*").first()
            logger.debug(f' action="test_{class_name}" result={dvc}')
        except IndexError as e:
            logger.warning(' '.join([f'action="test_{class_name}"',
                                     "result=no_results_returned",
                                     "status=success",
                                     f"exception={e}",
                                     f"exception_type='{type(e)}'",]))
        except Exception as e:
            ret["code"] = 1
            ret["status"] = "failure"
            error_msg, clean = self._catch_error(e)
            logger.error(f' {error_msg}')
            ret["message"] = clean.split(":")[0]
            ret["full_message"] = error_msg
            ret["e"] = f"{e}"
        return class_name, ret

    def _test_alert_class(self, **kwargs):
        #
        # Alert
        class_name = f"Alert"
        ret = {
            "status": "success",
            "code": 0,
            "message": "Success",
            "permission_required": "org.alerts (Read)",
        }
        try:
            logger.debug(f' conn_type={kwargs["conn_type"]}')
            if kwargs["conn_type"] == "alerts":
                logger.info(f' kwargs={kwargs}')
                query = kwargs.get("query", "*")
                at = kwargs.get("alert_type")
                dvc = (self.cb.select(Alert)
                       .set_minimum_severity(kwargs.get("severity", 0))
                       .add_criteria("type", [] if at == "ALL" else at.split(","))
                       .where(q=query)
                       .first())
                logger.debug(f' action="test_{class_name}" result={dvc}')
            else:
                dvc = self.cb.select(Alert).first()
                logger.debug(f' action="test_{class_name}" result={dvc}')
        except IndexError as e:
            logger.warning(' '.join([f'action="test_{class_name}"',
                                     "result=no_results_returned",
                                     "status=success",
                                     f"exception={e}",
                                     f"exception_type='{type(e)}'",]))
        except Exception as e:
            ret["code"] = 1
            ret["status"] = "failure"
            error_msg, clean = self._catch_error(e)
            logger.error(f'action=test_alert_class {error_msg}')
            ret["message"] = clean.split(":")[0]
            ret["full_message"] = error_msg
            ret["e"] = f"{e}"
        return class_name, ret

    def _test_device_class(self, **kwargs):
        # Device
        class_name = f"Assets (Device)"
        ret = {
            "status": "success",
            "code": 0,
            "message": "Success",
            "permission_required": "device (Read)",
        }
        try:
            logger.debug(f' conn_type={kwargs["conn_type"]}')
            if kwargs["conn_type"] == "assets":
                logger.info(f' conn_type={kwargs}')
                at = kwargs.get("deployment_type")
                invalid_device_deployment_types = ["USB_DEVICES", "ASSET_GROUPS", "ALL", "CHROME_OS"]
                dvc = (self.cb.select(Device)
                       .set_deployment_type([x for x in at.split(",") if x not in invalid_device_deployment_types])
                       .first())
                logger.debug(f' action="test_{class_name}" result={dvc}')
            else:
                dvc = self.cb.select(Device).first()
                logger.debug(f' action="test_{class_name}" result={dvc}')
        except IndexError as e:
            logger.warning(' '.join([f'action="test_{class_name}"',
                                     "result=no_results_returned",
                                     "status=success",
                                     f"exception={e}",
                                     f"exception_type='{type(e)}'",]))
        except Exception as e:
            ret["code"] = 1
            ret["status"] = "failure"
            error_msg, clean = self._catch_error(e)
            ret["message"] = clean.split(":")[0]
            ret["full_message"] = error_msg
            ret["e"] = f"{e}"
        return class_name, ret

    # @expose_page(must_login=False, methods=['GET'])
    def handle_POST(self, **kwargs):
        try:
            params = {
                k: v[0] for k, v in parse_qs(self.request.get("payload", "")).items()
            }
            logger.info(f"action=params params={params}")
            if "cbc_env" not in params and "credential_guid" not in params:
                ret_code = 400
                tests = {
                    "Invalid Config": {
                        "code": 201,
                        "message": "API Parameters are incorrect.",
                        "permission_required": "",
                    }
                }
                return [
                    {
                        "status": "success",
                        "data": "success",
                        "code": ret_code,
                        "msg": tests,
                        "params": params,
                    }
                ]

            conn_type = (
                "heartbeat" if "conn_type" not in params else params["conn_type"]
            )
            test_funcs = {
                "heartbeat": [],
                "alerts": [self._test_alert_class],
                "auth_events": [self._test_auth_events_class],
                "live_query": [self._test_live_query_results],
                "assets": [self._test_asset_group_input_class, self._test_device_class, self._test_asset_usb_input_class],
                "vulns": [self._test_vulnerabilities_class],
                "audit_logs": [self._test_audit_logs_class]
            }
            for f in list(test_funcs.keys()):
                if f != "heartbeat":
                    test_funcs["heartbeat"].extend(test_funcs[f])
            self.cb = self.setup_cb(**params)
            tests = {}
            ret_code = 200
            # Update this to accept "heartbeat", or a key for each input type, and test that input specifically
            # Audit log is only exception, as that burns a record, (try audit log search endpoint).
            # Return messages, indicating, success, failures, "query worked, but nothing returned"
            tests_to_perform = test_funcs[conn_type] if conn_type in test_funcs else test_funcs["heartbeat"]
            p = mp.Pool(len(tests_to_perform))
            # tasks = zip(tests_to_perform, repeat(params))
            futures = [p.apply_async(t, (), params) for t in tests_to_perform]
            results = [fut.get() for fut in futures]
            for test_name, test_code in results:
                tests[test_name] = test_code
                if test_code["status"] == "failure":
                    e_local = test_code["e"].split(": {")
                    e_msg = "{}"
                    if len(e_local) > 1:
                        e_msg=f"{'{'}{e_local[1]}"
                    msg = test_code["message"]
                    try:
                        d = json.loads(e_msg)
                        logger.debug(f"action=test_results d={d}")
                        if "message" in d:
                            msg = d["message"]
                    except:
                        pass
                    logger.debug(
                        f'action=test_results test_name="{test_name}" code={test_code["code"]} message="{msg}"')
                    tests[test_name]["message"] = msg

                ret_code += test_code["code"]
            return [
                {"status": "success", "data": "success", "code": ret_code, "msg": tests}
            ]
        except Exception as e:
            error_msg, clean = self._catch_error(e)
            logger.error("{}".format(error_msg))
            return [{"msg": {"Failure": {"message": clean, "code": 0}},
                     "exception_message": clean,
                     "operation": "error",
                     "code": 500,
                     "title": "Splunk Python Endpoint Error"}]

    def handle_GET(self, **kwargs):
        return [{"msg": "GET Not Supported", "operation": "error", "code": 400}]
