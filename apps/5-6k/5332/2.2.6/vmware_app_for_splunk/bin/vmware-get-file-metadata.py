# - Get File Metadata
#     - `Documentation <https://developer.carbonblack.com/reference/carbon-black-cloud/cb-threathunter/latest/universal-binary-store-api/#retrieve-metadata>`_
#     - Credential Type: Custom
#     - Global Configuration
#         - API Config: Supports multi-tenancy.
#             - To use multi-tenancy, include the ``org_key`` field with the corresponding value.
#         - Select the API Configs to use with this alert action.
#         - Only 1 API Config per Organization Key should be configured for each alert action.
#     - Search Configuration
#         - File Hash Field: the field name that contains the SHA256 hash (only SHA256) of the object in question.
import sys
import os
import json
import logging
import csv
from VMWUtilities import KennyLoggins, Utilities
from vmware_cbc_alert_actions import VmwareCBCAlertAction
from vmware_cbc_cmd import SplunkCBCTHBinary
import multiprocessing.dummy as mp
from pathlib import Path
import vmware_paths

_alert_name = Path(__file__).stem
__app_name__ = vmware_paths.__app_name__
kl = KennyLoggins()
logger = kl.get_logger(app_name=__app_name__, file_name=_alert_name, log_level=logging.INFO)


class VmwareGetFileMetadata(VmwareCBCAlertAction):
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
                        result["orig_sourcetype"] = result['sourcetype']
                        result["orig_source"] = result["source"]
                        result["orig_host"] = result["host"]
                        del result["source"]
                        del result["sourcetype"]
                        del result["host"]
                        for key in ["host", "sourcetype", "source", "index", "sid"]:
                            if key in result:
                                result["orig_{}".format(key)] = result[key]
                                del result[key]
                        delete_result_keys = [key for key in result if '_mv' in key]
                        for key in delete_result_keys:
                            del result[key]
                        self._log.debug("getting hash field result={}".format(num))
                        # From the alert action configuration, get the mapped field value for the result
                        hash_id = result.get(self._configuration.get("hash_field", None), None)
                        if hash_id is None:
                            msg = "action=cannot_complete_action hash_id={} hash_field={} ".format(
                                hash_id, self._configuration.get("hash_field", None))
                            self._log.warn(msg)
                            self._log.debug("{}".format(json.dumps(self._configuration)))
                            self.addevent(msg, "vmware:alert_action:{}:error".format(_alert_name))
                            return
                        hash_filter = "hash:{}".format(hash_id)
                        result["hash_filter"] = hash_filter
                        self._log.debug("listing_metadata_for: {}".format(hash_id))
                        try:
                            self._log.debug("action=getting_summary")
                            file_metadata = None
                            if result.get("org_key", None) is not None and self._use_multi_tenant:
                                org_key = result.get("org_key")
                                self._log.debug("action=multi_tenant_api_usage org_key={}".format(org_key))
                                file_metadata = self.multi_tenant_apis[org_key]["cb"].select(
                                    SplunkCBCTHBinary, hash_id).summary
                            else:
                                file_metadata = self.cb.select(SplunkCBCTHBinary, hash_id).summary
                            self._log.debug("action=show_file_metadata binary={}".format(file_metadata))
                            if file_metadata is None:
                                result["file_metadata"] = {}
                                self.addevent(json.dumps(dict(result)),
                                              sourcetype="vmware:alert_action:{}".format(_alert_name))
                                self._log.warn("action=cannot_get_file hash_filter={}".format(hash_filter))
                                return
                            result["file_metadata"] = file_metadata
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
        modaction = VmwareGetFileMetadata(sys.stdin.read(), action_name=_alert_name)
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
