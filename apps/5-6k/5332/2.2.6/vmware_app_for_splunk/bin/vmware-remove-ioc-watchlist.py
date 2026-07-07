# - Remove IOC from watchlist
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
#             - Can be overridden with a field value in the results. Fieldname: ``report_name``.
#         - IOC Value Field: The field name in the results that contains the IOC to remove from the watchlist report.
#             - This will be "string match". If the report value is a query, and contains the IOC string, it will be removed.
#             - If the IOC removed was a single IOC on the report, the report also gets removed.
import sys
import os
import json
import logging
import csv
from VMWUtilities import KennyLoggins
from vmware_cbc_alert_actions import VmwareCBCAlertAction
from pathlib import Path
import multiprocessing.dummy as mp
import vmware_paths
from cbc_sdk.enterprise_edr import Watchlist

_alert_name = Path(__file__).stem
__app_name__ = vmware_paths.__app_name__
kl = KennyLoggins()
logger = kl.get_logger(app_name=__app_name__, file_name=_alert_name, log_level=logging.INFO)


class VmwareRemoveIocWatchlist(VmwareCBCAlertAction):
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
            self._log.debug("processing result number result={}".format(num))
            result.setdefault('rid', str(num))
            watchlist_name = self._configuration.get("watchlist", None)
            if watchlist_name is None:
                msg = "action=cannot_complete_action watchlist={} watchlist_field={} ".format(
                    watchlist_name, self._configuration.get("watchlist", None))
                self._log.warn(msg)
                self._log.debug("{}".format(json.dumps(self._configuration)))
                self.addevent(msg, "vmware:alert_action:{}:warn".format(_alert_name))
                return
            self._log.debug("action=get_watchlist watchlist={}".format(watchlist_name))
            report_name = self._configuration.get("report_name", None)
            if report_name is None:
                msg = "action=cannot_complete_action report_name={} report_name_field={} ".format(
                    report_name, self._configuration.get("report_name", None))
                self._log.warn(msg)
                self._log.debug("{}".format(json.dumps(self._configuration)))
                self.addevent(msg, "vmware:alert_action:{}:warn".format(_alert_name))
                return
            self._log.debug("action=get_report_name report_name={}".format(report_name))
            ioc = result.get(self._configuration.get("ioc_field", None), None)
            if ioc is None:
                msg = "action=cannot_complete_action ioc={} ioc_field={} ".format(
                    ioc, self._configuration.get("ioc_field", None))
                self._log.warn(msg)
                self._log.debug("{}".format(json.dumps(self._configuration)))
                self.addevent(msg, "vmware:alert_action:{}:warn".format(_alert_name))
                return
            self._log.debug("checking fields result={} watchlist={} report_name={} ioc_value={}".format(num,
                                                                                                        watchlist_name,
                                                                                                        report_name,
                                                                                                        ioc))

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
                return
            self._log.debug("action=got_watchlist watchlists_found={}".format(len(list(watchlist))))

            watchlist_matches = [result for result in watchlist if result.name == watchlist_name]
            self._log.debug("action=match_watchlist matches={}".format(watchlist_matches))
            if not watchlist_matches:
                self._create_watchlist(local_cb_api, Watchlist, watchlist_name)
            # We are picking the first found match, since it is an exact matcher in the logic. Should only be one, ever.
            local_watchlist = watchlist_matches[0]
            reports = list(local_watchlist.reports)
            self._log.debug("action=get_reports length={}".format(len(list(reports))))
            if len(reports) < 1:
                self._log.warn("action=no_reports watchlist_name={}".format(watchlist_name))
                result["alert_action_exception"] = "no_reports"
                result["watchlist"] = watchlist_name
                result["report_name"] = report_name
                self.addevent(json.dumps(dict(result)),
                              sourcetype="vmware:alert_action:{}".format(_alert_name))
                return
            if result.get("report_name", None) is not None:
                report_name = result.get("report_name")
            report_matches = [x for x in reports if x.title == report_name]
            if len(report_matches) < 1:
                self._log.warn("action=no_matching_reports report_name={}".format(report_name))
                result["alert_action_exception"] = "no_matching_reports"
                result["watchlist"] = watchlist_name
                result["report_name"] = report_name
                self.addevent(json.dumps(dict(result)),
                              sourcetype="vmware:alert_action:{}".format(_alert_name))
                return
            # We are picking the first found match, since it is an exact matcher in the logic. Should only be one, ever.
            local_report = report_matches[0]
            def process_deletion(ri, i):
                self._log.debug("action=delete_ioc ioc={} ri={}".format(i, ri))
                # !!!!! THIS IS WHAT WILL REMOVE THE IOC FROM THE REPORT IT MATCHES ON STRING !!!!!
                if i in "{}".format(ri["values"]):
                    return None
                return ri
            self._log.debug("action=updating_report report_name={} info={} existing_iocs_v2={}".format(
                report_name, local_report._info, local_report.iocs_v2))
            new_iocs = list(filter(None, [process_deletion(x, ioc) for x in local_report.iocs_v2]))
            self._log.debug("action=new_iocs iocs={} next=local_report.update.save".format(new_iocs))
            local_report.update(iocs_v2=new_iocs)
            if len(new_iocs) == 0:
                self._log.debug("action=deleting_report reason=no_iocs_remaining")
                local_report.delete()


        except Exception as lre:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            self._log.error(
                "function=main action=fatal_error exception_line={} exception_file={}  message={}".format(
                    exc_tb.tb_lineno,
                    fname, lre))

    def main(self):
        try:
            self._log.debug("action=start")
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
        modaction = VmwareRemoveIocWatchlist(sys.stdin.read(), action_name=_alert_name)
        modaction.main()
        sc, evttype = modaction.get_evtidx("vmware_cbc_action_index")
        logger.info("action=found_eventtype class=alert_action_index alert_action_index=\"{}\"".format(evttype))
        modaction.writeevents(index=evttype,
                              fext='vmware_cbc_alert_action_st',
                              sourcetype="vmware:alert_action:{}".format(_alert_name),
                              source="vmware:alert_action:{}:{}".format(_alert_name,
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
