# - Add IOC to watchlist
#     - `Documentation <https://developer.carbonblack.com/reference/carbon-black-cloud/cb-threathunter/latest/watchlist-api/#update-watchlist>`_
#     - Credential Type: Custom
#     - Global Configuration
#         - API Config: Supports multi-tenancy.
#             - To use multi-tenancy, include the ``org_key`` field with the corresponding value.
#         - Select the API Configs to use with this alert action.
#         - Only 1 API Config per Organization Key should be configured for each alert action.
#     - Search Configuration
#         - Watchlist: The name of the watchlist.
#             - Will match exactly.
#             - If the watchlist doesn't exist, it will be created.
#             - Can be overridden with a field value in the results. Fieldname: ``watchlist``.
#         - Report Name: The name of the report on the watchlist.
#             - Will match exactly.
#             - If the report doesn't exist, it will be created.
#             - Can be overridden with a field value in the results. Fieldname: ``report_name``.
#         - IOC Field: The field name in the results that contains the IOC to add to the watchlist report.
#         - Severity: The severity to assign to the alert action report IOC.
#             - Can be overridden with a field value in the results. Fieldname: ``severity``.
import sys
import os
import re
import json
import logging
import csv
import uuid
from VMWUtilities import KennyLoggins, Utilities
from vmware_cbc_alert_actions import VmwareCBCAlertAction
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from cbc_sdk.enterprise_edr import Report, Watchlist
from datetime import datetime
import multiprocessing.dummy as mp
from pathlib import Path
import vmware_paths
__app_name__ = vmware_paths.__app_name__

_alert_name = Path(__file__).stem
kl = KennyLoggins()
logger = kl.get_logger(app_name=__app_name__, file_name=_alert_name, log_level=logging.INFO)


class VmwareAddIocWatchlist(VmwareCBCAlertAction):
    def __init__(self, settings, action_name):
        try:
            VmwareCBCAlertAction.__init__(self, settings=settings, action_name=_alert_name,
                                          filename=_alert_name,
                                          stanza="global_{}_configuration".format(_alert_name))
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error_msg = "error_message=\"{}\" " \
                        "error_type=\"{}\" " \
                        "error_arguments=\"{}\" " \
                        "error_filename=\"{}\" " \
                        "error_line_number=\"{}\" " \
                        "alert_name=\"{}\" " \
                .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno, _alert_name)
            logger.fatal(error_msg)

    def threaded_function(self, num, result):
        try:
            self._log.debug("processing result number result={}".format(num))
            result.setdefault('rid', str(num))
            for key in ["host", "sourcetype", "source", "index", "sid"]:
                if key in result:
                    result["orig_{}".format(key)] = result[key]
                    del result[key]
            delete_result_keys = [key for key in result if '_mv' in key]
            for key in delete_result_keys:
                del result[key]
            self._log.debug("action=getting watchlist field result={}".format(num))
            watchlist_name = self._configuration.get("watchlist", None)
            report_name = self._configuration.get("report_name", None)
            ioc = self._configuration.get("ioc_field", None)
            ioc_type = self._configuration.get("ioc_type", "equality")
            severity = self._configuration.get("severity_field", "5")
            ioc_field_map = {
                "src": "device_name",
                "src_ip": "netconn_ipv4",
                "src_port": "netconn_port",
                "dest": "device_name",
                "dest_ip": "netconn_ipv4",
                "dest_port": "netconn_port",
                "domain": "netconn_domain",
                "os": "device_os",
                "process": "process_name",
                "process_name": "process_name",
                "process_hash": "process_hash",
                "hash": "hash",
                "user": "process_username"
            }
            # self._log.debug("ioc: {}, result[ioc_field]: {}".format(ioc, result[ioc]))
            self._log.debug("action=checking fields result={} watchlist={} report_name={} ioc={} ioc_type={} severity={}".format(num,
                                                                                                              watchlist_name,
                                                                                                              report_name,
                                                                                                              ioc,
                                                                                                              ioc_type,
                                                                                                              severity))
            if watchlist_name is None:
                msg = "action=cannot_complete_action watchlist={} watchlist_field={} ".format(
                    watchlist_name, self._configuration.get("watchlist", None))
                self._log.warn(msg)
                self._log.debug("{}".format(json.dumps(self._configuration)))
                self.addevent(msg, "vmware:alert_action:{}:error".format(_alert_name))
                return

            if report_name is None:
                msg = "action=cannot_complete_action report_name={} report_name_field={} ".format(
                    report_name, self._configuration.get("report_name", None))
                self._log.warn(msg)
                self._log.debug("{}".format(json.dumps(self._configuration)))
                self.addevent(msg, "vmware:alert_action:{}:error".format(_alert_name))
                return

            if ioc is None:
                msg = "action=cannot_complete_action ioc={} ioc_field={} ".format(
                    ioc, self._configuration.get("ioc_field", None))
                self._log.warn(msg)
                self._log.debug("{}".format(json.dumps(self._configuration)))
                self.addevent(msg, "vmware:alert_action:{}:error".format(_alert_name))
                return

            ioc_field_map_splunk = list(ioc_field_map.keys())
            ioc_field_map_cb = list(ioc_field_map.values())

            if ioc_type == 'equality':
                self._log.debug("ioc_type = equality")
                if ioc not in ioc_field_map_splunk:
                    self._log.warn("action=equality ioc type checking for valid ioc field. msg=invalid field specified as ioc field. {}".format(ioc))
                    return
                else:
                    query_ioc_value = result.get(ioc, "")
                    ioc_field = ioc_field_map[ioc]
                    self._log.debug("action=found match between ioc field and ioc field map for equality object, ioc_field: {}, query_ioc_value: {}".format(ioc_field, query_ioc_value))
            elif ioc_type == 'query':
                self._log.debug("action=check format of query, msg=ioc_query: {}".format(ioc))
                pattern_match = re.search(r'(?P<query_ioc_field>[^:]*):(?P<query_ioc_value>[^\r\n]*)', ioc)
                if pattern_match:
                    query_ioc_field = pattern_match.group('query_ioc_field')
                    query_ioc_value = pattern_match.group('query_ioc_value')
                    if query_ioc_field not in ioc_field_map_splunk:
                        self._log.warn("action=query ioc type checking for valid ioc field. msg=invalid field specified as ioc field in query. {}".format(query_ioc_field))
                        return
                    else:
                        ioc_field = ioc_field_map[query_ioc_field]
                        self._log.debug("action=found match between ioc field and ioc field map, query_ioc_field for query object: {}, ioc_field: {}, query_ioc_value: {}".format(query_ioc_field, ioc_field, query_ioc_value))
                else:
                    self._log.warn("action=check format of query, msg-result was invalid query, query format should follow fieldname:value format")
                    return
            else:
                self._log.warn("action=check query type...ioc_type is not query or equality")
                return

            # Where can be one of: ip, hostname, groupid
            try:
                self._log.info("action=getting_watchlist watchlist_name={}".format(watchlist_name))
                local_cb_api = None
                if result.get("org_key", None) is not None and self._use_multi_tenant:
                    org_key = result.get("org_key")
                    self._log.debug("action=multi_tenant_api_usage org_key={}".format(org_key))
                    local_cb_api = self.multi_tenant_apis[org_key]["cb"]
                else:
                    local_cb_api = self.cb
                if result.get("watchlist", None) is not None:
                    watchlist_name = result.get("watchlist")
                select_watchlist_name = "name:{}".format(watchlist_name)
                watchlist = local_cb_api.select(Watchlist).where(select_watchlist_name).results
                if watchlist is None:
                    result["alert_action_exception"] = "watchlist_not_found"
                    self.addevent(json.dumps(dict(result)),
                                  sourcetype="vmware:alert_action:{}".format(_alert_name))
                    self._log.warn("action=cannot_get_watchlist watchlist={}".format(watchlist_name))
                    # return

                watchlist_matches = [result for result in watchlist if result.name == watchlist_name]
                self._log.debug("action=list watchlist matches, Watchlist matches: {}".format(watchlist_matches))

                if not watchlist_matches:
                    self._log.debug("action=create_new_watchlist, watchlist={}".format(watchlist_name))
                    self._create_watchlist(local_cb_api, Watchlist, watchlist_name)
                    watchlist = local_cb_api.select(Watchlist).where(select_watchlist_name).results
                    watchlist_matches = [result for result in watchlist if result.name == watchlist_name]
                    # return

                # We are picking the first found match, since it is an exact matcher in the logic. Should only be one, ever.
                local_watchlist = watchlist_matches[0]
                reports = list(local_watchlist.reports)
                self._log.debug("action=get_reports length={}".format(len(list(reports))))
                if result.get("report_name", None) is not None:
                    report_name = result.get("report_name")
                report_matches = [x for x in reports if x.title == report_name]
                if len(reports) < 1 or len(report_matches) < 1:
                    self._log.info("action=no_reports watchlist_name={}".format(watchlist_name))
                    now_now = int(datetime.now().strftime("%s"))
                    descr = "AutoGenerated from Splunk Search: '{}'".format(
                        self._settings.get("search_name", "unknown"))
                    uu = uuid.uuid4()
                    report_id = "splunk-ar-{}".format(uu)
                    report_dict = {
                        "title": report_name,
                        "timestamp": now_now,
                        "description": descr,
                        "severity": severity,
                        "id": report_id}
                    if ioc_type == 'equality':
                        report_dict["iocs_v2"] = [{
                                        "values": [result.get(ioc, "")],
                                        "id": "{}".format(uuid.uuid4()),
                                        "match_type": result.get(ioc_type, "equality"),
                                        "field": ioc_field
                                    }]
                    elif ioc_type == 'query':
                        report_dict["iocs_v2"] = [{
                            "values": ["({}:{})".format(ioc_field, query_ioc_value)],
                                "id": "{}".format(uuid.uuid4()),
                                "match_type": ioc_type,
                                "field": None
                            }]
                    self._log.debug("action=creating_report dict={}".format(report_dict))
                    new_report = local_cb_api.create(Report, report_dict)
                    self._log.debug("action=saving_watchlist_report result={}".format(new_report.save_watchlist()))
                    temp_id = local_watchlist.report_ids
                    temp_id.append(new_report.id)
                    self._log.debug("action=updating_whitelist new_report_ids={}".format(temp_id))
                    local_watchlist.update(report_ids=temp_id)

                    tioc = report_dict['iocs_v2']
                    add_ioc_update_event = {}
                    add_ioc_update_event['description'] = "Created by alert action: {}".format(_alert_name)
                    add_ioc_update_event['watchlist_name'] = watchlist_name
                    add_ioc_update_event['report_name'] = report_name
                    add_ioc_update_event['ioc_type'] = tioc[0]['match_type']
                    add_ioc_update_event['ioc_field'] = tioc[0]['field']
                    add_ioc_update_event['ioc_values'] = tioc[0]['values']
                    add_ioc_update_event['updated_timestamp'] = datetime.utcnow().isoformat()
                    add_ioc_update_event['updated_timestamp'] = datetime.utcnow().isoformat()
                    self.addevent(json.dumps(add_ioc_update_event),
                                  sourcetype="vmware:alert_action:{}".format(_alert_name))

                    self._log.debug("action=create_watchlist reports={}".format(local_watchlist.reports))
                    return

                self._log.debug("action=found_matching_report report={}".format(report_matches))
                #
                # Watchlist exists with matching report
                #
                local_report = report_matches[0]
                if local_report:
                    self._log.debug("action=append ioc to ioc list for watchlist: {}, report: {}, ioc: {}".format(
                        watchlist_name, local_report.title, ioc))
                    has_matching_ioc = False
                    has_matching_value = False
                    for ioc2 in local_report.iocs_v2:
                        has_matching_value = False
                        self._log.debug("action=ioc_check ioc={}".format(ioc2))
                        for ioc2v in ioc2["values"]:
                            self._log.debug("action=ioc_value_check value={} check={}".format(ioc2v, result.get(ioc, "")))
                            if ioc2v == result.get(ioc, "") or ioc2v == "({}:{})".format(ioc_field, query_ioc_value):
                                self._log.debug("action=ioc_value_check result=found_matching")
                                has_matching_ioc = True
                                has_matching_value = True

                    self._log.debug("action=ioc_check matching_ioc={} matching_value={}".format(has_matching_ioc, has_matching_value))
                    if not has_matching_ioc:
                        tioc = local_report.iocs_v2
                        self._log.debug("tioc before update: {}, type: {}".format(tioc, type(tioc)))
                        if ioc_type == 'query':
                            self._log.debug("query local_report: {}".format(local_report))
                            tioc.append({
                                "values": ["({}:{})".format(ioc_field, query_ioc_value)],
                                "id": "{}".format(uuid.uuid4()),
                                "match_type": "query",
                                "field": None
                            })
                        else:
                            self._log.debug("equality local_report: {}".format(local_report))
                            tioc.append({
                                "values": [result.get(ioc, "")],
                                "id": "{}".format(uuid.uuid4()),
                                "match_type": result.get(ioc_type, "equality"),
                                "field": ioc_field
                            })
                        self._log.debug("action=updating_report iocs={}, type: {}".format(json.dumps(tioc), type(tioc)))
                        local_report.iocs_v2 = json.dumps(tioc)
                        self._log.debug("action=updating_report report={}, type: {}".format(local_report, type(local_report)))
                        local_report.update(iocs_v2=tioc)
                        # local_report.update()

                        add_ioc_update_event = {}
                        add_ioc_update_event['description'] = "Created by alert action: {}".format(_alert_name)
                        add_ioc_update_event['watchlist_name'] = watchlist_name
                        add_ioc_update_event['report_name'] = report_name
                        add_ioc_update_event['ioc_type'] = tioc[0]['match_type']
                        add_ioc_update_event['ioc_field'] = tioc[0]['field']
                        add_ioc_update_event['ioc_values'] = tioc[0]['values']
                        add_ioc_update_event['updated_timestamp'] = datetime.utcnow().isoformat()
                        self.addevent(json.dumps(add_ioc_update_event),
                                      sourcetype="vmware:alert_action:{}".format(_alert_name))

                        return
                    else:
                        self._log.debug("action=found_ioc result=skip")
                        return

            except Exception as lre:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                self._log.error(
                    "function=main action=fatal_error exception_line={} exception_file={}  message={}".format(
                        exc_tb.tb_lineno,
                        fname, lre))
        except TypeError as te:
            result["alert_action_exception"] = "watchlist_not_found"
            self.addevent(json.dumps(dict(result)),
                          sourcetype="vmware:alert_action:{}".format(_alert_name))
            self._log.warn("action=cannot_get_watchlist watchlist_name={} type_e={}".format(watchlist_name,
                                                                                            type(te)))
            return

    def main(self):
        try:
            self._log.debug("action=start configuration={}".format(self.configuration))
            self._log.debug("cb object: {}".format(self.cb))
            with self._load_results("rt") as fh:
                self._log.debug("file_handler={}".format(fh))
                p = mp.Pool(10)
                matrix = [(num, result) for num, result in enumerate(csv.DictReader(fh))]
                p.starmap(self.threaded_function, matrix)
                p.close()
                p.join()
        except Exception as me:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error_msg = " " \
                        "error_message=\"{}\" " \
                        "error_type=\"{}\" " \
                        "error_arguments=\"{}\" " \
                        "error_filename=\"{}\" " \
                        "error_line_number=\"{}\" " \
                        "alert_name=\"{}\" " \
                .format(str(me), type(me), "{}".format(me), fname, exc_tb.tb_lineno, self._action_name)
            self._log.error(error_msg)


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        logger.fatal("FATAL Unsupported execution mode (expected --execute flag)")
        sys.exit(1)
    modaction = None
    try:
        logger.info("instantiating {}".format(_alert_name))
        modaction = VmwareAddIocWatchlist(sys.stdin.read(), action_name=_alert_name)
        modaction.main()
        sc, evttype = modaction.get_evtidx("vmware_cbc_action_index")
        logger.info("action=found_eventtype class=alert_action_index alert_action_index=\"{}\"".format(evttype))
        modaction.writeevents(index=evttype, source="vmware:alert_action:{}:{}".format(_alert_name,
                                                                                       modaction.payload[
                                                                                           "search_name"].replace(" ",
                                                                                                                  "_")))
    except Exception as e:
        try:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error_msg = " " \
                        "error_message=\"{}\" " \
                        "error_type=\"{}\" " \
                        "error_arguments=\"{}\" " \
                        "error_filename=\"{}\" " \
                        "error_line_number=\"{}\" " \
                        "alert_name=\"{}\" " \
                .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno, _alert_name)
            logger.error(error_msg)
        except Exception as e:
            logger.critical(e)
        sys.exit(3)
