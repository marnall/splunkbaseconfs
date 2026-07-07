import sys
import json
import csv
import logging
from Utilities import KennyLoggins, Utilities
from vmware_edr_client import EDRAlertAction
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import multiprocessing.dummy as mp
import os
from cbapi.response import Sensor

_APP_NAME = "vmware_cb_edr_app_for_splunk"
_alert_name = "vmware-edr-kill-process"
sys.path.insert(0, make_splunkhome_path(["etc", "apps", _APP_NAME, "lib"]))
kl = KennyLoggins()
logger = kl.get_logger(app_name=_APP_NAME, file_name=_alert_name, log_level=logging.INFO)


class SplunkSensor(Sensor):

    def __init__(self, *args, **kwargs):
        super(SplunkSensor, self).__init__(*args, **kwargs)

    def get_info(self):
        return self._info


class VmwareKillProcess(EDRAlertAction):
    def __init_(self, setting, action_name):
        try:
            EDRAlertAction.__init__(self, settings=settings, action_name=_alert_name,
                                          filename=_alert_name,
                                          stanza="global_{}_configuration".format(_alert_name))
        except Exception as e:
            self._catch_error(e, action_name)

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

    def main(self):
        try:
            self._log.debug("action=start")
            self.setup()
            edr_clients = self.clients_by_org_key()
            self._log.info("edr_client: {}".format(edr_clients))
            with self._load_results("rt") as fh:
                self._log.debug("file_handler={}".format(fh))
                p = mp.Pool(10)
                def do_threaded_result(num, result):
                    try:
                        self._log.debug("processing result number result={}".format(num))
                        result.setdefault('rid', str(num))
                        result["orig_sourcetype"] = result['sourcetype']
                        result["orig_source"] = result["source"]
                        result["orig_host"] = result["host"]
                        del result["source"]
                        del result["sourcetype"]
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
                            self.addevent(msg, "vmware:cb:edr:alert_action:{}:error".format(_alert_name))
                            return
                        hostname = "hostname:{}".format(device_id)
                        result["device_id"] = device_id
                        org_name = result["host"]
                        self._log.debug("org_name: {}".format(org_name))
                        try:

                            self._log.debug("action=starting_live_response_session")
                            edr_sensor = None
                            try:
                                edr_sensor = edr_clients[org_name].select(SplunkSensor).where(hostname).first()
                                if edr_sensor is None:
                                    result["alert_action_exception"] = "sensor_not_found"
                                    self.addevent(json.dumps(dict(result)),
                                                  sourcetype="vmware:cb:edr:alert_action:{}".format(_alert_name))
                                    self._log.warn("action=cannot_get_sensor hostname={}".format(hostname))
                                    return
                            except KeyError:
                                result["alert_action_exception"] = "Unable to find API config for host \"{}\"".format(
                                    org_name)
                                self.addevent(json.dumps(dict(result)),
                                              sourcetype="vmware:cb:edr:alert_action:{}:error".format(_alert_name))
                                self._log.warn("action=cannot_find_host host={}".format(org_name))
                                return
                            # edr_sensor.refresh()

                            def setK(k):
                                return k
                            with edr_sensor.lr_session() as session:
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
                                                      sourcetype="vmware:cb:edr:alert_action:{}".format(_alert_name))
                                        process_match_cnt += 1

                                if process_match_cnt == 0:
                                    self._log.info("Process: {} was not found".format(process_name))

                                self._log.info("action=exiting_session")
                                return

                        except Exception as te:
                            self._catch_error(te, self._action_name)

                    except Exception as lre:
                        self._catch_error(lre, self._action_name)
                matrix = [(num, result) for num, result in enumerate(csv.DictReader(fh))]
                p.starmap(do_threaded_result, matrix)
                p.close()
                p.join()

        except Exception as me:
            self._catch_error(me, self._action_name)


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        logger.fatal("FATAL Unsupported execution mode (expected --execute flag)")
        sys.exit(1)
    modaction = None
    try:
        logger.info("instantiating {}".format(_alert_name))
        modaction = VmwareKillProcess(sys.stdin.read(), action_name=_alert_name)
        modaction.main()
        sc, evttype = modaction.get_evtidx("vmware_cb_edr_action_index")
        logger.info("action=found_eventtype class=alert_action_index alert_action_index=\"{}\"".format(evttype))
        modaction.writeevents(index=evttype,
                              fext='vmware_cb_edr_alert_action_st',
                              sourcetype="vmware:cb:edr:alert_action:{}".format(_alert_name),
                              source="vmware:cb:edr:alert_action:{}:{}".format(_alert_name,
                                                                            modaction.payload["search_name"].replace(" ","_")))
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
