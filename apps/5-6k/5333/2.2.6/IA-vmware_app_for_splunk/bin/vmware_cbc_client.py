"""
Written by Kyle Smith for Aplura, LLC
Copyright (C) 2016-2024 Aplura, LLC

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
"""
import logging as logger
import re
import sys
import os
import json
import time
import uuid
from datetime import datetime
from VMWUtilities import KennyLoggins
from vmware_cbc_utilities import CBCUtilities
from VMWModularInput import ModularInput
import multiprocessing.dummy as mp
# this is needed for the cbc_sdk imports
import vmware_paths
from cbc_sdk.platform import Alert, AuditLog
from cbc_sdk import CBCloudAPI

__app_name__ = vmware_paths.__app_name__
__version__ = vmware_paths.__app_version__

kl = KennyLoggins()
iLog = kl.get_logger(
    app_name=__app_name__,
    file_name="vmware-instantiation-logger",
    log_level=logger.INFO,
)
cbc_override = kl.get_logger(
    app_name=__app_name__, file_name="cbc_sdk.connection", log_level=logger.INFO
)


class VmwareCBCModularInput(ModularInput):
    def __init__(self, **kwargs):
        ModularInput.__init__(self, **kwargs)
        self.utils = None
        self.cb = None
        self.cb_log = None
        self.tenant = None
        self.credential = None
        self.__app_name__ = __app_name__
        self._execution_run_guid = "{}".format(uuid.uuid4())
        self.tracking_uuid = str(uuid.uuid4())
        self.log_attrs = ["tracking_uuid"]
        self._integer_ipv4_fields = [
            "netconn_remote_ipv4",
            "netconn_proxy_ipv4",
            "netconn_local_ipv4",
            "netconn_ipv4",
            "auth_remote_ipv4",
            "event_network_local_ipv4",
            "event_network_remote_ipv4",
        ]
        self._integer_ipv6_fields = [
            "netconn_remote_ipv6",
            "netconn_proxy_ipv6",
            "netconn_local_ipv6",
            "netconn_ipv6",
            "auth_remote_ipv6",
        ]
        self._integer_detect_fields = ["device_external_ip", "device_internal_ip"]
        self._conversion_ip_fields = (
                self._integer_ipv6_fields
                + self._integer_detect_fields
                + self._integer_ipv4_fields
        )
        self.inform(
            action="instantiation",
            cmd=kwargs.get("name", "generic-input"),
            logger_name=self.log.name,
        )

    def int2ipv4(self, ipnum):
        try:
            # o1 = int(int(ipnum) / 16777216) % 256
            # o2 = int(int(ipnum) / 65536) % 256
            # o3 = int(int(ipnum) / 256) % 256
            # o4 = int(ipnum) % 256
            # str(ipaddress.ip_address(int(ipnum)) DOES NOT WORK FOR NEGATIVES
            l_ipnum = 0
            try:
                l_ipnum = int(ipnum)
            except ValueError as e:
                self.log.warning(f"action=int2ipv4_exception msg=invalid_integer ipnum={ipnum}")
                return ipnum
            self.log.debug(
                f'action="converting_ip", ipnum={ipnum}, type={type(ipnum)} int_ipnum={l_ipnum} type_int_ipnum={type(l_ipnum)}')
            return (
                    str(l_ipnum >> 24 & 255)
                    + "."
                    + str(l_ipnum >> 16 & 255)
                    + "."
                    + str(l_ipnum >> 8 & 255)
                    + "."
                    + str(l_ipnum & 255)
            )
        except Exception as e:
            self.log.error(f"action=int2ipv4_exception ipnum={ipnum} exception={e}")
        return ipnum

    def int2ipv6(self, ipnum):
        try:
            return ":".join([x for x in re.split(r"(.{4})", ipnum) if len(x) > 0])
        except Exception as e:
            self.log.warning(f"action=int2ipv6_exception ipnum={ipnum} exception={e}")

    def int2ip(self, field, ipnum):
        if field in self._integer_ipv4_fields or (
                len(ipnum) < 30 and field in self._integer_detect_fields
        ):
            return f"{field}_str", self.int2ipv4(ipnum)
        elif field in self._integer_ipv6_fields or (
                len(ipnum) > 30 and field in self._integer_detect_fields
        ):
            return f"{field}_str", self.int2ipv6(ipnum)
        else:
            return f"{field}_no_conversion", f"{ipnum}"

    def is_ip(self, field):
        return field in self._conversion_ip_fields

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
        self.log.info(self._build_message(**kwargs))

    def warn(self, **kwargs):
        self.log.warning(self._build_message(**kwargs))

    def dbg(self, **kwargs):
        self.log.debug(self._build_message(**kwargs))

    def error(self, **kwargs):
        self.log.error(self._build_message(**kwargs))

    def _catch_error(self, e):
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
        self.sourcetype("vmware:cbc:error")
        self.print_error("{}".format(error_msg))
        self.print_event("{}".format(error_msg))
        self.sourcetype(oldst)

    def setup_cb(self):
        try:
            self.utils = CBCUtilities(
                app_name=self.__app_name__, session_key=self.get_config("session_key")
            )
            self._config["api_key_secret"] = self.utils.get_credential(
                self.__app_name__, self.get_config("credential_guid")
            )
            self._config["tenant"] = self.utils.get_tenant(
                self.get_config("credential_guid")
            )
            t = self.get_config("tenant")
            self.log.debug(
                "action=checking_for_proxy guid={}".format(
                    self.get_config("proxy_guid")
                )
            )
            verify_ssl = True
            proxy_string = None
            if (
                    self.get_config("proxy_guid")
                    and self.get_config("proxy_guid") != "NOPROXYSELECTED"
            ):
                self.log.info(
                    "action=proxy_found guid={}".format(self.get_config("proxy_guid"))
                )
                proxy = self.utils.get_proxy(self.get_config("proxy_guid"))
                proto = "http"
                self.log.debug(
                    "action=checking_ssl use_ssl={}".format(proxy.get("use_ssl"))
                )
                if proxy.get("use_ssl") == "on":
                    proto = "https"
                proxy_string = "{}://{}".format(proto, proxy["proxy_url"])
                if "proxy_user" in proxy:
                    proxy_string = "{}://{}:{}@{}".format(
                        proto,
                        proxy["proxy_user"],
                        proxy["proxy_pass"],
                        proxy["proxy_url"],
                    )
                if proxy.get("verify_ssl") == "off":
                    verify_ssl = False
                if self.utils.is_cloud():
                    verify_ssl = True
                self.log.debug(
                    "action=proxy_string verify_ssl={} {}".format(
                        verify_ssl, proxy["proxy_url"]
                    )
                )
            self.log.info("action=setting_up_base_api")
            self.cb = CBCloudAPI(
                integration_name="SplunkApp/{}/{} ModularInput/{}".format(
                    self.__app_name__,
                    __version__,
                    self.get_config("name").split(":")[0],
                ),
                url="https://{}".format(t["cbc_env"]),
                org_key="{}".format(t["org_key"]),
                token="{0}/{1}".format(self.get_config("api_key_secret"), t["api_key"]),
                proxy=proxy_string,
                ssl_verify=verify_ssl,
            )
            self.host(t["cbc_env"])
            massive_debug = self.get_config("debug_cbc_sdk")
            self.log.info(
                "action=checking_dark_feature debug_cbc_sdk={}".format(massive_debug)
            )
            # This data *should* show up in $SPLUNK_HOME/var/log/splunk/vmware_app_for_splunk/cbc_sdk.log
            if "{}".format(massive_debug) == "enable":
                self.log.warning(
                    "ENABLING MASSIVE DEBUG DARK FEATURE debug={}".format(massive_debug)
                )
                kl = KennyLoggins()
                self.cb_log = kl.get_logger(self.__app_name__, "cbc_sdk", logger.DEBUG)
                self.cb_log.warn("action=instantiate_cbc_sdk_debugger")
                # index=_internal sourcetype="vmware:cbc:cbc_sdk"
        except Exception as e:
            self._catch_error(e)
            raise e

    def _process_evt_ips(self, alrt):
        self.log.debug(f"sourcetype={self.sourcetype()} keys={list(alrt.keys())}")
        new_alrt = {}
        for k in list(alrt.keys()):
            if k in self._conversion_ip_fields:
                f, v = self.int2ip(k, alrt[k])
                new_alrt[f] = v
            new_alrt[k] = alrt[k]
        return new_alrt

    def _get_alerts_threaded(self, num, x):
        self.log.debug(
            "action=found_alert function=threaded id={}".format(
                x.get("_info", {}).get("id", "N/A")
            )
        )
        alert = self._process_evt_ips(x.get("_info", "{}"))
        self.print_event(json.dumps(alert), time_field="last_update_time")

    def _get_auditlogs_threaded(self, num, x):
        self.log.debug(
            "action=found_auditlogs function=threaded id={}".format(
                x.get("eventId", f"list_item_{num}")
            )
        )
        ad = self._process_evt_ips(x)
        self.print_event(json.dumps(ad), time_field="create_time")

    def _get_vulnerability_threaded(self, num, x):
        self.log.debug(
            "action=found_vulnerability_info function=threaded num={} data={}".format(
                num, list(x.keys())
            )
        )
        x["modular_execution_guid"] = self._execution_run_guid
        self.print_event(json.dumps(x), time_field="time_received")

    def _process_audit_matrix(self, event_data, chkpnt):
        self.log.info("action=process_audit_matrix")

        def fix_time(x, y):
            # et = y["eventTime"]
            # y["eventTime"] = int(str(et)[:10])
            return x, y

        p = mp.Pool(10)
        #
        # Check eventTime against latest checkpoint and if earlier than latest checkpoint the drop event
        #
        new_matrix = []
        for num, result in enumerate(event_data):
            # result = r.to_json()
            self.log.debug(f'action=event_keys keys={",".join(list(result.keys()))}')
            # Removed: 10/18/2024 to support queue based ingest.
            # t = fix_time(num, result)
            # tmp_event_data = t[1]
            # self.log.info(
            #     "chkpnt: {}, matrix tmp_event_data: {}".format(chkpnt, tmp_event_data)
            # )
            # if tmp_event_data["eventTime"] < chkpnt:
            #     self.log.info(
            #         "action=remove tuple: {}, event_data: {}".format(t, tmp_event_data)
            #     )
            #     # matrix.remove(t)
            # else:
            #     self.log.info("eventTime > chkpnt keep event, t:{}".format(t))
            new_matrix.append(fix_time(num, result))

        p.starmap(self._get_auditlogs_threaded, new_matrix)
        p.close()
        p.join()

    @staticmethod
    def logobj(kwargs):
        return " ".join([f'{x}="{kwargs[x]}"' for x in kwargs])

    def get_alerts(self):
        try:
            oldst = self.sourcetype()
            tenant = self.get_config("tenant")
            query = self.get_config("query")
            chkpnt_name = "tnt-{}_org-{}_alerts.txt".format(
                tenant.get("guid"), tenant.get("org_key")
            )
            lb = self.get_config("lookback")
            enrich_events = True if "1" == self.get_config("enrich_events") else False
            self.log.debug(
                "action=evaluating_lookback lookback={} lookback_type={}".format(
                    lb, type(lb)
                )
            )
            self.log.debug(
                "action=evaluating_enrich_events enrich_events={} enrich_events_type={}".format(
                    enrich_events, type(enrich_events)
                )
            )
            if int(lb) > 0:
                self.log.debug(
                    "action=evaluating_lookback new_lookback={}".format(
                        (int(lb) * 1440)
                    )
                )
                self.checkpoint_default_lookback(new_time=(int(lb) * 1440))
            chkpnt = self.get_checkpoint(chkpnt_name)
            self.sourcetype("vmware:cbc:alerts")
            self.log.warning("checkpoint={}".format(chkpnt))
            #
            # 1/21/2021 - Start with an empty alert type list because of DESK-862 bug where alerts aren't ingested
            # if both types are requested but the customer only has Enterprise Standard watchlist events will cause
            # an error
            #
            alert_types = []
            alert_type = self.get_config("alert_type", None)
            severity = self.get_config("severity", 4)
            self.log.debug(
                f"action=checking_alert_type alert_type={alert_type} length={len(alert_type)} "
                f" has_comma={',' in alert_type} "
                f" is_none={alert_type is None} ")
            if alert_type:
                self.log.debug(f"action=set_alert_type is_defined=true alert_type={alert_type}")
                alert_types = alert_type.split(",") if "," in alert_type and len(alert_type) > 0 else [alert_type]
                if alert_type.lower() == "both":
                    alert_types = ['CB_ANALYTICS', 'WATCHLIST']
                if alert_type.lower() == "all":
                    alert_types = []
            # To Get All Alert Types: https://carbon-black-cloud-python-sdk.readthedocs.io/en/latest/alerts/
            self.log.debug(f"action=set_alert_type alert_type={alert_types}")
            # set_create_time(*args, **kwargs)
            start = "{}Z".format(datetime.utcfromtimestamp(chkpnt).isoformat())
            end = "{}Z".format(datetime.utcnow().isoformat())
            self.log.info(
                "action=calling_alerts_endpoint status=start "
                "start={} start_type={} end={} end_type={} "
                "checkpoint={} alert_types={}".format(
                    start, type(start), end, type(end), chkpnt, alert_types
                )
            )
            self.log.debug(
                f"action=setting_cb_select query_set={query is None} query={query} alert_types={alert_types} severity={severity} start={start} end={end}")
            if query is None:
                alerts = (
                    self.cb.select(Alert)
                    .set_minimum_severity(severity)
                    .add_criteria("type", alert_types)
                    .set_time_range("last_update_time", start=start, end=end)
                )
            else:
                alerts = (
                    self.cb.select(Alert)
                    .set_minimum_severity(severity)
                    .add_criteria("type", alert_types)
                    .set_time_range("last_update_time", start=start, end=end)
                    .where(q=query)
                )
            p = mp.Pool(10)
            matrix = [(num, result) for num, result in enumerate(alerts)]
            p.starmap(self._get_alerts_threaded, matrix)
            p.close()
            p.join()
            # TODO: VMW-58
            # p.starmap(self._get_enriched_events, matrix)
            # p.close()
            # p.join()
            self.log.info("action=calling_alerts_endpoint status=end")
            self.sourcetype(oldst)
            if len(alerts) > 0:
                self.log.info(
                    "action=saving_checkpoint alerts_found={}".format(len(alerts))
                )
                self.set_checkpoint(chkpnt_name)
            else:
                self.log.warning(
                    "action=saving_checkpoint "
                    "msg='not saving checkpoint in case there was a communication error' "
                    "start={} alerts_found={}".format(start, len(alerts))
                )
        except Exception as e:
            self._catch_error(e)

    def get_audit(self):
        # TODO: VMW-42
        # https://developer.carbonblack.com/reference/carbon-black-cloud/cb-defense/latest/rest-api/#audit-log-events
        try:
            self.log.info("action=start")

            oldst = self.sourcetype()
            tenant = self.get_config("tenant")
            chkpnt_name = "tnt-{}_org-{}_auditlogs.txt".format(
                tenant.get("guid"), tenant.get("org_key")
            )
            chkpnt = self.get_checkpoint(chkpnt_name)
            self.sourcetype("vmware:cbc:auditlogs")
            self.log.warning("checkpoint={}".format(chkpnt))
            start = "{}Z".format(datetime.utcfromtimestamp(chkpnt).isoformat())
            end = "{}Z".format(datetime.utcnow().isoformat())
            self.log.info(
                "action=calling_get_auditlogs status=start "
                "start={} start_type={} end={} end_type={} "
                "checkpoint={}".format(start, type(start), end, type(end), chkpnt)
            )
            # tmp_audit_logs = self.cb.get_auditlogs()
            # tmp_audit_logs = AuditLog.get_auditlogs(self.cb)
            event_data = []
            for x in AuditLog.get_queued_auditlogs(self.cb):
                try:
                    event_data.append(x if type(x) == "dict" else x.to_json())
                except Exception as e:
                    self.log.warning(f"action=process_audit_log_events x={x} type_x={type(x)} exception={e}")
            # self.log.info(
            #     "tmp_audit_logs_length: {}, type tmp_audit_logs: {}".format(
            #         len(tmp_audit_logs), type(tmp_audit_logs)
            #     )
            # )
            # audit_logs = json.dumps(tmp_audit_logs)
            # self.log.info(
            #     "action=get_audit logs, num events={}, auditlogs_type={}".format(
            #         len(audit_logs), type(audit_logs)
            #     )
            # )

            # event_data = json.loads(audit_logs)
            num_events = len(event_data)
            self.log.info(
                "num events in event_data: {}, type event_data: {}".format(
                    len(event_data), type(event_data)
                )
            )
            self.log.info("event_data: {}".format(event_data))
            self._process_audit_matrix(event_data, chkpnt)
            total_num_results = num_events

            while num_events >= 2500:
                if total_num_results <= 100000:
                    self.log.info(
                        "action=process event_data, num_events>=2500 retrieve more logs"
                    )
                    event_data = []
                    for x in AuditLog.get_queued_auditlogs(self.cb):
                        try:
                            event_data.append(x if type(x) == "dict" else x.to_json())
                        except Exception as e:
                            self.log.warning(f"action=process_audit_log_events x={x} type_x={type(x)} exception={e}")
                    num_events = len(event_data)
                    total_num_results = total_num_results + num_events
                    if num_events > 0:
                        self.log.info(
                            "processing event loop num events in event_data: {}, results processed so far in loop: {}".format(
                                len(event_data), total_num_results
                            )
                        )
                        self._process_audit_matrix(event_data, chkpnt)
                    else:
                        break
                else:
                    break

            self.log.info(
                "action=calling_get_auditlogs status=end, total results: {}".format(
                    total_num_results
                )
            )
            self.sourcetype(oldst)
            if total_num_results > 0:
                self.log.info(
                    "action=saving_checkpoint auditlogs_found={}".format(
                        len(event_data)
                    )
                )
                self.set_checkpoint(chkpnt_name)
            else:
                self.log.warning(
                    "action=saving_checkpoint "
                    "msg='not saving checkpoint in case there was a communication error' "
                    "start={} auditlogs_found={}".format(start, len(event_data))
                )

        except Exception as e:
            self._catch_error(e)
            raise e

    def get_vulnerabilities(self, *args):
        # TODO: This needs updated to use the CBC SDK Objects.
        try:
            self.log.debug("action=start get_vulnerabilities")
            num_rows_to_retrieve = 5000
            pool_thread_count = 25
            tenant = self.get_config("tenant")
            # Interval Check: DESK-1571
            interval = self.get_config("interval")
            if int(interval) and int(interval) < 3600:
                self.log.fatal(f"action=checking_interval_value interval={interval} message=not_valid")
                return
            self.log.warning(f"action=checking_interval_value interval={interval} result=will_continue")
            chkpnt_name = "tnt-{}_org-{}_vulnerabilities.txt".format(
                tenant.get("guid"), tenant.get("org_key")
            )
            chkpnt = self.get_checkpoint(chkpnt_name)
            self.sourcetype("vmware:cbc:vulnerabilities")
            self.log.warning("checkpoint={}".format(chkpnt))
            start = "{}Z".format(datetime.utcfromtimestamp(chkpnt).isoformat())
            end = "{}Z".format(datetime.utcnow().isoformat())
            self.log.info(
                "action=calling_get_vulnerability_summaries status=start "
                "start={} start_type={} end={} end_type={} "
                "checkpoint={}".format(start, type(start), end, type(end), chkpnt)
            )

            try:
                date_format_start = datetime.strptime(start, "%Y-%m-%dT%H:%M:%S.%fZ")
            except ValueError as ve:
                date_format_start = datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ")

            if self.get_config("query") is None:
                query = ""
            else:
                query = self.get_config("query")

            if self.get_config("risk") is None:
                min_risk_level = 0
            else:
                min_risk_level = self.get_config("risk")

            org_key = tenant["org_key"]

            urlobject = "/vulnerability/assessment/api/v1/orgs/{}/vulnerabilities/summary".format(
                org_key
            )
            self.log.debug(
                "org_key={}, query={}, min_risk_level={}, urlobject={}".format(
                    tenant["org_key"], query, min_risk_level, urlobject
                )
            )
            vuln_summary = self._process_evt_ips(self.cb.get_object(urlobject))
            self.log.debug(
                "action=get_vuln_summary vuln_summary={} type_vuln_summary={}".format(
                    vuln_summary, type(vuln_summary)
                )
            )

            self.sourcetype("vmware:cbc:vulnerability:summary")
            self.print_event(json.dumps(vuln_summary), time_field="time_received")

            # self.log.debug("action=set_url_criteria criteria={}".format(
            #     json.loads(json.dumps(urlcriteria))))

            self.sourcetype("vmware:cbc:vulnerability:os:list")
            self.log.info(
                "action=getting_vulnerability_list_for_os_application pooling_thread_count={}".format(
                    pool_thread_count
                )
            )

            urlcriteria = {}
            urlrisk = {"value": int(min_risk_level), "operator": "GREATER_THAN"}
            urlcriteria["risk_meter_score"] = urlrisk
            max_errors_per_page = 5
            sleep_timeout_seconds = 5
            urllist_object = "/vulnerability/assessment/api/v1/orgs/{}/devices/vulnerabilities/_search?dataForExport=true".format(
                org_key
            )

            kill_switch = True

            urlbody = {
                "query": query,
                "rows": num_rows_to_retrieve,
                "start": 0,
                "criteria": urlcriteria,
            }
            vuln_list_os = self.cb.post_object(
                urllist_object, json.loads(json.dumps(urlbody))
            )
            vuln_list_os_data = vuln_list_os.json()
            total_results = vuln_list_os_data["num_found"]
            self.log.debug(
                "action=paginate total_results_first_run={}".format(total_results)
            )
            total_results_retrieved = len(vuln_list_os_data["results"])
            self.log.debug(
                "action=paginate total_results_retrieved={} total_results={} urlbody={}".format(
                    total_results_retrieved, total_results, urlbody
                )
            )
            p = mp.Pool(pool_thread_count)
            matrix = [
                (num, result) for num, result in enumerate(vuln_list_os_data["results"])
            ]
            p.starmap(self._get_vulnerability_threaded, matrix)
            p.close()
            p.join()

            page_number = 1
            error_count = 0
            while total_results_retrieved < total_results and kill_switch:
                self.log.debug(
                    "action=paginate page_number={} error_count={} total_results_retrieved={} total_results={} kill_switch={}".format(
                        page_number,
                        error_count,
                        total_results_retrieved,
                        total_results,
                        kill_switch,
                    )
                )
                try:
                    urlbody = {
                        "query": query,
                        "rows": num_rows_to_retrieve,
                        "start": total_results_retrieved,
                        "criteria": urlcriteria,
                    }
                    self.log.debug(
                        "action=paginate total_results_retrieved={} total_results={} urlbody={}".format(
                            total_results_retrieved, total_results, urlbody
                        )
                    )
                    # self.log.info("urlbody: {}".format(json.loads(json.dumps(urlbody))))
                    vuln_list_os = self.cb.post_object(
                        urllist_object, json.loads(json.dumps(urlbody))
                    )
                    vuln_list_os_data = vuln_list_os.json()
                    self.log.info(
                        "action=paginate results_returned={}".format(
                            len(vuln_list_os_data["results"])
                        )
                    )
                    total_results_retrieved = total_results_retrieved + len(
                        vuln_list_os_data["results"]
                    )

                    p = mp.Pool(pool_thread_count)
                    matrix = [
                        (num, result)
                        for num, result in enumerate(vuln_list_os_data["results"])
                    ]
                    matrix_total_recs = len(matrix)
                    self.log.debug(
                        "action=print_matrix matrix_len={} matrix={} matrix_type={}".format(
                            matrix_total_recs, matrix, type(matrix)
                        )
                    )
                    p.starmap(self._get_vulnerability_threaded, matrix)
                    p.close()
                    p.join()
                    error_count = 0
                    page_number += 1
                except Exception as e:
                    error_count += 1
                    if error_count > max_errors_per_page:
                        kill_switch = False
                        self.log.fatal(
                            "action=kill_switch_invoked error_count={} error={}".format(
                                error_count, e
                            )
                        )
                    self.log.error(
                        "action=paginate error_count={} sleeping_timeout={} error={}".format(
                            error_count, sleep_timeout_seconds, e
                        )
                    )
                    time.sleep(sleep_timeout_seconds)
                self.log.info(
                    "action=paginate total_results_retrieved={} total_results={}".format(
                        total_results_retrieved, total_results
                    )
                )
            self.log.info(
                "action=paginate status=exit_while total_results_retrieved={} total_results={}".format(
                    total_results_retrieved, total_results
                )
            )
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
