# - Ban Hash
#     - `Documentation <https://developer.carbonblack.com/reference/carbon-black-cloud/cb-defense/latest/reputation-override-api/#configure-reputation-override>`_
#     - Credential Type: Custom
#     - Global Configuration
#         - API Config: Supports multi-tenancy.
#             - To use multi-tenancy, include the ``org_key`` field with the corresponding value.
#         - Select the API Configs to use with this alert action.
#         - Only 1 API Config per Organization Key should be configured for each alert action.
#     - Search Configuration
#         - File Hash Field: the field name that contains the SHA256 hash (only SHA256) of the object in question.
#         - ``description``: Optional Field to pass with a description for the CBC Reputation UI. Default: ``Banned via Splunk Alert Action``
#         - ``threat_cause_actor_name``: Optional field to pass with filename of the hash. Non-configurable.
import sys
import os
import json
import logging
import csv
import re
from VMWUtilities import KennyLoggins
from vmware_cbc_alert_actions import VmwareCBCAlertAction
import multiprocessing.dummy as mp
from pathlib import Path
import vmware_paths
from cbc_sdk.platform import ReputationOverride

_alert_name = Path(__file__).stem
__app_name__ = vmware_paths.__app_name__

kl = KennyLoggins()
logger = kl.get_logger(app_name=__app_name__, file_name=_alert_name, log_level=logging.INFO)


class VmwareBanHash(VmwareCBCAlertAction):
    def __init__(self, settings, action_name):
        try:
            logger.fatal("stdin={}".format(settings))
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

                def us(r, k):
                    if k in r:
                        r["orig_{}".format(k)] = r.get(k, "")
                        del r[k]
                self._log.debug("action=configuration hash_field={}".format(self._configuration.get("hash_field", None)))

                def do_threaded_result(num, result):
                    try:
                        self._log.debug("processing result number result={}".format(num))
                        result.setdefault('rid', str(num))
                        #  Update results for orig_ keys
                        [us(result, key) for key in ["sourcetype", "source", "host", "index", "sid"]]
                        delete_result_keys = [key for key in result if re.match(r"_[a-z_]+", key)]
                        for key in delete_result_keys:
                            del result[key]
                        self._log.debug("action=getting_hash_field result_num={} result_keys={}".format(num, result.keys()))
                        # From the alert action configuration, get the mapped field value for the result
                        hash_id = result.get(self._configuration.get("hash_field", None), None)
                        if hash_id is None:
                            msg = "action=cannot_complete_action hash_id={} hash_field={} orig_sid={}".format(
                                hash_id, self._configuration.get("hash_field", None), result.get("orig_sid", result.get("orig_sourcetype", "unknown")))
                            self._log.warn(msg)
                            self._log.debug("{}".format(json.dumps(self._configuration)))
                            self.addevent(msg, "vmware:alert_action:{}:error".format(_alert_name))
                            return
                        try:
                            self._log.debug("action=ban_hash")
                            c = None
                            if result.get("org_key", None) is not None and self._use_multi_tenant:
                                org_key = result.get("org_key")
                                self._log.debug("action=multi_tenant_api_usage org_key={}".format(org_key))
                                c = self.multi_tenant_apis[org_key]["cb"]
                            else:
                                c = self.cb
                            if len("{}".format(hash_id)) != 64:
                                result["ban_hash_response"] = "invalid_sha256"
                            else:
                                ro = ReputationOverride.create(c, {
                                    "sha256_hash": "{}".format(hash_id),
                                    "override_type": "SHA256",
                                    "override_list": "BLACK_LIST",
                                    "filename": result.get("threat_cause_actor_name", "Actor Name not defined"),
                                    "description": result.get("description", "Banned via Splunk Alert Action")
                                })
                                result["ban_hash_response"] = ro._info
                            self.addevent(json.dumps(dict(result)),
                                          sourcetype="vmware:alert_action:{}".format(_alert_name))
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
        modaction = VmwareBanHash(sys.stdin.read(), action_name=_alert_name)
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
