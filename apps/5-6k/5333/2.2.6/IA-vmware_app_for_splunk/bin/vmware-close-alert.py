# - Dismiss Alerts
#     - `Documentation <https://developer.carbonblack.com/reference/carbon-black-cloud/platform/latest/alerts-api/#create-workflow>`_
#     - Credential Type: Custom
#     - Global Configuration
#         - API Config: Supports multi-tenancy.
#             - To use multi-tenancy, include the ``org_key`` field with the corresponding value.
#         - Select the API Configs to use with this alert action.
#         - Only 1 API Config per Organization Key should be configured for each alert action.
#     - Search Configuration
#         - Alert ID Field: the field name that contains the alert id that should be closed.
import sys
import os
import json
import logging
import csv
import time
from VMWUtilities import KennyLoggins
from vmware_cbc_alert_actions import VmwareCBCAlertAction
import multiprocessing.dummy as mp
from pathlib import Path
import vmware_paths
from cbc_sdk.platform import BaseAlert


_alert_name = Path(__file__).stem
__app_name__ = vmware_paths.__app_name__


kl = KennyLoggins()
logger = kl.get_logger(
    app_name=__app_name__, file_name=_alert_name, log_level=logging.INFO)


class VmwareCloseAlert(VmwareCBCAlertAction):
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

    def main(self):
        try:
            self._log.debug("action=start")
            with self._load_results("rt") as fh:
                self._log.debug("file_handler={}".format(fh))
                p = mp.Pool(10)

                def do_threaded_result(num, result):
                    try:
                        self._log.debug(
                            "processing result number result={}".format(num))
                        result.setdefault('rid', str(num))
                        for key in ["host", "sourcetype", "source", "index", "sid"]:
                            if key in result:
                                result["orig_{}".format(key)] = result[key]
                                del result[key]
                        delete_result_keys = [
                            key for key in result if '_mv' in key]
                        for key in delete_result_keys:
                            del result[key]
                        self._log.debug(
                            "action=getting query fields from configuration result={}".format(num))
                        config_alert_ids = result.get(
                            self._configuration.get("alert_id"), None)
                        self._log.debug("action=check configuration variables")

                        if config_alert_ids is None:
                            msg = "action=validating configuration values, msg=no alert id specified, will not continue"
                            self._log.warn(msg)
                            self._log.debug("{}".format(
                                json.dumps(self._configuration)))
                            self.addevent(
                                msg, "vmware:alert_action{}:error".format(_alert_name))
                        else:
                            self._log.info("action=closing alerts")
                            alert_id_list = []
                            tmp_alert_ids = config_alert_ids.split(",")
                            for alert_id in tmp_alert_ids:
                                alert_id_list.append(alert_id)

                            try:
                                if result.get("org_key", None) is not None and self._use_multi_tenant:
                                    org_key = result.get("org_key")
                                    self._log.debug(
                                        "action=multi_tenant_api_usage org_key={}".format(org_key))
                                    alert = self.multi_tenant_apis[org_key]["cb"].select(
                                        BaseAlert).set_alert_ids(alert_id_list)
                                else:
                                    alert = self.cb.select(
                                        BaseAlert).set_alert_ids(alert_id_list)

                                request_id = alert.dismiss(
                                    'Closed in Splunk alert action {}'.format(_alert_name))
                                workflow_status = self.cb.select(
                                    WorkflowStatus, request_id)
                                while not workflow_status.finished:
                                    time.sleep(15)
                                    workflow_status = self.cb.select(
                                        WorkflowStatus, request_id)
                                workflow_status_event = workflow_status.get(
                                    "_info", "{}")
                                workflow_status_event['errors'] = workflow_status.errors
                                workflow_status_event['failed_ids'] = workflow_status.failed_ids
                                workflow_status_event['configured_ids'] = alert_id_list
                                self.addevent(json.dumps(workflow_status_event),
                                              sourcetype="vmware:alert_action:{}".format(_alert_name))
                            except Exception as te:
                                exc_type, exc_obj, exc_tb = sys.exc_info()
                                fname = os.path.split(
                                    exc_tb.tb_frame.f_code.co_filename)[1]
                                self._log.error(
                                    "function=main action=fatal_error exception_line={} exception_file={}  message={}".format(
                                        exc_tb.tb_lineno,
                                        fname, te))

                        self._log.info("action=processing alert complete")

                    except Exception as lre:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        fname = os.path.split(
                            exc_tb.tb_frame.f_code.co_filename)[1]
                        self._log.error(
                            "function=main action=fatal_error exception_line={} exception_file={}  message={}".format(
                                exc_tb.tb_lineno,
                                fname, lre))

                matrix = [(num, result)
                          for num, result in enumerate(csv.DictReader(fh))]
                p.starmap(do_threaded_result, matrix)
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
        logger.fatal(
            "FATAL Unsupported execution mode (expected --execute flag)")
        sys.exit(1)
    modaction = None
    try:
        logger.info("instantiating {}".format(_alert_name))
        modaction = VmwareCloseAlert(sys.stdin.read(), action_name=_alert_name)
        modaction.main()
        sc, evttype = modaction.get_evtidx("vmware_cbc_action_index")
        logger.info(
            "action=found_eventtype class=alert_action_index alert_action_index=\"{}\"".format(evttype))
        modaction.writeevents(index=evttype,
                              fext='vmware_cbc_alert_action_st',
                              sourcetype="vmware:alert_action:{}".format(
                                  _alert_name),
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
