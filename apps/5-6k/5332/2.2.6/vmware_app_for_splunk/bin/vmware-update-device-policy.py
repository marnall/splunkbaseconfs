# - Update Device Policy
#     - `Documentation <https://developer.carbonblack.com/reference/carbon-black-cloud/platform/latest/devices-api/#update-policy>`_
#     - Credential Type: Custom
#     - Global Configuration
#         - API Config: Supports multi-tenancy.
#             - To use multi-tenancy, include the ``org_key`` field with the corresponding value.
#         - Select the API Configs to use with this alert action.
#         - Only 1 API Config per Organization Key should be configured for each alert action.
#     - Search Configuration
#         - Device ID Field: the field name that contains the Device ID that should be updated.
#         - Policy ID Field: the field name that contains the new policy ID that should be applied
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
from cbc_sdk.platform import Device

_alert_name = Path(__file__).stem
__app_name__ = vmware_paths.__app_name__
kl = KennyLoggins()
logger = kl.get_logger(app_name=__app_name__, file_name=_alert_name, log_level=logging.INFO)


class VmwareUpdateDevicePolicy(VmwareCBCAlertAction):
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
                        self._log.debug("action=getting query fields from configuration result={}".format(num))
                        config_device_ids = result.get(self._configuration.get("device_id"), None)
                        config_policy_id = result.get(self._configuration.get("policy_id"), None)
                        self._log.debug("action=check configuration variables")
                        continue_processing = False
                        tmp_device_ids = []
                        device_id_list = []
                        if config_device_ids is None:
                            msg = "action=validating configuration values, msg=no device id specified, will not continue"
                            self._log.warn(msg)
                            self._log.debug("{}".format(json.dumps(self._configuration)))
                            self.addevent(msg, "vmware:alert_action:{}:error".format(_alert_name))
                            continue_processing = False
                        else:
                            continue_processing = True
                            tmp_device_ids = config_device_ids.split(",")

                        if config_policy_id is None:
                            msg = "action=validating configuration values, msg=no policy id specified or policy id is not an integer, will not continue"
                            self._log.warn(msg)
                            self._log.debug("{}".format(json.dumps(self._configuration)))
                            self.addevent(msg, "vmware:alert_action{}:error".format(_alert_name))
                            continue_processing = False
                        else:
                            continue_processing = True

                        try:
                            chk_policy_is_int = isinstance(int(config_policy_id), int)
                            continue_processing = True
                        except:
                            # if not isinstance(config_policy_id, int):
                            msg = "action=validating configuration values, msg=policy id is not an integer, will not continue"
                            self._log.warn(msg)
                            self._log.debug("{}".format(json.dumps(self._configuration)))
                            self.addevent(msg, "vmware:alert_action{}:error".format(_alert_name))
                            continue_processing = False

                        if continue_processing:
                            self._log.info("action=updating policy on devices, new policy_id: {}".format(config_policy_id))
                            for device_id in tmp_device_ids:
                                chk_is_int_device_id = device_id.isdigit()

                                if chk_is_int_device_id:
                                    device_id_list.append(int(device_id))
                                else:
                                    found_slash = device_id.find("\\")
                                    if found_slash != -1:
                                        hostname = "name:{}\"".format(device_id[:found_slash]+"\\"+device_id[found_slash:]+"\"")
                                    else:
                                        hostname = "name:{}".format(device_id)
                                    try:
                                        self._log.debug("action=get device information, device: {}, hostname: {}".format(device_id, hostname))
                                        device = None
                                        if result.get("org_key", None) is not None and self._use_multi_tenant:
                                            org_key = result.get("org_key")
                                            self._log.debug("action=multi_tenant_api_usage org_key={}".format(org_key))
                                            tmp_device_list = self.multi_tenant_apis[org_key]["cb"].select(Device).where(hostname).first()
                                            device = tmp_device_list.where(hostname).first()
                                        else:
                                            self._log.debug("hostname: {}, device_id: {}".format(hostname, device_id))
                                            tmp_device_list = self.cb.select(Device)
                                            device = tmp_device_list.where(hostname).first()

                                        if device is not None:
                                            self._log.info("device={}, type_of_device={}, len(device):{}".format(device, type(device), len(tmp_device_list)))
                                            tmp_device = device.get("_info", "{}")
                                            self._log.debug("tmp_device_id: {}, tmp_device: {}, type tmp_device: {}".format(tmp_device["id"], tmp_device, type(tmp_device)))
                                            device_id_list.append(int(tmp_device["id"]))

                                            self._log.debug("device_id_list: {}".format(device_id_list))
                                        else:
                                            msg = "action=retrieving device info for device name, msg=no device found for device: {}, will not continue".format(device_id)
                                            self._log.warn(msg)
                                            self._log.debug("{}".format(json.dumps(self._configuration)))
                                            self.addevent(msg, "vmware:alert_action{}:error".format(_alert_name))
                                            continue

                                    except Exception as te:
                                        exc_type, exc_obj, exc_tb = sys.exc_info()
                                        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                                        self._log.error(
                                            "function=main action=fatal_error exception_line={} exception_file={}  message={}".format(
                                                exc_tb.tb_lineno,
                                                fname, te))

                                self._log.debug("device_id_list: {}".format(device_id_list))
                                try:
                                    if result.get("org_key", None) is not None and self._use_multi_tenant:
                                        org_key = result.get("org_key")
                                        self._log.debug("action=multi_tenant_api_usage org_key={}".format(org_key))
                                        final_device_list = self.multi_tenant_apis[org_key]["cb"].select(Device) \
                                            .set_device_ids(device_id_list) \
                                            .update_policy(int(config_policy_id))
                                    else:
                                        self._log.debug("action=update policy, non multi-tenant")
                                        final_device_list = self.cb.select(Device) \
                                            .set_device_ids(device_id_list) \
                                            .update_policy(int(config_policy_id))

                                        device_policy_update_event = {}
                                        device_policy_update_event['description'] = "Created by alert action: {}".format(_alert_name)
                                        device_policy_update_event['device_ids'] = device_id_list
                                        device_policy_update_event['new_policy_id'] = config_policy_id
                                        device_policy_update_event['updated_timestamp'] = datetime.utcnow().isoformat()
                                        self.addevent(json.dumps(device_policy_update_event),
                                                      sourcetype="vmware:alert_action:{}".format(_alert_name))

                                except Exception as te:
                                    exc_type, exc_obj, exc_tb = sys.exc_info()
                                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                                    self._log.error(
                                        "function=main action=fatal_error exception_line={} exception_file={}  message={}".format(
                                            exc_tb.tb_lineno,
                                            fname, te))


                            self._log.info("action=policy update complete, device ids: {} to policy: {}".format(config_device_ids, config_policy_id))

                    except Exception as lre:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                        self._log.error(
                            "function=main action=fatal_error exception_line={} exception_file={}  message={}".format(
                                exc_tb.tb_lineno,
                                fname, lre))

                matrix = [(num, result) for num, result in enumerate(csv.DictReader(fh))]
                self._log.debug("matrix: {}".format(matrix))
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
        modaction = VmwareUpdateDevicePolicy(sys.stdin.read(), action_name=_alert_name)
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