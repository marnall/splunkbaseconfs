# - Kill Process
#     - `Documentation <https://developer.carbonblack.com/reference/carbon-black-cloud/cb-defense/latest/live-response-api/#kill>`_
#     - Credential Type: Live Response
#     - Global Configuration
#         - API Config: Supports multi-tenancy.
#             - To use multi-tenancy, include the ``org_key`` field with the corresponding value.
#         - Select the API Configs to use with this alert action.
#         - Only 1 API Config per Organization Key should be configured for each alert action.
#     - Search Configuration
#         - Device ID Field: the field name that contains the device id to list processes.
#         - Process Field: the field name that contains the process name to kill.
import sys
import os
import json
import logging
import csv
from VMWUtilities import KennyLoggins
from vmware_cbc_alert_actions import VmwareCBCAlertAction
import multiprocessing.dummy as mp
from pathlib import Path
import vmware_paths
# from cbc_sdk.endpoint_standard import Device
from cbc_sdk.platform import Device

_alert_name = Path(__file__).stem
__app_name__ = vmware_paths.__app_name__
kl = KennyLoggins()
logger = kl.get_logger(app_name=__app_name__, file_name=_alert_name, log_level=logging.INFO)


class VmwareKillProcess(VmwareCBCAlertAction):
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
                        self._log.debug("processing result number result={}".format(num))
                        result.setdefault('rid', str(num))
                        for key in ["host", "sourcetype", "source", "index", "sid"]:
                            if key in result:
                                result["orig_{}".format(key)] = result[key]
                                del result[key]
                        delete_result_keys = [key for key in result if '_mv' in key]
                        for key in delete_result_keys:
                            del result[key]
                        self._log.debug("getting device id field result={}".format(num))
                        device_id = result.get(self._configuration.get("device_id_field", None), None)
                        self._log.debug("getting process field result={}".format(num))
                        process_name = result.get(self._configuration.get("process_field", None), None)
                        self._log.debug("checking fields result={} device_id={} process_name={}".format(num,
                                                                                                        device_id,
                                                                                                        process_name))
                        if device_id is None or process_name is None:
                            msg = "action=cannot_complete_action device_id={} device_field={} process_name={} process_field={}".format(
                                device_id, self._configuration.get("device_id_field", None),
                                process_name, self._configuration.get("process_field", None))
                            self._log.warn(msg)
                            self._log.debug("{}".format(json.dumps(self._configuration)))
                            self.addevent(msg, "vmware:alert_action:{}:error".format(_alert_name))
                            return
                        # Where can be one of: ip, hostname, groupid
                        hostname = "deviceId:{}".format(device_id)
                        result["device_id"] = device_id
                        try:
                            self._log.debug("action=starting_live_response_session")
                            device = None
                            if result.get("org_key", None) is not None and self._use_multi_tenant:
                                org_key = result.get("org_key")
                                self._log.debug("action=multi_tenant_api_usage org_key={}".format(org_key))
                                device = self.multi_tenant_apis[org_key]["cb"].select(
                                    Device).where(hostname).first()
                            else:
                                device = self.cb.select(Device).where(hostname).first()
                            if device is None:
                                result["alert_action_exception"] = "sensor_not_found"
                                self.addevent(json.dumps(dict(result)),
                                              sourcetype="vmware:alert_action:{}".format(_alert_name))
                                self._log.warn("action=cannot_get_sensor hostname={}".format(hostname))
                                return
                            device.refresh()
                            self._log.debug("hosts={}".format(device._info))
                            self._log.info("action=starting_lr_session")

                            def setK(k):
                                return k
                            with device.lr_session() as session:
                                self._log.info("action=listing_processes")
                                result["processes"] = session.list_processes()
                                kv_processes = {setK(x["command_line"]): x["pid"] for x in result["processes"]}
                                self._log.debug("kv_processes: {}".format(kv_processes))
                                process_match_cnt = 0
                                for command_line, pid in kv_processes.items():
                                    if process_name in command_line:
                                        self._log.info("Kill process: {}, Command: {}, pid:  {}".format(process_name, command_line, pid))
                                        result["kill_process_pid"] = pid
                                        result["kill_process_name"] = process_name
                                        result["kill_process_result"] = session.kill_process(pid)
                                        self.addevent(json.dumps(dict(result)),
                                                      sourcetype="vmware:alert_action:{}".format(_alert_name))
                                        process_match_cnt += 1

                                if process_match_cnt == 0:
                                    self._log.info("Process: {} was not found".format(process_name))

                                self._log.info("action=exiting_session")
                                return
                        except Exception as te:
                            exc_type, exc_obj, exc_tb = sys.exc_info()
                            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                            self._log.error(
                                "function=main action=fatal_error exception_line={} exception_file={}  message={}".format(
                                    exc_tb.tb_lineno,
                                    fname, te))
                    except Exception as lre:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                        self._log.error(
                            "function=main action=fatal_error exception_line={} exception_file={}  message={}".format(
                                exc_tb.tb_lineno,
                                fname, lre))

                matrix = [(num, result) for num, result in enumerate(csv.DictReader(fh))]
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
        logger.fatal("FATAL Unsupported execution mode (expected --execute flag)")
        sys.exit(1)
    modaction = None
    try:
        logger.info("instantiating {}".format(_alert_name))
        modaction = VmwareKillProcess(sys.stdin.read(), action_name=_alert_name)
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
