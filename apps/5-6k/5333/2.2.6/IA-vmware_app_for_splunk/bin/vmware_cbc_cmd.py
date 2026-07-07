import json
import re

import version
from VMWUtilities import KennyLoggins
import logging as logger
import os
import sys
from vmware_cbc_utilities import CBCUtilities
import vmware_paths
from flatten_json import flatten
from cbc_sdk.platform import Alert
from vmware_cbc_classes import EnrichedEventObservationJson
from cbc_sdk import CBCloudAPI
from cbc_sdk.platform import Device
from cbc_sdk.enterprise_edr import Binary as THBinary

__app_name__ = vmware_paths.__app_name__
kl = KennyLoggins()
iLog = kl.get_logger(app_name=__app_name__, file_name="vmware-instantiation-logger", log_level=logger.INFO)


class SplunkCBCTHBinary(THBinary):

    def __init__(self, cb, model_unique_id):
        super(THBinary, self).__init__(cb, model_unique_id=model_unique_id)

    @property
    def summary(self):
        """Returns organization-specific information about this binary.
        """
        info = self._cb.select(THBinary.Summary, self.sha256)
        return info._info

    def to_json(self):
        lines = {}
        for attr in sorted(self._info):
            try:
                val = str(self._info[attr])
            except UnicodeDecodeError:
                val = repr(self._info[attr])
            lines[attr] = val
        return lines


class VmwareCBCCommand(object):

    def __init__(self, cmd_name, session_key):
        try:
            mykl = KennyLoggins()
            self._log = mykl.get_logger(
                app_name=__app_name__, file_name=cmd_name, log_level=logger.INFO)
            self._log.info(
                "action=instantiation_start cmd={}".format(cmd_name))
            self.cb = None
            self.cb_log = None
            self.multi_tenant_apis = {}
            self._app_name = __app_name__
            self._cmd_name = cmd_name
            self._settings = None
            self.session_key = session_key
            self._configuration = None
            self.utils = None
            self._use_multi_tenant = False
            self._tenants = None
            self.tenant = None
            self.api_key_secret = None
            self.proxy = None
            self.verify_ssl = None
            self.verify_proxy_ssl = None
            self.utils = CBCUtilities(
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

    def init(self, settings=None):
        if settings is None:
            settings = {}
        self._settings = settings
        self._tenants = None
        if "," in self._configuration.get("tenant", ""):
            self._tenants = self._configuration.get("tenant").split(",")
            self._use_multi_tenant = True
        else:
            self._tenants = [self._configuration.get("tenant")]
            self._use_multi_tenant = False
        self._log.info("action=setup_tenants multi_tenant={} tenants={}".format(
            self._use_multi_tenant, self._tenants))
        # Set the default tenant to the first one.
        if self._tenants is None:
            raise Exception(
                "API configuration not found for credential guid '{}'".format(self._tenants))
        self._log.debug(
            "action=setup_default_tenant tenant={}".format(self._tenants))
        self.tenant = self.utils.get_tenant(self._tenants[0])
        self.verify_ssl = self._configuration.get("verify_ssl", True)
        if self.utils.is_cloud():
            self.verify_ssl = True
        self._log.debug(
            "action=checking_ssl_verify verify={}".format(self.verify_ssl))
        self.api_key_secret = self.utils.get_credential(self._app_name,
                                                        self.tenant["guid"])
        self.proxy, self.verify_proxy_ssl = self.setup_proxy(
            self._configuration.get("proxy_guid", None))
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
        integration_name = "SplunkApp/{}/{} CustomCommand/{}".format(self._app_name,
                                                                     version.__version__,
                                                                     self._cmd_name)
        url = "https://{}".format(self.tenant["cbc_env"])
        org_key = "{}".format(self.tenant["org_key"])
        token = '{0}/{1}'.format(self.api_key_secret, self.tenant["api_key"])
        self._log.debug("tenant: {}".format(self.tenant))
        self.cb = CBCloudAPI(integration_name=integration_name, url=url, org_key=org_key,
                             token=token, proxy=self.proxy, ssl_verify=self.verify_ssl)
        if self._use_multi_tenant:
            self.setup_multi_tenant_apis()

    def setup_multi_tenant_apis(self):
        try:
            self._log.info("action=setting_up_multi_tenant_apis")
            integration_name = "SplunkApp/{}/{} CustomCommand/{}".format(self._app_name,
                                                                         version.__version__,
                                                                         self._cmd_name)
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
                self.multi_tenant_apis[org_key]["cb"] = CBCloudAPI(integration_name=integration_name, url=url,
                                                                   org_key=org_key,
                                                                   token=token, proxy=self.proxy,
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

    def get_alert_history(self, alert_id, org_key):
        try:
            c = None
            if self._use_multi_tenant:
                self._log.info(
                    "action=selecting_cb org_key={}".format(org_key))
                c = self.multi_tenant_apis[org_key]["cb"]
            else:
                self._log.info("action=selected_single_cb")
                c = self.cb
            alert_history = c.select(Alert, alert_id).get_history()
            threat_history = c.select(Alert, alert_id).get_history(
                threat=True
            )
            results = []
            fields = []
            sep = "."
            for note in threat_history:
                n, f = flatten(note, sep)
                [fields.append(fs) for fs in f]
                self._log.debug(f"action=flatten_threat_history n={n}")
                results.append(n)

            arh_sep = "|"
            for alert in alert_history:
                if alert["type"] == "ALERT_NOTE_ADDED" and "note" in alert and "thread" in alert["note"]:
                    for thread in alert["note"]["thread"]:
                        if "read_history" in thread:
                            u = []
                            for rh in list(thread["read_history"].keys()):
                                u.append(f"{rh}{arh_sep}{thread['read_history'][rh]}")
                            thread["read_history"] = ";".join(u)
                        if "note" in thread:
                            try:
                                parsed = json.loads(re.sub("'", "\"", thread["note"]))
                                thread["message"] = ';'.join([p["children"][0]["text"] for p in parsed])
                            except Exception as e:
                                self._log.info(f'action=parse_note_message alert="{alert["note"]["note"]}" exception="{e}"')
                                thread["message"] = thread["note"]
                        t = {"note": thread, "type": "ALERT_NOTE_ADDED"}
                        a, f = flatten(t, sep)
                        [fields.append(fs) for fs in f]
                        results.append(a)
                    alert["note"]["thread"] = "Auto-Expanded"
                if "note" in alert and "read_history" in alert["note"]:
                    u = []
                    for rh in list(alert["note"]["read_history"].keys()):
                        u.append(f"{rh}{arh_sep}{alert['note']['read_history'][rh]}")
                    alert["note"]["read_history"] = ";".join(u)
                if "note" in alert and "note" in alert["note"]:
                    try:
                        parsed = json.loads(re.sub("'", "\"", alert["note"]["note"]))
                        alert["note"]["message"] = ';'.join([p["children"][0]["text"] for p in parsed])
                    except Exception as e:
                        alert["note"]["message"] = alert["note"]["note"]
                        self._log.info(f'action=parse_note_message alert="{alert["note"]["note"]}" exception="{e}"')
                a, f = flatten(alert, sep)
                [fields.append(fs) for fs in f]
                results.append(a)
            unique_fields = list(self.uniq(fields))
            if len(results) > 0:
                r = results[0]
                for field in unique_fields:
                    if field not in r:
                        r[field] = ""
                results[0] = r
            self._log.info("alert_id={} org_key={} unique_fields={}".format(alert_id, org_key, unique_fields))
            return results
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
            self._log.warn(
                "action=exception alert_id={} {}".format(alert_id, error_msg))
            return {"internal_exception": "{}".format(e)}

    @staticmethod
    def uniq(lst):
        last = []
        for item in lst:
            if item in last:
                continue
            yield item
            last.append(item)

    def get_alert_observations(self, alert_id, org_key):
        try:
            c = None
            if self._use_multi_tenant:
                self._log.info(
                    "action=selecting_cb org_key={}".format(org_key))
                c = self.multi_tenant_apis[org_key]["cb"]
            else:
                self._log.info("action=selected_single_cb")
                c = self.cb
            obs_details = EnrichedEventObservationJson.bulk_get_details(c, alert_id=alert_id)
            if obs_details is None:
                obs_details = []
            self._log.info("alert_id={} org_key={} details_length={}".format(alert_id, org_key, len(obs_details)))
            return [EnrichedEventObservationJson.json(obs) for obs in obs_details]
        except Exception as e:
            self._log.warn(
                "action=exception alert_id={} exception={}".format(alert_id, e))
            return {"internal_exception": "{}".format(e)}

    def get_device(self, dvc_name, org_key):
        try:
            c = None
            if self._use_multi_tenant:
                self._log.info(
                    "action=selecting_cb org_key={}".format(org_key))
                c = self.multi_tenant_apis[org_key]["cb"]
            else:
                self._log.info("action=selected_single_cb")
                c = self.cb
            dvc = c.select(Device, dvc_name)
            dvc.refresh()
            self._log.info("dvc_name={} org_key={}".format(dvc_name, org_key))
            dvc._info["internal_exception"] = "none"
            return dvc._info
        except Exception as e:
            self._log.warn(
                "action=exception device_id={} exception={}".format(dvc_name, e))
            return {"internal_exception": "{}".format(e)}

    def get_hash_device(self, hash_value, org_key):
        try:
            c = None
            if self._use_multi_tenant:
                self._log.info(
                    "action=selecting_cb org_key={}".format(org_key))
                c = self.multi_tenant_apis[org_key]["cb"]
            else:
                self._log.info("action=selected_single_cb")
                c = self.cb
            hash_object = c.select(SplunkCBCTHBinary, hash_value)
            self._log.info("action=hash_object hash_object={} org_key={}".format(
                hash_object.summary, org_key))
            summ = hash_object.summary
            summ["internal_exception"] = "none"
            return summ
        except Exception as e:
            self._log.warn(
                "action=exception device_id={} exception={}".format(hash_value, e))
            return {"internal_exception": "{}".format(e)}

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
        iLog.error(error_msg)

    def setup_proxy(self, proxy_guid):
        try:
            invalid_proxies = ["NOPROXYSELECTED", "NONE"]
            self._log.debug(
                "action=checking_for_proxy guid={} upper={} invalid_proxies={}".format(proxy_guid, f"{proxy_guid}".upper(), invalid_proxies))
            verify_ssl = True
            proxy_string = None
            if proxy_guid and f"{proxy_guid}".upper() not in invalid_proxies:
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
