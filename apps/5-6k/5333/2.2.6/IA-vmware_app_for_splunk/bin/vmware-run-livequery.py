# - Run Livequery
#     - `Documentation <https://developer.carbonblack.com/reference/carbon-black-cloud/cb-liveops/latest/livequery-api/#start-query-run>`_
#     - Credential Type: Custom
#     - Global Configuration
#         - API Config: Supports multi-tenancy.
#             - To use multi-tenancy, include the ``org_key`` field with the corresponding value.
#         - Select the API Configs to use with this alert action.
#         - Only 1 API Config per Organization Key should be configured for each alert action.
#     - Search Configuration
#         - Livequery Name: the name that should be used for the Livequery.
#         - SQL Query: the field name that contains the SQL query that will be submitted.
#         - Device IDs: the field name that contains the device IDs that the query will be run against.
#         - Policy Name: the field name that contains the policy that the query will be run agains.
import sys
import os
import json
import logging
import csv
from VMWUtilities import KennyLoggins
from vmware_cbc_alert_actions import VmwareCBCAlertAction
from datetime import datetime
import multiprocessing.dummy as mp
from pathlib import Path
import vmware_paths
from cbc_sdk.audit_remediation import Run
from cbc_sdk.platform import Device

_alert_name = Path(__file__).stem
__app_name__ = vmware_paths.__app_name__
kl = KennyLoggins()
logger = kl.get_logger(
    app_name=__app_name__, file_name=_alert_name, log_level=logging.INFO
)


class VmwareRunLiveQuery(VmwareCBCAlertAction):
    def __init__(self, settings, action_name):
        try:
            VmwareCBCAlertAction.__init__(
                self,
                settings=settings,
                action_name=_alert_name,
                filename=_alert_name,
                stanza="global_{}_configuration".format(_alert_name),
            )
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error_msg = (
                'error_message="{}" '
                'error_type="{}" '
                'error_arguments="{}" '
                'error_filename="{}" '
                'error_line_number="{}" '
                'alert_name="{}" '.format(
                    str(e),
                    type(e),
                    "{}".format(e),
                    fname,
                    exc_tb.tb_lineno,
                    _alert_name,
                )
            )
            logger.fatal(error_msg)

    def main(self):
        try:
            self._log.debug("action=start")
            with self._load_results("rt") as fh:
                self._log.debug("file_handler={}".format(fh))
                p = mp.Pool(10)

                def process_query_results(query_result, processed_ids=None):
                    if processed_ids is None:
                        processed_ids = []
                    for key, value in enumerate(query_result):
                        livequery = value.get("_info", "{}")
                        found_id = False
                        for i in processed_ids:
                            if i == livequery["device"]["id"]:
                                found_id = True

                        if not found_id:
                            processed_ids.append(livequery["device"]["id"])
                            self._log.debug(
                                "action=process result, msg=add event to splunk, id: {}".format(
                                    livequery["device"]["id"]
                                )
                            )
                            self._log.debug(
                                "added livequery result: {}".format(livequery)
                            )
                            self.addevent(
                                json.dumps(livequery),
                                sourcetype="vmware:alert_action:{}:result".format(
                                    _alert_name
                                ),
                            )

                    return processed_ids

                def do_threaded_result(num, result):
                    try:
                        self._log.debug(
                            "processing result number result={}".format(num)
                        )
                        result.setdefault("rid", str(num))
                        for key in ["host", "sourcetype", "source", "index", "sid"]:
                            if key in result:
                                result["orig_{}".format(key)] = result[key]
                                del result[key]
                        delete_result_keys = [key for key in result if "_mv" in key]
                        for key in delete_result_keys:
                            del result[key]
                        self._log.debug(
                            "action=getting query fields from configuration result={}".format(
                                num
                            )
                        )
                        config_livequery_name = self._configuration.get(
                            "livequery_name", None
                        )
                        config_sql_query = result.get(
                            self._configuration.get("sql_query", None), None
                        )
                        config_device_ids = result.get(
                            self._configuration.get("device_ids", None), None
                        )
                        config_device_os = result.get(
                            self._configuration.get("device_os", None), None
                        )
                        config_policy_name = result.get(
                            self._configuration.get("policy_name", None), None
                        )
                        self._log.debug(
                            "livequery name: {}, device_ids: {}, device_os: {}, policy_name: {}".format(
                                config_livequery_name,
                                config_device_ids,
                                config_device_os,
                                config_policy_name,
                            )
                        )
                        self._log.debug("sql query: {}".format(config_sql_query))

                        tmp_device_ids = []
                        tmp_policy_ids = []
                        tmp_device_os = []

                        self._log.info("action=validating configuration values")
                        if config_livequery_name is None:
                            msg = "action=validating configuration values, msg=LiveQuery name is not specified, defaulting to vmware_app_livequery"
                            self._log.warn(msg)
                            self._log.debug(
                                "{}".format(json.dumps(self._configuration))
                            )
                            self.addevent(
                                msg, "vmware:alert_action{}:error".format(_alert_name)
                            )
                            config_livequery_name = "vmware_app_livequery"

                        if config_device_ids is None:
                            tmp_device_ids = []
                        else:
                            tmp_split_deviceids = config_device_ids.split(",")
                            for deviceid in tmp_split_deviceids:
                                chk_is_int_device_id = deviceid.isdigit()
                                if chk_is_int_device_id:
                                    tmp_device_ids.append(int(deviceid))
                                else:
                                    if deviceid != "*":
                                        found_slash = deviceid.find("\\")
                                        if found_slash != -1:
                                            hostname = 'name:{}"'.format(
                                                deviceid[:found_slash]
                                                + "\\"
                                                + deviceid[found_slash:]
                                                + '"'
                                            )
                                        else:
                                            hostname = "name:{}".format(deviceid)
                                        try:
                                            self._log.debug(
                                                "action=get device information, device: {}, hostname: {}".format(
                                                    deviceid, hostname
                                                )
                                            )
                                            device = None
                                            if (
                                                result.get("org_key", None) is not None
                                                and self._use_multi_tenant
                                            ):
                                                org_key = result.get("org_key")
                                                self._log.debug(
                                                    "action=multi_tenant_api_usage org_key={}".format(
                                                        org_key
                                                    )
                                                )
                                                tmp_device_list = (
                                                    self.multi_tenant_apis[org_key][
                                                        "cb"
                                                    ]
                                                    .select(Device)
                                                    .where(hostname)
                                                    .first()
                                                )
                                                device = tmp_device_list.where(
                                                    hostname
                                                ).first()
                                            else:
                                                self._log.debug(
                                                    "hostname: {}, device_id: {}".format(
                                                        hostname, deviceid
                                                    )
                                                )
                                                tmp_device_list = self.cb.select(Device)
                                                device = tmp_device_list.where(
                                                    hostname
                                                ).first()

                                            if device is not None:
                                                self._log.info(
                                                    "device={}, type_of_device={}, len(device):{}".format(
                                                        device,
                                                        type(device),
                                                        len(tmp_device_list),
                                                    )
                                                )
                                                tmp_device = device.get("_info", "{}")
                                                self._log.debug(
                                                    "tmp_device_id: {}, tmp_device: {}, type tmp_device: {}".format(
                                                        tmp_device["id"],
                                                        tmp_device,
                                                        type(tmp_device),
                                                    )
                                                )
                                                tmp_device_ids.append(
                                                    int(tmp_device["id"])
                                                )

                                                self._log.debug(
                                                    "device_id_list: {}".format(
                                                        tmp_device_ids
                                                    )
                                                )
                                            else:
                                                msg = "action=retrieving device info for device name, msg=no device found for device: {}, will not continue".format(
                                                    deviceid
                                                )
                                                self._log.warn(msg)
                                                self._log.debug(
                                                    "{}".format(
                                                        json.dumps(self._configuration)
                                                    )
                                                )
                                                self.addevent(
                                                    msg,
                                                    "vmware:alert_action{}:error".format(
                                                        _alert_name
                                                    ),
                                                )
                                                continue
                                        except Exception as te:
                                            exc_type, exc_obj, exc_tb = sys.exc_info()
                                            fname = os.path.split(
                                                exc_tb.tb_frame.f_code.co_filename
                                            )[1]
                                            self._log.error(
                                                "function=main action=fatal_error exception_line={} exception_file={}  message={}".format(
                                                    exc_tb.tb_lineno, fname, te
                                                )
                                            )

                        if config_device_os is None:
                            tmp_device_os = []
                        else:
                            if config_device_os == "ALL":
                                tmp_device_os = ["WINDOWS", "MAC", "LINUX"]
                            else:
                                tmp_split_deviceos = config_device_os.split(",")
                                for deviceos in tmp_split_deviceos:
                                    tmp_device_os.append(deviceos)

                        if config_policy_name is None:
                            tmp_policy_ids = []
                        else:
                            tmp_split_policy_ids = config_policy_name.split(",")
                            for policyid in tmp_split_policy_ids:
                                tmp_policy_ids.append(int(policyid))

                        if config_sql_query is not None:
                            try:
                                tmp_ttl_start = datetime.now()
                                self._log.info(
                                    "action=submit livequery name: {}, TTL start time: {}".format(
                                        config_livequery_name, tmp_ttl_start
                                    )
                                )
                                self._log.debug(
                                    "device_ids: {}, policy_id: {}, device_os: {}".format(
                                        tmp_device_ids, tmp_policy_ids, tmp_device_os
                                    )
                                )
                                if (
                                    result.get("org_key", None) is not None
                                    and self._use_multi_tenant
                                ):
                                    org_key = result.get("org_key")
                                    self._log.debug(
                                        "action=multi_tenant_api_usage org_key={}".format(
                                            org_key
                                        )
                                    )
                                    #
                                    # There appears to be an issue with empty policy_id values when using the SDK
                                    #
                                    if config_policy_name is None:
                                        livequery_run = (
                                            self.multi_tenant_apis[org_key]["cb"]
                                            .select(Run)
                                            .where(config_sql_query)
                                            .name(config_livequery_name)
                                            .device_ids(tmp_device_ids)
                                            .device_types(tmp_device_os)
                                            .submit()
                                        )
                                    else:
                                        livequery_run = (
                                            self.multi_tenant_apis[org_key]["cb"]
                                            .select(Run)
                                            .where(config_sql_query)
                                            .name(config_livequery_name)
                                            .device_ids(tmp_device_ids)
                                            .policy_id(tmp_policy_ids)
                                            .device_types(tmp_device_os)
                                            .submit()
                                        )
                                else:
                                    if config_policy_name is None:
                                        livequery_run = (
                                            self.cb.select(Run)
                                            .where(config_sql_query)
                                            .name(config_livequery_name)
                                            .device_ids(tmp_device_ids)
                                            .device_types(tmp_device_os)
                                            .submit()
                                        )
                                    else:
                                        livequery_run = (
                                            self.cb.select(Run)
                                            .where(config_sql_query)
                                            .name(config_livequery_name)
                                            .device_ids(tmp_device_ids)
                                            .policy_id(tmp_policy_ids)
                                            .device_types(tmp_device_os)
                                            .submit()
                                        )

                                tmp_livequery_run_id = livequery_run.id
                                tmp_livequery_run_status = livequery_run.status
                                tmp_active_org_devices = (
                                    livequery_run.active_org_devices
                                )

                                livequery_event = livequery_run.get("_info", "{}")
                                self._log.info(
                                    "action=submitted_livequery id={}, active_org_devices: {}".format(
                                        livequery_run.get("_info", {}).get("id", "N/A"),
                                        tmp_active_org_devices,
                                    )
                                )
                                self.addevent(
                                    json.dumps(livequery_event),
                                    sourcetype="vmware:alert_action:{}".format(
                                        _alert_name
                                    ),
                                )

                                # livequery_result = None
                                # livequery_results = self.cb.select(Result) \
                                #    .run_id(tmp_livequery_run_id)

                                # livequery_result = livequery_results.all()
                                # self._log.debug("livequery_result: {}, type: {}".format(livequery_result, type(livequery_result)))

                                # processed_ids = []

                                # while tmp_livequery_run_status == 'ACTIVE':
                                #    tmp_livequery_history = self.cb.select(RunHistory)
                                #    for history_rec in tmp_livequery_history:
                                #        self._log.debug("action=loop through run history, history_rec.id {}, history_rec.status: {}, livequery_run_id: {}".format(history_rec.id, history_rec.status, tmp_livequery_run_id))
                                #        if history_rec.id in tmp_livequery_run_id:
                                #            tmp_livequery_run_status = history_rec.status
                                #            self._log.debug("action=check livequery run status: {}".format(tmp_livequery_run_status))
                                #            break

                                #    livequery_results = self.cb.select(Result) \
                                #        .run_id(tmp_livequery_run_id)

                                #    livequery_result = livequery_results.all()
                                #    processed_ids = process_query_results(livequery_result, processed_ids)

                                #    tmp_ttl_end = datetime.now()
                                #    time_difference = tmp_ttl_end - tmp_ttl_start
                                #    total_seconds = time_difference.total_seconds()
                                #    self._log.debug("action=check for long running queries, msg: ttl={}, tmp_ttl_start: {}, tmp_ttl_end: {}, total_seconds: {}".format(config_ttl, tmp_ttl_start, tmp_ttl_end, total_seconds))
                                # if int(total_seconds) > int(config_ttl):
                                #     self._log.info("action=Run time exceeds ttl so kill job - id: {}".format(tmp_livequery_run_id))
                                #    livequery_run.stop()
                                #    break

                                #    self._log.debug("sleep for 15 seconds...whew am I tired")
                                #    time.sleep(15)

                                # self._log.debug("livequery_run_status: {}".format(tmp_livequery_run_status))
                                # tmp_livequery_results = livequery_results.all()
                                # processed_ids = process_query_results(tmp_livequery_results, processed_ids)

                                # self._log.info("action=livequery processing complete, id: {}".format(tmp_livequery_run_id))
                            except Exception as te:
                                exc_type, exc_obj, exc_tb = sys.exc_info()
                                fname = os.path.split(
                                    exc_tb.tb_frame.f_code.co_filename
                                )[1]
                                self._log.error(
                                    "function=main action=fatal_error exception_line={} exception_file={}  message={}".format(
                                        exc_tb.tb_lineno, fname, te
                                    )
                                )
                                # continue

                        else:
                            self._log.info(
                                "action=submit livequery name: {}, msg=no query specified, skipping run".format(
                                    config_livequery_name
                                )
                            )

                    except Exception as lre:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                        self._log.error(
                            "function=main action=fatal_error exception_line={} exception_file={}  message={}".format(
                                exc_tb.tb_lineno, fname, lre
                            )
                        )

                matrix = [
                    (num, result) for num, result in enumerate(csv.DictReader(fh))
                ]
                p.starmap(do_threaded_result, matrix)
                p.close()
                p.join()

        except Exception as me:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error_msg = (
                " "
                'error_message="{}" '
                'error_type="{}" '
                'error_arguments="{}" '
                'error_filename="{}" '
                'error_line_number="{}" '
                'alert_name="{}" '.format(
                    str(me),
                    type(me),
                    "{}".format(me),
                    fname,
                    exc_tb.tb_lineno,
                    self._action_name,
                )
            )
            self._log.error(error_msg)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        logger.fatal("FATAL Unsupported execution mode (expected --execute flag)")
        sys.exit(1)
    modaction = None
    try:
        logger.info("instantiating {}".format(_alert_name))
        modaction = VmwareRunLiveQuery(sys.stdin.read(), action_name=_alert_name)
        modaction.main()
        sc, evttype = modaction.get_evtidx("vmware_cbc_action_index")
        logger.info(
            'action=found_eventtype class=alert_action_index alert_action_index="{}"'.format(
                evttype
            )
        )
        modaction.writeevents(
            index=evttype,
            fext="vmware_cbc_alert_action_st",
            sourcetype="vmware:alert_action:{}".format(_alert_name),
            source="vmware:alert_action:{}:{}".format(
                _alert_name, modaction.payload["search_name"].replace(" ", "_")
            ),
        )
    except Exception as e:
        try:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error_msg = (
                " "
                'error_message="{}" '
                'error_type="{}" '
                'error_arguments="{}" '
                'error_filename="{}" '
                'error_line_number="{}" '
                'alert_name="{}" '.format(
                    str(e),
                    type(e),
                    "{}".format(e),
                    fname,
                    exc_tb.tb_lineno,
                    _alert_name,
                )
            )
            logger.error(error_msg)
        except Exception as e:
            logger.critical(e)
        sys.exit(3)
